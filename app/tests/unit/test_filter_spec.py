from catalog_records.filter_spec import FilterCondition, FilterField, parse_filters
from catalog_records.models import RecordFilter


class TestParseFilters:
    def test_empty_filter(self):
        result = parse_filters(RecordFilter())
        assert result == []

    def test_record_ids(self):
        result = parse_filters(RecordFilter(record_ids=["a", "b"]))
        assert result == [FilterCondition(FilterField.RecordIds, ["a", "b"])]

    def test_text_query(self):
        result = parse_filters(RecordFilter(text_query="hello"))
        assert result == [FilterCondition(FilterField.TextQuery, "hello")]

    def test_boolean_deleted_false(self):
        result = parse_filters(RecordFilter(deleted=False))
        assert result == [FilterCondition(FilterField.Deleted, False)]

    def test_boolean_deleted_true(self):
        result = parse_filters(RecordFilter(deleted=True))
        assert result == [FilterCondition(FilterField.Deleted, True)]

    def test_boolean_processed_none_excluded(self):
        result = parse_filters(RecordFilter(processed=None))
        assert not any(c.field == FilterField.Processed for c in result)

    def test_score_range(self):
        result = parse_filters(RecordFilter(score_min=0.5, score_max=0.9))
        fields = {c.field: c.value for c in result}
        assert fields[FilterField.ScoreMin] == 0.5
        assert fields[FilterField.ScoreMax] == 0.9

    def test_all_array_fields(self):
        f = RecordFilter(
            authority_link_linkers=["L1"],
            authority_link_bases=["B1"],
            comparison_bases=["CB1"],
            match_qualities=["Excellent"],
            field_explanations=["FE1"],
            validators=["V1"],
            validation_statuses=["Valid"],
            validation_target_tags=["856"],
            validation_reasons=["R1"],
        )
        result = parse_filters(f)
        fields = {c.field for c in result}
        assert FilterField.AuthorityLinkLinkers in fields
        assert FilterField.AuthorityLinkBases in fields
        assert FilterField.ComparisonBases in fields
        assert FilterField.MatchQualities in fields
        assert FilterField.FieldExplanations in fields
        assert FilterField.Validators in fields
        assert FilterField.ValidationStatuses in fields
        assert FilterField.ValidationTargetTags in fields
        assert FilterField.ValidationReasons in fields

    def test_multiple_conditions_combined(self):
        f = RecordFilter(bases=["MZK01"], deleted=True, text_query="test")
        result = parse_filters(f)
        assert len(result) == 3
        fields = {c.field for c in result}
        assert fields == {FilterField.TextQuery, FilterField.Bases, FilterField.Deleted}

    def test_empty_lists_excluded(self):
        f = RecordFilter(bases=[], authority_link_linkers=[], validators=[])
        result = parse_filters(f)
        assert result == []

    def test_filter_condition_is_frozen(self):
        c = FilterCondition(FilterField.Bases, ["MZK01"])
        assert c.field == FilterField.Bases
        assert c.value == ["MZK01"]
