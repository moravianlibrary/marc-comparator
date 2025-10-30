import re
import unicodedata
from collections import Counter
from enum import StrEnum
from itertools import product
from string import punctuation
from typing import Dict, List, Set

from marcdantic import MarcRecord
from marcdantic.constants import CONTROL_FIELDS
from marcdantic.fields import VariableField
from pydantic import BaseModel, Field, model_validator

from ._base import (
    BaseComparator,
    FieldComparison,
    RecordComparison,
    SubfieldComparison,
)


class RuleType(StrEnum):
    Normalization = "Normalization"
    # TODO: Implement these rules ?
    # WhitespaceNormalization = "WhitespaceNormalization"
    # PunctuationNormalization = "PunctuationNormalization"
    # CaseNormalization = "CaseNormalization"
    # DiacriticNormalization = "DiacriticNormalization"
    # AlternateTagMatch = "AlternateTagMatch"
    # PrefixMatching = "PrefixMatching"
    # TermOrderMismatch = "TermOrderMismatch"
    # FormatMismatch = "FormatMismatch"


class FieldRuleConfig(BaseModel):
    """
    Configuration for rule-based MARC field comparison.
    Defines which normalization and matching rules apply to a specific field,
    along with optional rule-specific parameters.
    """

    tag: str = Field(
        ...,
        description=(
            "The MARC field tag this configuration applies to (e.g. '245')."
        ),
    )
    subfield_codes: List[str] | None = Field(
        default=None,
        description=(
            "Specific subfield codes (e.g. ['a', 'b']). "
            "If not set, applies to all subfields."
        ),
    )

    match_score: float = Field(default=1.0, ge=0.0)
    missing_field_score: float = Field(default=0.0, ge=0.0)
    missing_subfield_score: float = Field(default=0.0, ge=0.0)
    mismatch_score: float = Field(default=0.0, ge=0.0)
    rule_scores: Dict[RuleType, float] = Field(
        ...,
        description=(
            "Expected score contribution (0.0-1.0) "
            "for each rule when it applies.\n"
            "Rules not included are considered inactive.\n"
            "A lower value represents a more severe penalty."
        ),
    )

    field_weight: float = Field(
        default=1.0,
        ge=0.0,
        description=(
            "Relative weight of this field in the overall comparison score."
        ),
    )

    # Optional rule parameters
    # alternate_tag: str | None = Field(
    #     default=None,
    #     description="Required if AlternateTagMatch rule is active. "
    #     "Specifies the allowed alternate tag.",
    # )
    # prefix_length: int = Field(
    #     default=3,
    #     ge=1,
    #     description="Used by PrefixMatching rule. "
    #     "Defines how many initial characters to compare.",
    # )
    # format_patterns: List[str] | None = Field(
    #     default=None,
    #     description="Required if FormatMismatch rule is active. "
    #     "List of regex patterns defining allowed formats.",
    # )

    # @model_validator(mode="after")
    # def validate_rule_dependencies(
    #     cls, model: "FieldRuleConfig"
    # ) -> "FieldRuleConfig":
    #     """
    #     Ensure that dependent parameters are provided
    #     when relevant rules are active.
    #     """
    #     active_rules: Set[RuleType] = {
    #         rule
    #         for rule in RuleType
    #         if (
    #             not model.rule_weights
    #             or model.rule_weights.get(rule, 1.0) > 0.0
    #         )
    #     }

    #     if (
    #         RuleType.AlternateTagMatch in active_rules
    #         and not model.alternate_tag
    #     ):
    #         raise ValueError(
    #             "FieldConfig: 'alternate_tag' must be specified "
    #             "when AlternateTagMatch is enabled."
    #         )

    #     if (
    #         RuleType.FormatMismatch in active_rules
    #         and not model.format_patterns
    #     ):
    #         raise ValueError(
    #             "FieldConfig: 'format_patterns' must be specified "
    #             "when FormatMismatch is enabled."
    #         )

    #     return model


class RuleBasedComparatorConfig(BaseModel):
    field_rules: List[FieldRuleConfig]


class RuleBasedComparator(BaseComparator):
    """
    Comparator that compares MARC records by using various normalizations.
    """

    config_model = RuleBasedComparatorConfig

    def __init__(self, config: RuleBasedComparatorConfig):
        self.config = config

    async def run(
        self,
        record_a: MarcRecord,
        record_b: MarcRecord,
    ):
        count, score = 0, 0.0

        for field_rule in self.config.field_rules:
            if not _has_target(
                record_a, field_rule.tag, field_rule.subfield_codes
            ) and not _has_target(
                record_b, field_rule.tag, field_rule.subfield_codes
            ):
                continue

            score += _compare_records(record_a, record_b, field_rule)
            count += 1

        overall_score = score / count if count > 0 else 1.0

        return RecordComparison(
            overall_score=overall_score,
            summary=f"Compared {count} fields using rule-based comparator.",
        )


def _is_control_field(tag: str) -> bool:
    return tag in CONTROL_FIELDS


