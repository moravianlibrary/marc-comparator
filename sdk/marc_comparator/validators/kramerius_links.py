import re
from typing import List

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


VALIDATION_FIELD = ValidationTarget(tag="856", codes=["u", "y"])


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
            KrameriusConfig(host=config.kramerius_host)
        )

    async def find_kramerius_pids(
        self, record: MarcRecord, current_kramerius_pids: List[str]
    ) -> List[str]:
        models = [
            Model.Monograph,
            Model.MonographUnit,
            Model.Periodical,
            Model.PeriodicalVolume,
            Model.PeriodicalItem,
            Model.Supplement,
            Model.Graphic,
            Model.Map,
        ]

        query = None
        for field, values in [
            (
                KrameriusField.Barcode,
                [i.barcode for i in record.issues_selector.all],
            ),
            (KrameriusField.Isbn, record.variable_fields.query(IsbnActiveJq)),
            (KrameriusField.Issn, record.variable_fields.query(IssnActiveJq)),
            (KrameriusField.Nbn, record.variable_fields.query(NbnActiveJq)),
        ]:
            if not values:
                continue

            if query is None:
                query = F(field, values)
                continue

            query |= F(field, values)

        if query is None:
            return []

        query = G(query) & F(KrameriusField.Model, models)

        pid_paths = [
            doc.own_pid_path
            for doc in self.client.Search.search(
                query,
                fl=[
                    f.value
                    for f in [
                        KrameriusField.OwnPidPath,
                        KrameriusField.ModelPath,
                    ]
                ],
            )
        ]

        pids = []

        for pid_path in pid_paths:
            split = pid_path.split("/")
            pids.append(split[-1])

        for pid in current_kramerius_pids:
            if self.client.Search.num_found(F(KrameriusField.Pid, pid)) == 1:
                pids.append(pid)

        return pids

    async def run(self, record: MarcRecord) -> List[ValidationResult]:
        current_kramerius_pids = []
        results: List[ValidationResult] = []

        def add_partial_result(
            status: ValidityStatus = ValidityStatus.Invalid,
            reason: str | None = None,
            details: str | None = None,
            hint: str | None = None,
        ):
            results.append(
                ValidationResult(
                    status=status,
                    target=VALIDATION_FIELD,
                    reason=reason,
                    details=details,
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
                    hint=(
                        "Ensure the link follows the pattern: "
                        f"{self.config.url_to_pid_pattern}"
                    ),
                )

        found_kramerius_pids = await self.find_kramerius_pids(
            record, current_kramerius_pids
        )

        if not current_kramerius_pids and not found_kramerius_pids:
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

        extra_pids = set(current_kramerius_pids) - set(found_kramerius_pids)
        for pid in extra_pids:
            add_partial_result(
                reason="Link not found in Kramerius",
                details=(
                    f"PID '{pid}' is present in MARC "
                    "but not found in Kramerius."
                ),
                hint="Remove or correct the invalid Kramerius link.",
            )

        missing_pids = set(found_kramerius_pids) - set(current_kramerius_pids)
        for pid in missing_pids:
            add_partial_result(
                reason="Missing Kramerius link in MARC",
                details=(
                    f"PID '{pid}' exists in Kramerius but not in MARC record."
                ),
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
