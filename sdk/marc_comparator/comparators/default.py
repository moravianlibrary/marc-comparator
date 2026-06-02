import asyncio
from collections import defaultdict
from typing import Any

from marcdantic import MarcRecord
from pydantic import BaseModel

from ._base import (
    BaseComparator,
    Explanation,
    FieldComparisonResult,
    RecordComparisonResult,
    SubfieldComparisonResult,
)
from .intiim_engine.engine import compare_records
from .intiim_engine.llm import set_ollama_url
from .intiim_engine.scoring import score_differences

_LABEL_TO_EXPLANATION: dict[str, Explanation] = {
    "IDENTICAL": Explanation.Identical,
    "NON_STANDARDIZED": Explanation.NonStandardized,
    "TYPO": Explanation.Typo,
    "INCOMPLETE": Explanation.Incomplete,
    "INCORRECT": Explanation.Incorrect,
    "MISSING": Explanation.Missing,
}


class DefaultComparatorConfig(BaseModel):
    ollama_url: str = "http://localhost:11434"
    llm_enabled: bool = False
    nonstandard_llm_enabled: bool = False
    excellent_threshold: int = 6
    moderate_threshold: int = 12


class DefaultComparator(BaseComparator):
    """
    Comparator that uses multiple checks to compare MARC records:
    - Identical Check
    - Nonstandardized Check
    - Typo Check
    - Incomplete Check
    - Incorrect Check
    - Missing Check
    """

    config_model = DefaultComparatorConfig

    def __init__(self, config: DefaultComparatorConfig):
        self.config = config
        set_ollama_url(config.ollama_url)

    def _parse_record_to_dict(self, record: MarcRecord) -> dict:
        d: dict = {"leader": record.leader, "fields": []}

        for tag, value in record.fixed_fields.root.items():
            d["fields"].append({tag: value})

        for tag, fields in record.variable_fields.root.items():
            for f in fields:
                subfields = []

                for code, values in f.subfields.items():
                    for value in values:
                        subfields.append({code: value})

                d["fields"].append(
                    {
                        tag: {
                            "ind1": (f.ind1 if f.ind1 is not None else " "),
                            "ind2": (f.ind2 if f.ind2 is not None else " "),
                            "subfields": subfields,
                        }
                    }
                )

        return d

    async def run(
        self,
        record_a: MarcRecord,
        record_b: MarcRecord,
    ) -> RecordComparisonResult:
        record_a_dict = self._parse_record_to_dict(record_a)
        record_b_dict = self._parse_record_to_dict(record_b)

        comparison = await asyncio.to_thread(
            compare_records,
            record_a_dict,
            record_b_dict,
            include_identical=True,
            llm_backend="ollama" if self.config.llm_enabled else None,
            nonstandard_llm=self.config.nonstandard_llm_enabled,
            llm_enabled=self.config.llm_enabled,
        )

        scoring = await asyncio.to_thread(score_differences, comparison.get("differences", []))
        field_score_caps = {
            f["tag"]: f.get("cap") or 10.0 for f in scoring.get("field_contributions", [])
        }
        field_scoring = {
            f["tag"]: normalize_score(
                f.get("applied", 0.0),
                excellent_threshold=self.config.excellent_threshold / 3,
                moderate_threshold=self.config.moderate_threshold / 3,
                cap=field_score_caps.get(f["tag"], 10.0),
            )
            for f in scoring.get("field_contributions", [])
        }
        subfield_scoring = {
            f"{s['tag']}|{s['code']}|{s['value_main']}": normalize_score(
                s.get("weight", 0.0),
                excellent_threshold=self.config.excellent_threshold / 3,
                moderate_threshold=self.config.moderate_threshold / 3,
                cap=field_score_caps.get(s["tag"], 10.0),
            )
            for s in scoring.get("components", [])
        }

        all_comparison_results = comparison.get("differences", []) + comparison.get("identical", [])

        field_results_groupped: dict[str, list[Any]] = {}

        for field_diff in all_comparison_results:
            tag = field_diff["tag"]
            field_results_groupped.setdefault(tag, []).append(field_diff)

        field_results: list[FieldComparisonResult] = []

        for tag, groups in field_results_groupped.items():
            # Diff results on fixed fields
            if len(groups) == 1 and groups[0].get("code") is None:
                group = groups[0]
                field_results.append(
                    FieldComparisonResult(
                        tag=group["tag"],
                        idxA=0 if group.get("value_main", "") != "" else None,
                        idxB=0 if group.get("value_test", "") != "" else None,
                        value_a=group.get("value_main") or None,
                        value_b=group.get("value_test") or None,
                        score=field_scoring.get(tag, 1.0),
                        explanation=_LABEL_TO_EXPLANATION.get(group.get("label")),
                        details=group.get("details", {}).get("reason"),
                    )
                )
                continue

            if any(group.get("code") is None for group in groups):
                continue

            indexes_A = get_field_and_subfield_indexes(
                record_a,
                tag,
                [(group["code"], group.get("value_main")) for group in groups],
            )
            indexes_B = get_field_and_subfield_indexes(
                record_b,
                tag,
                [(group["code"], group.get("value_test")) for group in groups],
            )

            subfield_results: list[SubfieldComparisonResult] = []
            for group, (idxA, idxB) in zip(groups, zip(indexes_A, indexes_B)):
                subfield_results.append(
                    SubfieldComparisonResult(
                        code=group["code"],
                        idxA=idxA[2],
                        idxB=idxB[2],
                        value_a=group.get("value_main"),
                        value_b=group.get("value_test"),
                        score=subfield_scoring.get(
                            f"{tag}|{group['code']}|{group.get('value_main')}",
                            1.0,
                        ),
                        explanation=_LABEL_TO_EXPLANATION.get(group.get("label")),
                        details=group.get("details", {}).get("reason"),
                    )
                )

            # Group subfield results by field index (idxA / idxB)
            fields_by_idx: dict[
                tuple[str, int | None, str, int | None],
                list[SubfieldComparisonResult],
            ] = defaultdict(list)
            for subfield, (idxA, idxB) in zip(subfield_results, zip(indexes_A, indexes_B)):
                fields_by_idx[(idxA[0], idxA[1], idxB[0], idxB[1])].append(subfield)

            # Build FieldComparisonResult objects
            for (
                field_tagA,
                field_idxA,
                field_tagB,
                field_idxB,
            ), subfields in fields_by_idx.items():
                # Use first subfield's tag for the field tag (all same)
                field_results.append(
                    FieldComparisonResult(
                        tag=field_tagA,
                        tagB=field_tagB if field_tagA != field_tagB else None,
                        idxA=field_idxA,
                        idxB=field_idxB,
                        score=(sum(subfield.score for subfield in subfields) / len(subfields)),
                        subfield_results=subfields,
                    )
                )

        score_30 = scoring["record_score_30_exact"]

        return RecordComparisonResult(
            overall_score=normalize_score(
                score_30,
                self.config.excellent_threshold,
                self.config.moderate_threshold,
                30,
            ),
            field_results=field_results,
        )


