from sqlalchemy import String, and_, bindparam, func, or_, text

from entities.authority_link import AuthorityLink
from entities.catalog_record import CatalogRecord
from entities.comparison import Comparison
from entities.record_review import RecordReview, ReviewStatus
from entities.validation import Validation

from .filter_spec import FilterCondition, FilterField

MATCH_QUALITY_RANGES = {
    "Excellent": (0.9, None),
    "Moderate": (0.7, 0.9),
    "Poor": (None, 0.7),
}

RELATIONSHIP_FILTERS = {
    FilterField.AuthorityLinkLinkers: (CatalogRecord.authority_links, AuthorityLink.linker),
    FilterField.AuthorityLinkBases: (CatalogRecord.authority_links, AuthorityLink.base),
    FilterField.Validators: (CatalogRecord.validations, Validation.validator),
}


def apply_conditions(query, conditions: list[FilterCondition]):
    """Apply all filter conditions to a SQLAlchemy query."""
    for c in conditions:
        query = _compile_one(query, c)
    return query


def _compile_one(query, c: FilterCondition):
    match c.field:
        case FilterField.RecordIds:
            return query.filter(CatalogRecord.id.in_(c.value))

        case FilterField.TextQuery:
            return query.filter(
                CatalogRecord.search_vector.op("@@")(func.plainto_tsquery("simple", c.value))
            )

        case FilterField.Bases:
            return query.filter(CatalogRecord.base.in_(c.value))

        case FilterField.TypeOfRecord:
            return query.filter(CatalogRecord._type_of_record.in_(c.value))

        case FilterField.BibliographicLevel:
            return query.filter(CatalogRecord._bibliographic_level.in_(c.value))

        case FilterField.Deleted:
            return query.filter(CatalogRecord.deleted == c.value)

        case FilterField.Processed:
            return query.filter(
                CatalogRecord.processed_at.isnot(None)
                if c.value
                else CatalogRecord.processed_at.is_(None)
            )

        case FilterField.ReviewStatuses:
            has_current = CatalogRecord.reviews.any(RecordReview.status == ReviewStatus.Current)
            has_bad_comparisons = CatalogRecord.comparisons.any(
                Comparison._result["overall_score"].as_float() < 0.9
            )
            has_bad_validations = CatalogRecord.validations.any(
                Validation._result["status"].as_string().notin_(["Valid", "AdditionalInfo"])
            )
            review_not_needed = and_(~has_bad_comparisons, ~has_bad_validations)
            clauses = []
            for rs in c.value:
                if rs == "ReviewNotNeeded":
                    clauses.append(review_not_needed)
                elif rs == "Unreviewed":
                    clauses.append(and_(~review_not_needed, ~has_current))
                else:
                    # Both Reviewed and PartiallyReviewed require at least one current review
                    clauses.append(and_(~review_not_needed, has_current))
            return query.filter(or_(*clauses))

        case (
            FilterField.AuthorityLinkLinkers
            | FilterField.AuthorityLinkBases
            | FilterField.Validators
        ):
            relationship, column = RELATIONSHIP_FILTERS[c.field]
            for val in c.value:
                query = query.filter(relationship.any(column == val))
            return query

        case FilterField.ComparisonBases:
            for val in c.value:
                query = query.filter(CatalogRecord.comparisons.any(Comparison.base == val))
            return query

        case FilterField.MatchQualities:
            score_col = Comparison._result["overall_score"].as_float()
            for quality in c.value:
                lo, hi = MATCH_QUALITY_RANGES.get(quality, (None, None))
                condition = None
                if lo is not None and hi is not None:
                    condition = (score_col >= lo) & (score_col < hi)
                elif lo is not None:
                    condition = score_col >= lo
                elif hi is not None:
                    condition = score_col < hi
                if condition is not None:
                    query = query.filter(CatalogRecord.comparisons.any(condition))
            return query

        case FilterField.ValidationStatuses:
            for val in c.value:
                validator, status = val.split(":", 1) if ":" in val else (None, val)
                conditions = [Validation._result["status"].as_string() == status]
                if validator:
                    conditions.append(Validation.validator == validator)
                query = query.filter(CatalogRecord.validations.any(and_(*conditions)))
            return query

        case FilterField.ValidationTargetTags:
            tag_col = Validation._result["target"]["tag"].as_string()
            for val in c.value:
                query = query.filter(CatalogRecord.validations.any(tag_col == val))
            return query

        case FilterField.ValidationReasons:
            for val in c.value:
                validator, reason = val.split(":", 1) if ":" in val else (None, val)
                conditions = [Validation._result["reason"].as_string() == reason]
                if validator:
                    conditions.append(Validation.validator == validator)
                query = query.filter(CatalogRecord.validations.any(and_(*conditions)))
            return query

        case FilterField.ScoreMin:
            score_col = Comparison._result["overall_score"].as_float()
            return query.filter(CatalogRecord.comparisons.any(score_col >= c.value))

        case FilterField.ScoreMax:
            score_col = Comparison._result["overall_score"].as_float()
            return query.filter(CatalogRecord.comparisons.any(score_col <= c.value))

        case FilterField.FieldExplanations:
            for i, val in enumerate(c.value):
                param_name = f"fe_val_{i}"
                query = query.filter(
                    text(
                        "EXISTS ("
                        "  SELECT 1 FROM comparisons c_fe,"
                        "  LATERAL jsonb_array_elements(c_fe._result->'field_results') AS elem(val)"
                        "  WHERE c_fe.main_record_id = catalog_records.id"
                        f"  AND elem.val->>'explanation' = :{param_name}"
                        ")"
                    ).bindparams(bindparam(param_name, value=val, type_=String))
                )
            return query

        case _:
            raise ValueError(f"Unhandled ORM filter: {c.field}")
