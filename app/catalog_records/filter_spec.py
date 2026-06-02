from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .models import RecordFilter


class FilterField(StrEnum):
    RecordIds = "record_ids"
    TextQuery = "text_query"
    Bases = "bases"
    TypeOfRecord = "type_of_record"
    BibliographicLevel = "bibliographic_level"
    Deleted = "deleted"
    Processed = "processed"
    ReviewStatuses = "review_statuses"
    AuthorityLinkLinkers = "authority_link_linkers"
    AuthorityLinkBases = "authority_link_bases"
    ComparisonBases = "comparison_bases"
    MatchQualities = "match_qualities"
    FieldExplanations = "field_explanations"
    Validators = "validators"
    ValidationStatuses = "validation_statuses"
    ValidationTargetTags = "validation_target_tags"
    ValidationReasons = "validation_reasons"
    ScoreMin = "score_min"
    ScoreMax = "score_max"


@dataclass(frozen=True)
class FilterCondition:
    field: FilterField
    value: Any


def parse_filters(filters: RecordFilter) -> list[FilterCondition]:
    """Single extraction point: RecordFilter -> list of active conditions.

    Both ORM and SQL compilers consume this list, ensuring
    every filter field is handled in exactly one place.
    """
    conditions: list[FilterCondition] = []

    if filters.record_ids:
        conditions.append(FilterCondition(FilterField.RecordIds, filters.record_ids))
    if filters.text_query:
        conditions.append(FilterCondition(FilterField.TextQuery, filters.text_query))
    if filters.bases:
        conditions.append(FilterCondition(FilterField.Bases, filters.bases))
    if filters.type_of_record:
        conditions.append(FilterCondition(FilterField.TypeOfRecord, filters.type_of_record))
    if filters.bibliographic_level:
        conditions.append(
            FilterCondition(FilterField.BibliographicLevel, filters.bibliographic_level)
        )
    if filters.deleted is not None:
        conditions.append(FilterCondition(FilterField.Deleted, filters.deleted))
    if filters.processed is not None:
        conditions.append(FilterCondition(FilterField.Processed, filters.processed))
    if filters.review_statuses:
        conditions.append(FilterCondition(FilterField.ReviewStatuses, filters.review_statuses))
    if filters.authority_link_linkers:
        conditions.append(
            FilterCondition(FilterField.AuthorityLinkLinkers, filters.authority_link_linkers)
        )
    if filters.authority_link_bases:
        conditions.append(
            FilterCondition(FilterField.AuthorityLinkBases, filters.authority_link_bases)
        )
    if filters.comparison_bases:
        conditions.append(FilterCondition(FilterField.ComparisonBases, filters.comparison_bases))
    if filters.match_qualities:
        conditions.append(FilterCondition(FilterField.MatchQualities, filters.match_qualities))
    if filters.field_explanations:
        conditions.append(
            FilterCondition(FilterField.FieldExplanations, filters.field_explanations)
        )
    if filters.validators:
        conditions.append(FilterCondition(FilterField.Validators, filters.validators))
    if filters.validation_statuses:
        conditions.append(
            FilterCondition(FilterField.ValidationStatuses, filters.validation_statuses)
        )
    if filters.validation_target_tags:
        conditions.append(
            FilterCondition(FilterField.ValidationTargetTags, filters.validation_target_tags)
        )
    if filters.validation_reasons:
        conditions.append(
            FilterCondition(FilterField.ValidationReasons, filters.validation_reasons)
        )
    if filters.score_min is not None:
        conditions.append(FilterCondition(FilterField.ScoreMin, filters.score_min))
    if filters.score_max is not None:
        conditions.append(FilterCondition(FilterField.ScoreMax, filters.score_max))

    return conditions