TAG_ALIASES_BIDIRECTIONAL = {
    "260": "264",
    "264": "260",
}


def get_field_and_subfield_indexes(
    record: MarcRecord, tag: str, subfields: list[tuple[str, str | None]]
) -> list[tuple[str, int | None, int | None]]:
    # Try main tag
    variable_fields = record.variable_fields.root.get(tag, [])
    # Fallback to alias
    used_tag = tag
    if not variable_fields and tag in TAG_ALIASES_BIDIRECTIONAL:
        used_tag = TAG_ALIASES_BIDIRECTIONAL[tag]
        variable_fields = record.variable_fields.root.get(used_tag, [])

    if not variable_fields:
        return [(tag, None, None)] * len(subfields)

    # Track used subfield indices per field
    used_subfields: dict[int, dict[str, set[int]]] = {i: {} for i in range(len(variable_fields))}
    results: list[tuple[int | None, int | None]] = []

    for code, expected_value in subfields:
        found = False

        for field_idx, vf in enumerate(variable_fields):
            values = vf.subfields.get(code, [])
            if not values:
                continue

            # Initialize set for this code if missing
            code_used = used_subfields[field_idx].setdefault(code, set())

            for sub_idx, value in enumerate(values):
                if sub_idx in code_used:
                    continue
                if expected_value is None or value == expected_value:
                    results.append((used_tag, field_idx, sub_idx))
                    code_used.add(sub_idx)
                    found = True
                    break  # stop searching this subfield

            if found:
                break  # stop searching other fields for this subfield

        if not found:
            results.append((used_tag, None, None))

    return results


def normalize_score(
    score: float,
    excellent_threshold: float,
    moderate_threshold: float,
    cap: float,
) -> float:
    """
    Piecewise linear mapping:
    0 → 1.0
    excellent_threshold → 0.9
    moderate_threshold → 0.7
    cap → 0.0
    """
    score = max(0.0, min(score, cap))

    if score <= excellent_threshold:
        t = score / excellent_threshold if excellent_threshold else 0.0
        return 1.0 - 0.1 * t

    if score <= moderate_threshold:
        t = (score - excellent_threshold) / (moderate_threshold - excellent_threshold)
        return 0.9 - 0.2 * t

    t = (score - moderate_threshold) / (cap - moderate_threshold)
    return 0.7 * (1.0 - t)
