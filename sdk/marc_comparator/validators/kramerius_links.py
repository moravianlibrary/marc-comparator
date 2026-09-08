import asyncio
import json
import logging
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from kramerius import KrameriusClient, KrameriusConfig, KrameriusField, Model
from marcdantic import MarcRecord
from marcdantic.fields import VariableField
from marcdantic.selectors import IsbnActiveJq, IssnActiveJq, NbnActiveJq
from pydantic import BaseModel
from solrify import F, G

from ..reports import ReportFile
from ._base import (
    BaseValidator,
    ReportInput,
    ValidationResult,
    ValidationTarget,
    ValidityStatus,
)


class KrameriusLinksValidatorConfig(BaseModel):
    url_to_pid_pattern: str = (
        r"https?://(?:www\.)?digitalniknihovna\.cz/mzk/uuid/(?P<pid>uuid:[0-9a-fA-F-]+)(?:\?.*)?"
    )
    url_to_pid_wrong_path_pattern: str = (
        r"https?://(?:www\.)?digitalniknihovna\.cz/mzk/[^/]+/(?P<pid>uuid:[0-9a-fA-F-]+)(?:\?.*)?"
    )
    url_to_pid_fallback_pattern: str = r"https?://[^/]+/.*?(?P<pid>uuid:[0-9a-fA-F-]+)(?:\?.*)?"
    link_text_pattern: str = r"Digitalizovaný dokument"

    kramerius_host: str = "https://api.kramerius.mzk.cz/search"
    kramerius_client_url: str = "https://www.digitalniknihovna.cz/mzk/uuid/{pid}"
    solr_cloud: bool = True
    search_page_size: int = 10

    #: An identifier should resolve to one document. When it resolves to more, the
    #: extra matches are almost always wrong metadata in Kramerius — MZK's index has
    #: ČNB numbers shared by dozens to hundreds of unrelated documents. Those hits are
    #: not turned into links; they are reported for review instead.
    max_documents_per_identifier: int = 1


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
        # Returned so each hit can be attributed back to the identifier that matched
        # it, which is what lets an unreliable identifier be dropped on its own.
        KrameriusField.Barcode,
        KrameriusField.Isbn,
        KrameriusField.Issn,
        KrameriusField.Nbn,
    ]
]
MAX_QUERY_PARTS = 50

#: The KrameriusDocument attribute carrying each identifier we search on.
IDENTIFIER_DOC_ATTR = {
    KrameriusField.Barcode: "barcode",
    KrameriusField.Isbn: "isbn",
    KrameriusField.Issn: "issn",
    KrameriusField.Nbn: "nbn",
}

#: How many candidate PIDs to name in a review result. The identifier is reported
#: alongside them, so the full set stays one Solr query away.
PIDS_IN_REVIEW_SAMPLE = 10

logger = logging.getLogger(__name__)

#: Standard 856 $y link text written for added/replaced links.
STANDARD_LINK_TEXT = "Digitalizovaný dokument"


@dataclass
class FoundKrameriusLink:
    pid: str
    model: Model
    has_wrong_model: bool = False
    level: int = 0


@dataclass
class AmbiguousIdentifier:
    """
    An identifier that resolved to more Kramerius documents than a record can have.

    Its hits are withheld rather than proposed as links: one identifier pointing at
    several unrelated documents is a metadata error on the Kramerius side, and which
    (if any) of them belongs to the record is a judgement call for a curator.
    """

    #: None when the hits matched no searched value verbatim.
    field: KrameriusField | None
    values: list[str]
    pids: list[str]


