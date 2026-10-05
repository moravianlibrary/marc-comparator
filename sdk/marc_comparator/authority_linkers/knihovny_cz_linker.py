"""Link catalog records through the knihovny.cz deduplication service.

A dedup group is an assertion by another system that two records describe the
same thing. It is a strong hint and a good retrieval step, but it is still
somebody else's judgement about our record. The comparator has the final word
here exactly as it does for the locally harvested linkers, so every link this
plugin reports carries a measured confidence rather than an implied one.
"""

import asyncio
import logging
import re
from collections.abc import Sequence
from typing import Any

import httpx
from lxml import etree
from marcdantic import MarcRecord
from pydantic import BaseModel, Field

from ..comparators._base import MATCH_SCALE_MAX
from ..comparators.default import DefaultComparator, DefaultComparatorConfig
from ._base import (
    CANDIDATE_MARC_CONTEXT,
    AuthorityLink,
    BaseAuthorityLinker,
    LinkProposal,
    LinkRequest,
    MatchRoute,
)
from .identity import find_identity_conflicts

logger = logging.getLogger(__name__)

#: Ids per prefetch request. The service refuses 200 outright; at 50 a record
#: costs about 12 ms against 196 ms asked for one at a time, and the URL stays
#: well inside what the service accepts.
_PREFETCH_BATCH_SIZE = 50

#: Prefetch requests in flight at once. A window of two hundred is four
#: requests; letting them overlap turns a window's wait from the sum of
#: them into roughly the slowest, without asking the service for more at
#: once than a person reading the catalogue would.
_PREFETCH_CONCURRENCY = 4

#: knihovny.cz answers a record it does not hold with this, under HTTP 400.
_RECORD_NOT_FOUND_MESSAGE = "Error loading record"


def _is_record_not_found(response: httpx.Response) -> bool:
    """Whether a 400 is knihovny.cz saying it holds no such record.

    The API has no 404: an id it does not hold and a malformed id get the same
    400 with an ERROR body reading "Error loading record". Raising for it would
    make a record the service simply lacks indistinguishable from a fault, and
    the caller abandons the whole record when a linker fails — no comparison,
    no validation, not even marked processed.

    The body is read rather than the status alone so a genuinely bad request
    still surfaces as a failure. That distinction matters: "no link" is taken
    as evidence that an existing link is obsolete and deletes it, so only an
    answer that really means "not here" may be reported as one.
    """

    if response.status_code != httpx.codes.BAD_REQUEST:
        return False
    try:
        payload = response.json()
    except ValueError:
        return False
    return (
        payload.get("status") == "ERROR"
        and payload.get("statusMessage") == _RECORD_NOT_FOUND_MESSAGE
    )


def _parse_full_record(xml: str) -> MarcRecord | None:
    return MarcRecord.from_xml(etree.fromstring(xml.encode("utf-8")), CANDIDATE_MARC_CONTEXT)


class KnihovnyCZBaseMapping(BaseModel):
    base: str
    id_template: str
    pattern: str
    is_target: bool = False


class KnihovnyCZLinkerConfig(BaseModel):
    api_url: str = "https://www.knihovny.cz/api/v1"

    #: Lowest comparator score worth reporting at all. 9 out of 15 is the
    #: bottom of the comparator's "Moderate" band; below it a dedup group has
    #: grouped two records this catalogue would not call the same thing.
    minimum_confidence: float = Field(default=9.0, ge=0.0, le=MATCH_SCALE_MAX)

    mappings: list[KnihovnyCZBaseMapping] = [
        KnihovnyCZBaseMapping(
            base="MZK01",
            id_template="mzk.MZK01-{system_number}",
            pattern=r"^mzk\.MZK01-(\d{9})$",
        ),
        KnihovnyCZBaseMapping(
            base="MZK03",
            id_template="mzk.MZK03-{system_number}",
            pattern=r"^mzk\.MZK03-(\d{9})$",
        ),
        KnihovnyCZBaseMapping(
            base="SKC",
            id_template="caslin.SKC01-{system_number}",
            pattern=r"^caslin\.SKC01-(\d{9})$",
            is_target=True,
        ),
    ]