def _has_target(
    record: MarcRecord, tag: str, subfield_codes: List[str] | None = None
) -> bool:
    if _is_control_field(tag):
        return tag in record.fixed_fields.root

    for field in record.variable_fields.root.get(tag, []):
        if subfield_codes is None:
            return True
        if any(code in field.subfields for code in subfield_codes):
            return True
    return False


def _compare_values(
    code: str,
    value_a: str,
    value_b: str,
    field_rule: FieldRuleConfig,
) -> List[SubfieldComparison]:
    if value_a == value_b:
        return

    if 

    return 0.0, "Values do not match."


def _compare_fixed_fields(
    record_a: MarcRecord,
    record_b: MarcRecord,
    field_rule: FieldRuleConfig,
) -> FieldComparison:
    value_a = record_a.fixed_fields.root.get(field_rule.tag)
    value_b = record_b.fixed_fields.root.get(field_rule.tag)

    if value_a is None:
        return FieldComparison(
            tag=field_rule.tag,
            score=0.0,
            explanation="Fixed field missing in record A.",
        )

    if value_b is None:
        return FieldComparison(
            tag=field_rule.tag,
            score=0.0,
            explanation="Fixed field missing in record B.",
        )

    score, explanation = _compare_values(value_a, value_b, field_rule)
    return FieldComparison(
        tag=field_rule.tag,
        score=score,
        explanation=explanation,
    )


def _compare_variable_fields(
    field_a: VariableField,
    field_b: VariableField,
    field_rule: FieldRuleConfig,
) -> List[FieldComparison]:
    subfield_codes = field_rule.subfield_codes or sorted(
        set(field_a.subfields.keys()).union(field_b.subfields.keys())
    )

    results: List[SubfieldComparison] = []

    for code in subfield_codes:
        values_a = field_a.subfields.get(code, [])
        values_b = field_b.subfields.get(code, [])

        if not values_a and not values_b:
            continue

        # Compare all pair combinations
        pairs = []
        for v_a, v_b in product(values_a, values_b):
            score, explanation = _compare_values(v_a, v_b, field_rule)
            pairs.append((v_a, v_b, score, explanation))

        # Sort by best score
        pairs.sort(key=lambda x: x[2], reverse=True)

        used_a, used_b = set(), set()
        matched_scores: List[float] = []
        explanations: List[str] = []

        # Greedy best-match selection
        for v_a, v_b, score, explanation in pairs:
            if v_a in used_a or v_b in used_b:
                continue
            used_a.add(v_a)
            used_b.add(v_b)
            matched_scores.append(score)
            explanations.append(explanation)

        # Handle unmatched values
        unmatched_a = [v for v in values_a if v not in used_a]
        unmatched_b = [v for v in values_b if v not in used_b]

        for _ in unmatched_a:
            matched_scores.append(0.0)
            explanations.append("Missing in record B.")
        for _ in unmatched_b:
            matched_scores.append(0.0)
            explanations.append("Missing in record A.")

        # Aggregate score for this subfield code
        avg_score = (
            sum(matched_scores) / len(matched_scores)
            if matched_scores
            else 0.0
        )

        results.append(SubfieldComparison(code=code, score=avg_score))

    return results


def _compare_records(
    record_a: MarcRecord,
    record_b: MarcRecord,
    field_rule: FieldRuleConfig,
) -> List[FieldComparison]:
    result = FieldComparison(
        tag=field_rule.tag,
        codes=field_rule.subfield_codes,
        score=0.0,
    )

    if _is_control_field(field_rule.tag):
        return [_compare_fixed_fields(record_a, record_b, field_rule)]

    fields_a = record_a.variable_fields.root.get(field_rule.tag, [])
    fields_b = record_b.variable_fields.root.get(field_rule.tag, [])

    if not fields_a:
        result.explanation = "Variable field missing in record A."
        return [result]

    if not fields_b:
        result.explanation = "Variable field missing in record B."
        return [result]

    # Build score matrix for all possible field pairings
    field_pair_scores = []
    for f_a, f_b in product(fields_a, fields_b):
        subfield_results = _compare_variable_fields(f_a, f_b, field_rule)
        score = (
            sum(sf.score for sf in subfield_results) / len(subfield_results)
            if subfield_results
            else 0.0
        )
        field_pair_scores.append((f_a, f_b, subfield_results, score))

    field_pair_scores.sort(key=lambda x: x[3], reverse=True)

    used_a, used_b = set(), set()
    results: List[FieldComparison] = []

    for f_a, f_b, subfield_results, score in field_pair_scores:
        if f_a in used_a or f_b in used_b:
            continue
        used_a.add(f_a)
        used_b.add(f_b)

        explanation = f"Matched with score {score:.2f}"
        results.append(
            FieldComparison(
                tag=field_rule.tag,
                score=score,
                explanation=explanation,
                subtargets=subfield_results,
            )
        )

    # Handle unmatched fields on either side
    for f_a in fields_a:
        if f_a not in used_a:
            results.append(
                FieldComparison(
                    tag=field_rule.tag,
                    score=0.0,
                    explanation="Field missing in record B.",
                )
            )

    for f_b in fields_b:
        if f_b not in used_b:
            results.append(
                FieldComparison(
                    tag=field_rule.tag,
                    score=0.0,
                    explanation="Field missing in record A.",
                )
            )

    return results