class KrameriusLinksValidator(BaseValidator):
    """
    Validator to check for the presence of Kramerius links in MARC records.
    """

    config_model = KrameriusLinksValidatorConfig
    can_generate_report = True

    def __init__(self, config: KrameriusLinksValidatorConfig):
        self.config = config

        self.url_to_pid_regex = re.compile(config.url_to_pid_pattern)
        self.url_to_pid_wrong_path_regex = re.compile(config.url_to_pid_wrong_path_pattern)
        self.url_to_pid_fallback_regex = re.compile(config.url_to_pid_fallback_pattern)
        self.link_text_regex = re.compile(config.link_text_pattern)

        self.client = KrameriusClient(
            KrameriusConfig(
                host=config.kramerius_host,
                solr_cloud=config.solr_cloud,
                search_page_size=config.search_page_size,
            )
        )

    async def find_kramerius_links(
        self, record: MarcRecord, current_kramerius_pids: list[str]
    ) -> tuple[list[FoundKrameriusLink], list[AmbiguousIdentifier]]:
        links: dict[str, FoundKrameriusLink] = {}

        raw_fields = [
            (
                KrameriusField.Barcode,
                [i.barcode for i in record.issues_selector.all if i.barcode],
            ),
            (KrameriusField.Isbn, record.variable_fields.query(IsbnActiveJq)),
            (KrameriusField.Issn, record.variable_fields.query(IssnActiveJq)),
            (KrameriusField.Nbn, record.variable_fields.query(NbnActiveJq)),
        ]

        field_query_parts = [
            (field, value) for field, values in raw_fields for value in (values or [])
        ]

        searched_values: dict[KrameriusField, set[str]] = defaultdict(set)
        for field, value in field_query_parts:
            searched_values[field].add(value)

        # Hits grouped by the identifier that produced them. None collects hits that
        # match no searched value verbatim (a normalisation difference, say) — they are
        # kept, but subject to the same plausibility cap as any single identifier.
        roots_by_identifier: dict[KrameriusField | None, dict[str, FoundKrameriusLink]] = (
            defaultdict(dict)
        )

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
                # Both paths run root -> leaf, so the root's model is the first element.
                # Taking the last one named the leaf, which wrongly flagged every parent
                # reached via a child hit as non-linkable.
                root_model = Model(doc.model_path.split("/")[0])
                has_wrong_model = root_model not in VALID_TOP_LEVEL_MODELS
                link = FoundKrameriusLink(root_pid, root_model, has_wrong_model)

                matched = [
                    field
                    for field, attr in IDENTIFIER_DOC_ATTR.items()
                    if searched_values[field] & set(getattr(doc, attr) or [])
                ]
                for field in matched or [None]:
                    roots_by_identifier[field][root_pid] = link

        ambiguous: list[AmbiguousIdentifier] = []
        for field, roots in roots_by_identifier.items():
            if len(roots) > self.config.max_documents_per_identifier:
                values = sorted(searched_values.get(field, set())) if field else []
                logger.warning(
                    "%s matched %d Kramerius documents for %s — withholding them for "
                    "review; an identifier shared by several documents is a metadata "
                    "error on the Kramerius side",
                    field.value if field else "Unattributed hits",
                    len(roots),
                    values or "-",
                )
                ambiguous.append(
                    AmbiguousIdentifier(field=field, values=values, pids=sorted(roots))
                )
                continue

            links.update(roots)

        for pid in current_kramerius_pids:
            docs = list(
                await asyncio.to_thread(
                    self.client.Search.search, F(KrameriusField.Pid, pid), fl=FL
                ),
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
            # Root model is the first element of the path, not the leaf's.
            root_model = Model(doc.model_path.split("/")[0])
            has_wrong_model = root_model not in VALID_TOP_LEVEL_MODELS

            links[root_pid] = FoundKrameriusLink(root_pid, root_model, has_wrong_model)

        return list(links.values()), ambiguous

    async def run(self, record: MarcRecord) -> list[ValidationResult]:
        current_kramerius_pids: list[str] = []
        pid_field_index: dict[str, int] = {}
        # PIDs extracted from URLs with wrong path or wrong server
        url_issue_pids: dict[str, dict] = {}
        results: list[ValidationResult] = []

        def add_result(
            status: ValidityStatus = ValidityStatus.Invalid,
            reason: str | None = None,
            params: dict | None = None,
            field_index: int | None = None,
        ):
            results.append(
                ValidationResult(
                    status=status,
                    target=ValidationTarget(
                        tag=VALIDATION_FIELD.tag,
                        codes=VALIDATION_FIELD.codes,
                        field_index=field_index,
                    ),
                    reason=reason,
                    params=params,
                )
            )

        for field_idx, vf in enumerate(record.variable_fields.query_fields('.["856"][]?')):
            if not any(self.link_text_regex.match(v) for v in vf.subfields.get("y", [])):
                if not any(self.url_to_pid_regex.match(v) for v in vf.subfields.get("u", [])):
                    continue

                add_result(
                    status=ValidityStatus.ForReview,
                    reason="missing_link_text",
                    params={"pattern": self.config.link_text_pattern},
                    field_index=field_idx,
                )

            for v in vf.subfields.get("u", []):
                match = self.url_to_pid_regex.search(v)

                if match:
                    pid = match.group("pid")
                    current_kramerius_pids.append(pid)
                    pid_field_index.setdefault(pid, field_idx)
                    continue

                wrong_path_match = self.url_to_pid_wrong_path_regex.search(v)

                if wrong_path_match:
                    pid = wrong_path_match.group("pid")
                    current_kramerius_pids.append(pid)
                    pid_field_index.setdefault(pid, field_idx)
                    url_issue_pids[pid] = {
                        "type": "wrong_path",
                        "value": v,
                        "field_index": field_idx,
                    }
                    continue

                fallback_match = self.url_to_pid_fallback_regex.search(v)

                if fallback_match:
                    pid = fallback_match.group("pid")
                    current_kramerius_pids.append(pid)
                    pid_field_index.setdefault(pid, field_idx)
                    url_issue_pids[pid] = {
                        "type": "wrong_server",
                        "value": v,
                        "field_index": field_idx,
                    }
                    continue

                add_result(
                    reason="invalid_link_format",
                    params={
                        "value": v,
                        "url": self.config.kramerius_client_url,
                    },
                    field_index=field_idx,
                )

        found_kramerius_links, ambiguous_identifiers = await self.find_kramerius_links(
            record, current_kramerius_pids
        )

        for ambiguous in ambiguous_identifiers:
            add_result(
                status=ValidityStatus.ForReview,
                reason="identifier_matches_multiple_documents",
                params={
                    "identifier": ambiguous.field.value if ambiguous.field else "-",
                    "values": ", ".join(ambiguous.values) or "-",
                    "count": str(len(ambiguous.pids)),
                    "pids": ", ".join(ambiguous.pids[:PIDS_IN_REVIEW_SAMPLE]),
                },
            )

        if not current_kramerius_pids and not found_kramerius_links:
            if not results:
                add_result(
                    status=ValidityStatus.Valid,
                    reason="no_links_found_or_expected",
                )

            return results

        found_kramerius_pids = []
        valid_kramerius_pids = []

        for link in found_kramerius_links:
            found_kramerius_pids.append(link.pid)

            if link.level > 0:
                add_result(
                    reason="non_top_level_document",
                    params={
                        "pid": link.pid,
                        "model": link.model.value,
                        "level": str(link.level),
                    },
                )

            elif link.has_wrong_model:
                add_result(
                    status=ValidityStatus.AdditionalInfo,
                    reason="non_linkable_model",
                    params={
                        "pid": link.pid,
                        "model": link.model.value,
                    },
                )

            else:
                valid_kramerius_pids.append(link.pid)

        current_set = set(current_kramerius_pids)
        found_set = set(found_kramerius_pids)
        valid_set = set(valid_kramerius_pids)

        for pid in current_set & valid_set:
            issue = url_issue_pids.get(pid)
            if issue:
                if issue["type"] == "wrong_path":
                    reason = "wrong_path_found"
                    status = ValidityStatus.AdditionalInfo
                else:
                    reason = "wrong_server_found"
                    status = ValidityStatus.Invalid
                add_result(
                    status=status,
                    reason=reason,
                    params={
                        "pid": pid,
                        "value": issue["value"],
                        "url": self.config.kramerius_client_url,
                    },
                    field_index=issue["field_index"],
                )
            else:
                add_result(
                    status=ValidityStatus.Valid,
                    reason="valid_link",
                    params={"pid": pid},
                    field_index=pid_field_index.get(pid),
                )

        for pid in current_set - found_set:
            issue = url_issue_pids.get(pid)
            if issue:
                if issue["type"] == "wrong_path":
                    reason = "wrong_path_not_found"
                    status = ValidityStatus.AdditionalInfo
                else:
                    reason = "wrong_server_not_found"
                    status = ValidityStatus.Invalid
                add_result(
                    status=status,
                    reason=reason,
                    params={
                        "pid": pid,
                        "value": issue["value"],
                        "url": self.config.kramerius_client_url,
                    },
                    field_index=issue["field_index"],
                )
            else:
                add_result(
                    reason="link_not_found",
                    params={"pid": pid},
                    field_index=pid_field_index.get(pid),
                )

        for pid in valid_set - current_set:
            add_result(
                reason="missing_link_in_marc",
                params={"pid": pid},
            )

        return results

    # ── report generation ──────────────────────────────────────────────────
    #
    # Turn the stored not-valid results into Aleph sequential (.seq) repair
    # files (REPLACE-ALL mode: every 856 for a sysno is wiped and reloaded from
    # the emitted lines) plus a delete list for sysnos left with no 856 fields.
    # All changes for one record are grouped and applied in a single pass so
    # conflicting edits to the same 856 set do not overwrite each other.
    #
    # reason → action:
    #   missing_link_in_marc  → add a new correct 856
    #   wrong_server_found    → remove the wrong-server field + add a correct one
    #   wrong_path_found      → replace $u at field_index with the correct URL
    #   wrong_path_not_found  → replace $u at field_index with the correct URL
    #   missing_link_text     → add $y (standard link text) at field_index
    #   link_not_found        → remove the broken field at field_index
    # Non-repairable reasons (invalid_link_format, wrong_server_not_found,
    # non_linkable_model, non_top_level_document,
    # identifier_matches_multiple_documents) are left untouched.

    def _make_url(self, params: dict[str, str]) -> str:
        pid = params.get("pid", "")
        template = params.get("url") or self.config.kramerius_client_url
        return template.replace("{pid}", pid)

    def _build_changes(self, results: Iterable[ValidationResult]) -> dict:
        changes: dict = {"modifications": [], "removals": set(), "additions": []}
        for result in results:
            reason = result.reason
            params = result.params or {}
            field_index = result.target.field_index

            if reason == "missing_link_in_marc":
                changes["additions"].append({"u": self._make_url(params), "y": STANDARD_LINK_TEXT})
            elif reason == "wrong_server_found":
                if field_index is not None:
                    changes["removals"].add(field_index)
                changes["additions"].append({"u": self._make_url(params), "y": STANDARD_LINK_TEXT})
            elif reason in ("wrong_path_found", "wrong_path_not_found"):
                changes["modifications"].append(
                    {
                        "field_index": field_index,
                        "action": "replace_u",
                        "new_u": self._make_url(params),
                    }
                )
            elif reason == "missing_link_text":
                changes["modifications"].append(
                    {"field_index": field_index, "action": "add_y", "new_y": STANDARD_LINK_TEXT}
                )
            elif reason == "link_not_found" and field_index is not None:
                changes["removals"].add(field_index)
            # other reasons are not auto-repairable — leave the field as-is
        return changes

    def _apply_changes(
        self,
        fields: list[VariableField],
        changes: dict,
        errors: list[dict],
        catalog_record_id: str,
    ) -> list[VariableField]:
        # Step 1 — in-place modifications (indices stay valid).
        for mod in changes["modifications"]:
            idx = mod["field_index"]
            if idx is None or idx >= len(fields):
                errors.append(
                    {
                        "catalog_record_id": catalog_record_id,
                        "error": (
                            f"modification field_index {idx} out of range "
                            f"({len(fields)} 856 fields) — skipping"
                        ),
                    }
                )
                continue
            if mod["action"] == "replace_u":
                fields[idx].subfields["u"] = [mod["new_u"]]
            elif mod["action"] == "add_y":
                fields[idx].subfields["y"] = [mod["new_y"]]

        # Step 2 — drop removed fields (by original index).
        removals = changes["removals"]
        kept = [f for i, f in enumerate(fields) if i not in removals]

        # Step 3 — append additions, skipping any $u already present (Aleph
        # replaces all 856, so a duplicate $u would commit a duplicate link).
        existing_us = {u for f in kept for u in f.subfields.get("u", [])}
        for add in changes["additions"]:
            if add["u"] in existing_us:
                continue
            kept.append(
                VariableField(ind1="4", ind2="1", subfields={"u": [add["u"]], "y": [add["y"]]})
            )
            existing_us.add(add["u"])

        return kept

    @staticmethod
    def _field_to_seq_line(sysno: str, field: VariableField) -> str:
        ind1 = field.ind1 or " "
        ind2 = field.ind2 or " "
        subfields = "".join(
            f"$${code}{value}" for code, values in field.subfields.items() for value in values
        )
        return f"{sysno} {VALIDATION_FIELD.tag}{ind1}{ind2} L {subfields}"

    def generate_report(self, records: Iterable[ReportInput]) -> list[ReportFile]:
        seq_lines_by_base: dict[str, list[str]] = defaultdict(list)
        delete_sysnos_by_base: dict[str, list[str]] = defaultdict(list)
        errors: list[dict] = []

        for record in records:
            try:
                # 'MZK01-001974304' → doc number '001974304'
                doc_number = record.catalog_record_id.split("-", 1)[-1]
                sysno = doc_number.zfill(9)

                changes = self._build_changes(record.results)
                if not (changes["modifications"] or changes["removals"] or changes["additions"]):
                    # No repairable results for this record — leave it alone.
                    continue

                fields = record.marc.variable_fields.query_fields('.["856"][]?')
                final_fields = self._apply_changes(
                    list(fields), changes, errors, record.catalog_record_id
                )

                if final_fields:
                    for field in final_fields:
                        seq_lines_by_base[record.base].append(self._field_to_seq_line(sysno, field))
                else:
                    # Every 856 removed, none added — needs deletion.
                    delete_sysnos_by_base[record.base].append(sysno)
            except Exception as exc:  # noqa: BLE001 - report, don't abort the batch
                errors.append({"catalog_record_id": record.catalog_record_id, "error": str(exc)})

        report_files: list[ReportFile] = []
        for base, lines in sorted(seq_lines_by_base.items()):
            report_files.append(
                ReportFile(
                    filename=f"aleph_seq_{base}.seq",
                    content=("\n".join(lines) + "\n").encode("utf-8"),
                    content_type="text/plain",
                )
            )
        for base, sysnos in sorted(delete_sysnos_by_base.items()):
            report_files.append(
                ReportFile(
                    filename=f"aleph_delete_856_{base}.txt",
                    content=("\n".join(sorted(sysnos)) + "\n").encode("utf-8"),
                    content_type="text/plain",
                )
            )
        if errors:
            report_files.append(
                ReportFile(
                    filename="errors.json",
                    content=json.dumps(errors, indent=2, ensure_ascii=False).encode("utf-8"),
                    content_type="application/json",
                )
            )

        return report_files
