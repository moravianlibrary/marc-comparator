import asyncio
import re
from dataclasses import dataclass
from typing import Dict, List

from kramerius import KrameriusClient, KrameriusConfig, KrameriusField, Model
from marcdantic import MarcRecord
from marcdantic.selectors import IsbnActiveJq, IssnActiveJq, NbnActiveJq
from pydantic import BaseModel
from solrify import F, G

from ._base import (
    BaseValidator,
    ValidationResult,
    ValidationTarget,
    ValidityStatus,
)


class KrameriusLinksValidatorConfig(BaseModel):
    url_to_pid_pattern: str = r"https?://[^/]+/mzk/uuid/(uuid:[0-9a-fA-F-]+)"
    link_text_pattern: str = r"Digitalizovaný dokument"

    kramerius_host: str = "https://api.kramerius.mzk.cz/search"
    kramerius_client_url: str = "https://www.digitalniknihovna.cz/mzk/{pid}"
    solr_cloud: bool = False


VALIDATION_FIELD = ValidationTarget(tag="856", codes=["u", "y"])

TARGET_MODELS = [
    Model.Monograph,
    Model.MonographUnit,
    Model.Periodical,
    Model.PeriodicalVolume,
    Model.PeriodicalItem,
    Model.Supplement,
    Model.Graphic,
    Model.Map,
    Model.Sheetmusic,
    Model.SoundRecording,
    Model.Archive,
    Model.Manuscript,
]
VALID_TOP_LEVEL_MODELS = {
    Model.Monograph,
    Model.Periodical,
    Model.Graphic,
    Model.Map,
    Model.Sheetmusic,
    Model.SoundRecording,
    Model.Archive,
    Model.Manuscript,
}
FL = [
    f.value
    for f in [
        KrameriusField.OwnPidPath,
        KrameriusField.ModelPath,
        KrameriusField.Level,
    ]
]
MAX_QUERY_PARTS = 50


@dataclass
class FoundKrameriusLink:
    pid: str
    model: Model
    has_wrong_model: bool = False
    level: int = 0


