import asyncio
import math
from collections import defaultdict
from typing import Any, Dict, List, Set, Tuple

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
    valid_threshold: int = 6
    warning_threshold: int = 12


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
        )

        scoring = await asyncio.to_thread(
            score_differences, comparison.get("differences", [])
        )
        field_score_caps = {
            f["tag"]: f.get("cap") or 10.0
            for f in scoring.get("field_contributions", [])
        }
        field_scoring = {
            f["tag"]: normalize_score(
                f.get("applied", 0.0),
                valid_threshold=self.config.valid_threshold / 3,
                warning_threshold=self.config.warning_threshold / 3,
                cap=field_score_caps.get(f["tag"], 10.0),
            )
            for f in scoring.get("field_contributions", [])
        }
        subfield_scoring = {
            f"{s['tag']}|{s['code']}|{s["value_main"]}": normalize_score(
                s.get("weight", 0.0),
                valid_threshold=self.config.valid_threshold / 3,
                warning_threshold=self.config.warning_threshold / 3,
                cap=field_score_caps.get(s["tag"], 10.0),
            )
            for s in scoring.get("components", [])
        }

        all_comparison_results = comparison.get(
            "differences", []
        ) + comparison.get("identical", [])

        field_results_groupped: Dict[str, List[Any]] = {}

        for field_diff in all_comparison_results:
            tag = field_diff["tag"]
            field_results_groupped.setdefault(tag, []).append(field_diff)

        field_results: List[FieldComparisonResult] = []

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

            subfield_results: List[SubfieldComparisonResult] = []
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
            fields_by_idx: Dict[
                Tuple[str, int | None, str, int | None],
                List[SubfieldComparisonResult],
            ] = defaultdict(list)
            for subfield, (idxA, idxB) in zip(
                subfield_results, zip(indexes_A, indexes_B)
            ):
                fields_by_idx[(idxA[0], idxA[1], idxB[0], idxB[1])].append(
                    subfield
                )

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
                        score=(
                            sum(subfield.score for subfield in subfields)
                            / len(subfields)
                        ),
                        subfield_results=subfields,
                    )
                )

        score_30 = scoring["record_score_30_exact"]

        return RecordComparisonResult(
            overall_score=normalize_score(
                score_30,
                self.config.valid_threshold,
                self.config.warning_threshold,
                30,
            ),
            field_results=field_results,
        )


TAG_ALIASES_BIDIRECTIONAL = {
    "260": "264",
    "264": "260",
}


def get_field_and_subfield_indexes(
    record: MarcRecord, tag: str, subfields: List[Tuple[str, str | None]]
) -> List[Tuple[str, int | None, int | None]]:
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
    used_subfields: Dict[int, Dict[str, Set[int]]] = {
        i: {} for i in range(len(variable_fields))
    }
    results: List[Tuple[int | None, int | None]] = []

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
    score: float, valid_threshold: float, warning_threshold: float, cap: float
) -> float:
    """
    Piecewise logistic mapping:
    0 → 1.0
    valid → 0.9
    warning → 0.7
    cap → 0.0
    """
    score = max(0, min(score, cap))

    def logistic(x, midpoint, steepness=0.3):
        return 1 / (1 + math.exp(steepness * (x - midpoint)))

    def normalized_segment(
        x, start_x, end_x, start_y, end_y, midpoint, steepness=0.3
    ):
        """
        Smooth logistic segment,
        but exactly hits (start_x → start_y) and (end_x → end_y).
        """

        # raw logistic values at segment boundaries
        raw_start = logistic(start_x, midpoint, steepness)
        raw_end = logistic(end_x, midpoint, steepness)

        # value at x
        raw_x = logistic(x, midpoint, steepness)

        # normalize raw curve to (start_y .. end_y)
        denom = raw_end - raw_start
        if abs(denom) < 1e-12:
            return start_y
        t = (raw_x - raw_start) / denom
        return start_y + t * (end_y - start_y)

    if score <= valid_threshold:
        # map 0 → 1.0, valid → 0.9
        return normalized_segment(
            score,
            0,
            valid_threshold,
            1.0,
            0.9,
            midpoint=valid_threshold / 2,
        )

    if score <= warning_threshold:
        # map valid → 0.9, warning → 0.7
        return normalized_segment(
            score,
            valid_threshold,
            warning_threshold,
            0.9,
            0.7,
            midpoint=(valid_threshold + warning_threshold) / 2,
        )

    # final segment: warning → 0.7, 30 → 0.0
    return normalized_segment(
        score,
        warning_threshold,
        cap,
        0.7,
        0.0,
        midpoint=(warning_threshold + cap) / 2,
    )
