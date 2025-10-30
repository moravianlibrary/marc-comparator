import unicodedata
from enum import StrEnum
from itertools import product
from string import punctuation
from typing import Dict, List

from marcdantic import MarcRecord
from marcdantic.constants import CONTROL_FIELDS
from marcdantic.fields import VariableField
from pydantic import BaseModel, Field

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
    rules: List[FieldRuleConfig]


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
        scores: List[float] = []
        weights: List[float] = []
        results: List[FieldComparison] = []

        for field_rule in self.config.rules:
            if not has_target(
                record_a, field_rule.tag, field_rule.subfield_codes
            ) and not has_target(
                record_b, field_rule.tag, field_rule.subfield_codes
            ):
                continue

            result = compare_records(record_a, record_b, field_rule)

            scores.append(
                sum(r.score for r in result)
                / len(result)
                * field_rule.field_weight
            )
            weights.append(field_rule.field_weight)
            results.extend(result)

        overall_score = sum(scores) / sum(weights) if weights else 1.0

        return RecordComparison(overall_score=overall_score, targets=results)


def is_control_field(tag: str) -> bool:
    return tag in CONTROL_FIELDS


def has_target(
    record: MarcRecord, tag: str, subfield_codes: List[str] | None = None
) -> bool:
    if is_control_field(tag):
        return tag in record.fixed_fields.root

    for field in record.variable_fields.root.get(tag, []):
        if subfield_codes is None:
            return True
        if any(code in field.subfields for code in subfield_codes):
            return True
    return False


def normalize(str: str) -> str:
    str = (" ".join(str.split())).strip()
    str = str.translate(str.maketrans("", "", punctuation))
    str = str.lower()
    str = unicodedata.normalize("NFKD", str)
    str = "".join(c for c in str if not unicodedata.combining(c))
    return str


def compare_values(
    code: str,
    value_a: str,
    value_b: str,
    field_rule: FieldRuleConfig,
) -> SubfieldComparison:
    if value_a == value_b:
        return SubfieldComparison(code=code, score=field_rule.match_score)

    if RuleType.Normalization in field_rule.rule_scores:
        value_a, value_b = normalize(value_a), normalize(value_b)

        if value_a == value_b:
            return SubfieldComparison(
                code=code,
                score=field_rule.rule_scores[RuleType.Normalization],
                explanation="Values match after normalization.",
            )

    return SubfieldComparison(
        code=code,
        score=0.0,
        explanation="Values do not match.",
    )


def compare_fixed_fields(
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

    result = compare_values("-", value_a, value_b, field_rule)
    return FieldComparison(
        tag=field_rule.tag,
        score=result.score,
        explanation=result.explanation,
    )


def compare_variable_fields(
    field_a: VariableField,
    field_b: VariableField,
    field_rule: FieldRuleConfig,
) -> FieldComparison:
    subfield_codes = field_rule.subfield_codes or sorted(
        set(field_a.subfields.keys()).union(field_b.subfields.keys())
    )

    scores: List[float] = []
    results: List[SubfieldComparison] = []

    for code in subfield_codes:
        values_a = field_a.subfields.get(code, [])
        values_b = field_b.subfields.get(code, [])

        if not values_a and not values_b:
            continue

        # Compare all pair combinations
        pairs = []
        for v_a, v_b in product(values_a, values_b):
            result = compare_values(code, v_a, v_b, field_rule)
            pairs.append((v_a, v_b, result.score, result))

        # Sort by best score
        pairs.sort(key=lambda x: x[2], reverse=True)

        used_a, used_b = set(), set()
        matched_scores: List[float] = []
        matched_results: List[SubfieldComparison] = []

        # Greedy best-match selection
        for v_a, v_b, score, result in pairs:
            if v_a in used_a or v_b in used_b:
                continue
            used_a.add(v_a)
            used_b.add(v_b)
            matched_scores.append(score)
            matched_results.append(result)

        # Handle unmatched values
        unmatched_a = [v for v in values_a if v not in used_a]
        unmatched_b = [v for v in values_b if v not in used_b]

        for _ in unmatched_a:
            matched_scores.append(0.0)
            matched_results.append(
                SubfieldComparison(
                    code=code,
                    score=0.0,
                    explanation="Subfield missing in record B.",
                )
            )
        for _ in unmatched_b:
            matched_scores.append(0.0)
            matched_results.append(
                SubfieldComparison(
                    code=code,
                    score=0.0,
                    explanation="Subfield missing in record A.",
                )
            )

        scores.append(
            sum(matched_scores) / len(matched_scores)
            if matched_scores
            else 0.0
        )
        results.extend(matched_results)

    return FieldComparison(
        tag=field_rule.tag,
        score=sum(scores) / len(scores) if scores else 0.0,
        subtargets=results,
    )


def compare_records(
    record_a: MarcRecord,
    record_b: MarcRecord,
    field_rule: FieldRuleConfig,
) -> List[FieldComparison]:
    if is_control_field(field_rule.tag):
        return [compare_fixed_fields(record_a, record_b, field_rule)]

    fields_a = record_a.variable_fields.root.get(field_rule.tag, [])
    fields_b = record_b.variable_fields.root.get(field_rule.tag, [])

    if not fields_a:
        return [
            FieldComparison(
                tag=field_rule.tag,
                score=field_rule.missing_field_score,
                explanation="Variable field missing in record A.",
            )
        ]

    if not fields_b:
        return [
            FieldComparison(
                tag=field_rule.tag,
                score=field_rule.missing_field_score,
                explanation="Variable field missing in record B.",
            )
        ]

    # Compare all pair combinations
    pairs = []
    for v_a, v_b in product(fields_a, fields_b):
        result = compare_variable_fields(v_a, v_b, field_rule)
        pairs.append((v_a, v_b, result.score, result))

    # Sort by best score
    pairs.sort(key=lambda x: x[2], reverse=True)

    used_a, used_b = set(), set()
    matched_scores: List[float] = []
    matched_results: List[FieldComparison] = []

    # Greedy best-match selection
    # Use id() to track VariableField instances
    for v_a, v_b, score, result in pairs:
        if id(v_a) in used_a or id(v_b) in used_b:
            continue
        used_a.add(id(v_a))
        used_b.add(id(v_b))
        matched_scores.append(score)
        matched_results.append(result)

    # Handle unmatched values
    unmatched_a = [f for f in fields_a if id(f) not in used_a]
    unmatched_b = [f for f in fields_b if id(f) not in used_b]

    for _ in unmatched_a:
        matched_scores.append(0.0)
        matched_results.append(
            FieldComparison(
                tag=field_rule.tag,
                score=field_rule.missing_field_score,
                explanation="Field missing in record B.",
            )
        )
    for _ in unmatched_b:
        matched_scores.append(0.0)
        matched_results.append(
            FieldComparison(
                tag=field_rule.tag,
                score=field_rule.missing_field_score,
                explanation="Field missing in record A.",
            )
        )

    return matched_results
