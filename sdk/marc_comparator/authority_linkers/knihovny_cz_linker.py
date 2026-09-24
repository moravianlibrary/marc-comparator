"""Link catalog records through the knihovny.cz deduplication service.

A dedup group is an assertion by another system that two records describe the
same thing. It is a strong hint and a good retrieval step, but it is still
somebody else's judgement about our record. The comparator has the final word
here exactly as it does for the locally harvested linkers, so every link this
plugin reports carries a measured confidence rather than an implied one.
"""

import re

import httpx
from lxml import etree
from marcdantic import MarcRecord
from pydantic import BaseModel, Field

from ..comparators.default import DefaultComparator, DefaultComparatorConfig
from ._base import AuthorityLink, BaseAuthorityLinker

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


class KnihovnyCZBaseMapping(BaseModel):
    base: str
    id_template: str
    pattern: str
    is_target: bool = False


class KnihovnyCZLinkerConfig(BaseModel):
    api_url: str = "https://www.knihovny.cz/api/v1"

    #: Lowest comparator score worth reporting at all. 0.7 is the bottom of the
    #: comparator's "Moderate" band; below it a dedup group has grouped two
    #: records this catalogue would not call the same thing.
    minimum_confidence: float = Field(default=0.7, ge=0.0, le=1.0)

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


class KnihovnyCZLinker(BaseAuthorityLinker):
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

    @classmethod
    async def get_target_bases(cls, config: KnihovnyCZLinkerConfig) -> list[str]:
        return [mapping.base for mapping in config.mappings if mapping.is_target]

    async def _get_dedup_ids(self, id: str) -> list[str]:
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
        response = await self.client.get(
            f"{self.config.api_url}/record",
            params={"id": id, "field[]": "fullRecord"},
        )

        if _is_record_not_found(response):
            return None

        response.raise_for_status()

        full_record_xml = response.json()["records"][0]["fullRecord"]
        xml_bytes = full_record_xml.encode("utf-8")
        xml_element = etree.fromstring(xml_bytes)

        return MarcRecord.from_xml(xml_element)

    async def run(
        self,
        base: str,
        system_number: str,
        record: MarcRecord,
        target_base: str,
    ) -> AuthorityLink | None:
        if base not in self._base_to_id_mapper:
            raise ValueError(f"Unsupported base: {base}")

        dedup_ids = await self._get_dedup_ids(
            self._base_to_id_mapper[base].format(system_number=system_number)
        )

        # A dedup group may name more than one record in the target base. Weigh
        # them all rather than keeping whichever happened to come last.
        target_system_numbers: list[str] = []
        for dedup_id in dedup_ids:
            for (
                pattern,
                mapped_base,
            ) in self._id_to_base_patterns.items():
                if target_base != mapped_base:
                    continue

                match_obj = re.match(pattern, dedup_id)
                if not match_obj:
                    continue

                system_number = match_obj.group(1)
                if system_number not in target_system_numbers:
                    target_system_numbers.append(system_number)

        if not target_system_numbers:
            return None

        best_system_number: str | None = None
        best_record: MarcRecord | None = None
        best_score = 0.0
        for target_system_number in target_system_numbers:
            target_record = await self._get_record(
                self._base_to_id_mapper[target_base].format(system_number=target_system_number)
            )

            if target_record is None:
                # The dedup group names a record knihovny.cz will not serve.
                # Dropping that one member keeps the rest of the group usable;
                # a transport failure still raises and is never read as "no
                # link", which is what would delete a good link.
                continue

            comparison = await self._comparator.run(record, target_record)
            if best_record is None or comparison.overall_score > best_score:
                best_system_number = target_system_number
                best_record = target_record
                best_score = comparison.overall_score

        # The dedup group says these records belong together; the comparator
        # says how far this catalogue agrees. Disagreement below the floor is
        # reported as no link rather than as a link nobody can trust.
        if best_record is None or best_system_number is None:
            return None
        if best_score < self.config.minimum_confidence:
            return None

        return AuthorityLink(
            base=target_base,
            system_number=best_system_number,
            record=best_record,
            confidence=best_score,
        )
