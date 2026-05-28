from .filter_spec import FilterCondition, FilterField


def compile_conditions(conditions: list[FilterCondition]) -> tuple[str, dict]:
    """Compile filter conditions to a SQL WHERE clause for the analytics table."""
    clauses = ["TRUE"]
    params: dict = {}

    for c in conditions:
        clause, p = _compile_one(c)
        if clause:
            clauses.append(clause)
            params.update(p)

    where = "WHERE " + " AND ".join(clauses)
    return where, params


def _compile_one(c: FilterCondition) -> tuple[str | None, dict]:
    match c.field:
        case FilterField.RecordIds:
            return "id = ANY(:record_ids)", {"record_ids": c.value}

        case FilterField.TextQuery:
            # text_query is not supported on the analytics table
            return None, {}

        case FilterField.Bases:
            return "base = ANY(:bases)", {"bases": c.value}

        case FilterField.TypeOfRecord:
            return "type_of_record = ANY(:type_of_record)", {"type_of_record": c.value}

        case FilterField.BibliographicLevel:
            return "bibliographic_level = ANY(:bib_level)", {"bib_level": c.value}

        case FilterField.Deleted:
            return "is_deleted = :is_deleted", {"is_deleted": c.value}

        case FilterField.Processed:
            return "is_processed = :is_processed", {"is_processed": c.value}

        case FilterField.ReviewStatuses:
            return "review_status = ANY(:review_statuses)", {"review_statuses": c.value}

        case (
            FilterField.AuthorityLinkLinkers
            | FilterField.AuthorityLinkBases
            | FilterField.ComparisonBases
            | FilterField.MatchQualities
            | FilterField.FieldExplanations
            | FilterField.Validators
            | FilterField.ValidationStatuses
            | FilterField.ValidationTargetTags
            | FilterField.ValidationReasons
        ):
            field = c.field.value  # enum value matches the analytics column name
            return f"CAST({field} AS text[]) && :arr_{field}", {f"arr_{field}": c.value}

        case FilterField.ScoreMin:
            return (
                "EXISTS (SELECT 1 FROM unnest(overall_scores) s WHERE s >= :score_min)",
                {"score_min": c.value},
            )

        case FilterField.ScoreMax:
            return (
                "EXISTS (SELECT 1 FROM unnest(overall_scores) s WHERE s <= :score_max)",
                {"score_max": c.value},
            )

        case _:
            raise ValueError(f"Unhandled SQL filter: {c.field}")