class KnihovnyCZLinker(BaseAuthorityLinker[KnihovnyCZLinkerConfig]):
    """
    Authority linker for the Knihovny.cz authority base.
    """

    config_model = KnihovnyCZLinkerConfig

    def __init__(self, config: KnihovnyCZLinkerConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=10)
        # DefaultComparator writes the Ollama URL into module state when it is
        # constructed. The gate never calls the LLM, so carry the value already
        # in effect rather than resetting one the comparison feature configured
        # in this same worker process.
        from ..comparators.intiim_engine import llm

        self._comparator = DefaultComparator(
            DefaultComparatorConfig(
                ollama_url=llm.OLLAMA_URL,
                llm_enabled=False,
                nonstandard_llm_enabled=False,
            )
        )

        self._base_to_id_mapper: dict[str, str] = {
            mapping.base: mapping.id_template for mapping in config.mappings
        }
        self._id_to_base_patterns: dict[str, str] = {
            mapping.pattern: mapping.base for mapping in config.mappings
        }

        # Answers for the window the host last announced. Both are replaced
        # wholesale by each prefetch, so they hold one window and not a run.
        self._dedup_cache: dict[str, list[str]] = {}
        self._record_cache: dict[str, MarcRecord | None] = {}

    @classmethod
    async def get_target_bases(cls, config: KnihovnyCZLinkerConfig) -> list[str]:
        return [mapping.base for mapping in config.mappings if mapping.is_target]

    def _source_id(self, base: str, system_number: str) -> str | None:
        template = self._base_to_id_mapper.get(base)
        return None if template is None else template.format(system_number=system_number)

    def _target_system_numbers(self, dedup_ids: list[str], target_base: str) -> list[str]:
        """The members of a dedup group that live in the base being linked to.

        A group may name more than one, so they are all kept and weighed rather
        than the last one winning.
        """

        found: list[str] = []
        for dedup_id in dedup_ids:
            for pattern, mapped_base in self._id_to_base_patterns.items():
                if target_base != mapped_base:
                    continue
                match_obj = re.match(pattern, dedup_id)
                if match_obj and match_obj.group(1) not in found:
                    found.append(match_obj.group(1))
        return found

    async def _fetch_field(self, ids: list[str], field: str) -> dict[str, Any]:
        """Read one field of many records per request, keyed by what answered.

        The response is not positional: ids the service cannot load are dropped
        from it entirely, so three ids can come back as two records. `id` is
        therefore asked for alongside the field being read and the result keyed
        by that, never by request order. An id missing from the answer is the
        batch form of the 400 a single lookup gets for the same record.
        """

        chunks = [
            ids[start : start + _PREFETCH_BATCH_SIZE]
            for start in range(0, len(ids), _PREFETCH_BATCH_SIZE)
        ]
        # The chunks do not depend on each other, and the service answers a
        # request in about half a second however small it is, so waiting for
        # each in turn is most of what a window costs. Bounded because being
        # able to ask for everything at once is not a reason to.
        limit = asyncio.Semaphore(_PREFETCH_CONCURRENCY)

        async def fetch(chunk: list[str]) -> list[dict[str, Any]]:
            async with limit:
                response = await self.client.get(
                    f"{self.config.api_url}/record",
                    params=[("id[]", id) for id in chunk] + [("field[]", field), ("field[]", "id")],
                )
            if _is_record_not_found(response):
                return []
            response.raise_for_status()
            return response.json().get("records") or []

        # One chunk failing is one chunk's worth of records falling back to
        # their own lookup, which is what they would have done without a
        # window at all. Losing the chunks that did answer would be worse.
        results = await asyncio.gather(*(fetch(chunk) for chunk in chunks), return_exceptions=True)

        found: dict[str, Any] = {}
        for chunk, entries in zip(chunks, results, strict=True):
            if isinstance(entries, BaseException):
                logger.warning(
                    "Could not read %s for %d records at once (%s); "
                    "they will be asked for one at a time",
                    field,
                    len(chunk),
                    entries,
                )
                continue
            for entry in entries:
                id = entry.get("id")
                if id is not None and field in entry:
                    found[id] = entry[field]
        return found

    async def prefetch(self, requests: Sequence[LinkRequest]) -> None:
        """Answer a whole window in two requests instead of two per record.

        One round trip per record is what a full pass spends most of its time
        on, and the service takes many ids at once. The dedup groups come back
        first; they name the target records `run` will compare against, so
        those are fetched in the same shape rather than one at a time after.
        """

        self._dedup_cache = {}
        self._record_cache = {}

        source_ids: list[str] = []
        for request in requests:
            source_id = self._source_id(request.base, request.system_number)
            if source_id is not None:
                source_ids.append(source_id)
        if not source_ids:
            return

        unique = list(dict.fromkeys(source_ids))
        self._dedup_cache = await self._fetch_field(unique, "dedupIds")
        # An id the service did not answer for has no dedup group, and caching
        # that is what keeps `run` from asking again one record at a time.
        for source_id in unique:
            self._dedup_cache.setdefault(source_id, [])

        target_ids: list[str] = []
        for request in requests:
            source_id = self._source_id(request.base, request.system_number)
            if source_id is None:
                continue
            for system_number in self._target_system_numbers(
                self._dedup_cache[source_id], request.target_base
            ):
                target_id = self._source_id(request.target_base, system_number)
                if target_id is not None and target_id not in target_ids:
                    target_ids.append(target_id)
        if not target_ids:
            return

        fetched = await self._fetch_field(target_ids, "fullRecord")
        for target_id in target_ids:
            xml = fetched.get(target_id)
            if xml is None:
                self._record_cache[target_id] = None
                continue
            try:
                self._record_cache[target_id] = _parse_full_record(xml)
            except Exception:
                # One record the service cannot express as MARC must not cost
                # the window it happened to be in. Left out of the cache, so
                # `run` asks for it on its own and fails only that record.
                logger.warning("Skipping unparseable knihovny.cz record %s", target_id)

    async def _get_dedup_ids(self, id: str) -> list[str]:
        if id in self._dedup_cache:
            return self._dedup_cache[id]

        response = await self.client.get(
            f"{self.config.api_url}/record",
            params={"id": id, "field[]": "dedupIds"},
        )

        # Not every record of ours reaches knihovny.cz. One it has never
        # indexed has no dedup group, which is an answer, not an error.
        if _is_record_not_found(response):
            return []

        response.raise_for_status()

        return response.json()["records"][0]["dedupIds"]

    async def _get_record(self, id: str) -> MarcRecord | None:
        """
        Fetch the MARC record by its knihovny.cz ID.
        """
        if id in self._record_cache:
            return self._record_cache[id]

        response = await self.client.get(
            f"{self.config.api_url}/record",
            params={"id": id, "field[]": "fullRecord"},
        )

        if _is_record_not_found(response):
            return None

        response.raise_for_status()

        return _parse_full_record(response.json()["records"][0]["fullRecord"])

    async def run(
        self,
        base: str,
        system_number: str,
        record: MarcRecord,
        target_base: str,
    ) -> LinkProposal:
        source_id = self._source_id(base, system_number)
        if source_id is None:
            raise ValueError(f"Unsupported base: {base}")

        dedup_ids = await self._get_dedup_ids(source_id)
        target_system_numbers = self._target_system_numbers(dedup_ids, target_base)

        if not target_system_numbers:
            return LinkProposal.nothing_found()

        scored: list[AuthorityLink] = []
        for target_system_number in target_system_numbers:
            target_id = self._source_id(target_base, target_system_number)
            if target_id is None:
                continue
            target_record = await self._get_record(target_id)

            if target_record is None:
                # The dedup group names a record knihovny.cz will not serve.
                # Dropping that one member keeps the rest of the group usable;
                # a transport failure still raises and is never read as "no
                # link", which is what would delete a good link.
                continue

            comparison = await self._comparator.run(record, target_record)
            scored.append(
                AuthorityLink(
                    base=target_base,
                    system_number=target_system_number,
                    record=target_record,
                    confidence=comparison.overall_score,
                    # The pair the pipeline compares next, for whichever of
                    # these is chosen.
                    comparison=comparison,
                    # Every candidate here comes from one place, so unlike the
                    # dump linker there is nothing to tell apart and one floor
                    # is enough.
                    matched_by=MatchRoute.Dedup,
                    conflicts=find_identity_conflicts(record, target_record),
                )
            )

        if not scored:
            # The group named members and not one of them could be fetched.
            # Still "nothing to consider" rather than a failure: a transport
            # error would have raised out of `_get_record`.
            return LinkProposal.nothing_found()

        scored.sort(key=lambda link: link.confidence or 0.0, reverse=True)

        # A dedup group is knihovny.cz asserting that these records are the
        # same work, and a conflicting national bibliography number contradicts
        # it outright. The veto wins: dedup groups are built by an algorithm
        # and ČNB is assigned per bibliographic unit by the national library.
        #
        # Unmeasured on this route, unlike the dump linker's — only 336 of the
        # 47,777 links measured came through dedup, too few to say anything.
        # Applied here for consistency rather than on evidence, which is worth
        # revisiting once this route carries enough links to count.
        best = next((link for link in scored if not link.conflicts), None)

        # The dedup group says these records belong together; the comparator
        # says how far this catalogue agrees. Disagreement below the floor
        # withholds the link, but the group still comes back as candidates —
        # a group the comparator dislikes is a finding, not an absence.
        return LinkProposal(
            link=(
                best
                if best is not None and (best.confidence or 0.0) >= self.config.minimum_confidence
                else None
            ),
            candidates=scored,
            candidate_count=len(target_system_numbers),
        )