class KrameriusLinksValidator(BaseValidator):
    """
    Validator to check for the presence of Kramerius links in MARC records.
    """

    config_model = KrameriusLinksValidatorConfig

    def __init__(self, config: KrameriusLinksValidatorConfig):
        self.config = config

        self.url_to_pid_regex = re.compile(config.url_to_pid_pattern)
        self.link_text_regex = re.compile(config.link_text_pattern)

        self.client = KrameriusClient(
            KrameriusConfig(
                host=config.kramerius_host, solr_cloud=config.solr_cloud
            )
        )

    async def find_kramerius_links(
        self, record: MarcRecord, current_kramerius_pids: List[str]
    ) -> List[FoundKrameriusLink]:
        links: Dict[str, FoundKrameriusLink] = {}

        raw_fields = [
            (
                KrameriusField.Barcode,
                [i.barcode for i in record.issues_selector.all],
            ),
            (KrameriusField.Isbn, record.variable_fields.query(IsbnActiveJq)),
            (KrameriusField.Issn, record.variable_fields.query(IssnActiveJq)),
            (KrameriusField.Nbn, record.variable_fields.query(NbnActiveJq)),
        ]

        field_query_parts = [
            (field, value)
            for field, values in raw_fields
            for value in (values or [])
        ]

        for i in range(0, len(field_query_parts), MAX_QUERY_PARTS):
            upper = min(i + MAX_QUERY_PARTS, len(field_query_parts))
            field_query_parts_chunk = field_query_parts[i:upper]

            query = None

            for field, values in field_query_parts_chunk:
                if query is None:
                    query = F(field, values)
                    continue

                query |= F(field, values)

            if query is None:
                break

            query = G(query) & F(KrameriusField.Model, TARGET_MODELS)

            for doc in await asyncio.to_thread(self.client.Search.search, query, fl=FL):
                root_pid = doc.own_pid_path.split("/")[0]
                root_model = Model(doc.model_path.split("/")[-1])
                has_wrong_model = root_model not in VALID_TOP_LEVEL_MODELS

                links[root_pid] = FoundKrameriusLink(
                    root_pid, root_model, has_wrong_model
                )

        for pid in current_kramerius_pids:
            docs = list(
                await asyncio.to_thread(self.client.Search.search, F(KrameriusField.Pid, pid), fl=FL),
            )
            if not docs:
                continue

            doc = docs[0]

            if doc.level != 0:
                links[pid] = FoundKrameriusLink(
                    pid,
                    model=Model(doc.model_path.split("/")[-1]),
                    level=doc.level,
                )
                continue

            root_pid = doc.own_pid_path.split("/")[0]
            root_model = Model(doc.model_path.split("/")[-1])
            has_wrong_model = root_model not in VALID_TOP_LEVEL_MODELS

            links[root_pid] = FoundKrameriusLink(
                root_pid, root_model, has_wrong_model
            )

        return list(links.values())

    async def run(self, record: MarcRecord) -> List[ValidationResult]:
        current_kramerius_pids = []
        results: List[ValidationResult] = []

        def add_partial_result(
            status: ValidityStatus = ValidityStatus.Invalid,
            reason: str | None = None,
            details: str | None = None,
            details_params: dict | None = None,
            hint: str | None = None,
        ):
            results.append(
                ValidationResult(
                    status=status,
                    target=VALIDATION_FIELD,
                    reason=reason,
                    details=details,
                    details_params=details_params,
                    hint=hint,
                )
            )

        for vf in record.variable_fields.query_fields('.["856"][]?'):
            if not any(
                self.link_text_regex.match(v)
                for v in vf.subfields.get("y", [])
            ):
                if not any(
                    self.url_to_pid_regex.match(v)
                    for v in vf.subfields.get("u", [])
                ):
                    continue

                add_partial_result(
                    status=ValidityStatus.ForReview,
                    reason="Missing link text in $y",
                    details=(
                        "Field 856 is missing expected link text "
                        f"matching pattern: {self.config.link_text_pattern}"
                    ),
                    details_params={
                        "pattern": self.config.link_text_pattern,
                    },
                    hint="Add appropriate link text to subfield $y.",
                )

            for v in vf.subfields.get("u", []):
                match = self.url_to_pid_regex.search(v)

                if match:
                    current_kramerius_pids.append(match.group(1))
                    continue

                add_partial_result(
                    reason="Invalid Kramerius link format",
                    details=(
                        f"Value '{v}' does not match expected URL pattern."
                    ),
                    details_params={
                        "value": v,
                        "pattern": self.config.url_to_pid_pattern,
                    },
                    hint=(
                        "Ensure the link follows the pattern: "
                        f"{self.config.url_to_pid_pattern}"
                    ),
                )

        found_kramerius_links = await self.find_kramerius_links(
            record, current_kramerius_pids
        )

        if not current_kramerius_pids and not found_kramerius_links:
            if not results:
                add_partial_result(
                    status=ValidityStatus.Valid,
                    reason="No Kramerius links found or expected",
                    details=(
                        "Record contains no Kramerius links, "
                        "and no matching documents exist."
                    ),
                )

            return results

        found_kramerius_pids = []

        for link in found_kramerius_links:
            if link.level > 0:
                add_partial_result(
                    reason="Kramerius link points to non-top-level document",
                    details=(
                        f"Document with PID '{link.pid}' "
                        f"and model '{link.model.value}' "
                        f"is at level {link.level} "
                        "and not a top-level document."
                    ),
                    details_params={
                        "pid": link.pid,
                        "model": link.model.value,
                        "level": str(link.level),
                    },
                    hint="Link should point to a top-level document.",
                )

            elif link.has_wrong_model:
                add_partial_result(
                    status=ValidityStatus.AdditionalInfo,
                    reason="Kramerius link points to invalid model",
                    details=(
                        f"Found top level document with PID '{link.pid}' "
                        f"that has model '{link.model.value}' "
                        "which is not a valid top-level model."
                    ),
                    details_params={
                        "pid": link.pid,
                        "model": link.model.value,
                    },
                    hint="Check integrity of the data in Kramerius.",
                )

            else:
                found_kramerius_pids.append(link.pid)

        extra_pids = set(current_kramerius_pids) - set(found_kramerius_pids)
        for pid in extra_pids:
            add_partial_result(
                reason="Link not found in Kramerius",
                details=(
                    f"PID '{pid}' is present in MARC "
                    "but not found in Kramerius."
                ),
                details_params={"pid": pid},
                hint="Remove or correct the invalid Kramerius link.",
            )

        missing_pids = set(found_kramerius_pids) - set(current_kramerius_pids)
        for pid in missing_pids:
            add_partial_result(
                reason="Missing Kramerius link in MARC",
                details=(
                    f"PID '{pid}' exists in Kramerius but not in MARC record."
                ),
                details_params={"pid": pid},
                hint="Add a corresponding 856$u for this PID.",
            )

        if not results:
            add_partial_result(
                ValidityStatus.Valid,
                reason="All Kramerius links valid",
                details=(
                    "All links are well-formed "
                    "and match existing Kramerius documents."
                ),
            )

        return results
