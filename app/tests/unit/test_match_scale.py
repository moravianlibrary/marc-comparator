"""The comparator's score is the engine's own number, read the right way up.

The engine scores a *penalty* from 0 to 30, bigger meaning further apart. What
was shown instead was a second curve laid over it — ``normalize_score`` — with
its own thresholds, its own cap, and no relationship to the arithmetic that
produced the record score. A field could spend every point of its budget and
display as 0.95 out of 1.

There is one scale now, 0 to 15 and bigger is better, and all three levels of
it come out of the same division.
"""

import lxml.etree as etree
import pytest
from marc_comparator.comparators import (
    EXCELLENT_MATCH,
    MATCH_SCALE,
    MATCH_SCALE_MAX,
    MODERATE_MATCH,
    MatchQuality,
    RecordComparisonResult,
    match_from_penalty,
)
from marc_comparator.comparators.default import (
    DefaultComparator,
    DefaultComparatorConfig,
    _explain,
)
from marc_comparator.comparators.intiim_engine.scoring import (
    _field_max_weight,
    _field_overall_cap,
    _load_weights,
    score_differences,
)
from marcdantic import MarcRecord


def _difference(tag: str, code: str | None = "a", label: str = "INCORRECT") -> dict:
    return {"tag": tag, "code": code, "label": label, "value_main": "x", "value_test": "y"}


def _contribution(scoring: dict, tag: str) -> dict:
    return next(c for c in scoring["field_contributions"] if c["tag"] == tag)


class TestTheScaleIsTheEnginesOwn:
    def test_no_differences_is_the_top_of_the_scale(self):
        assert match_from_penalty(0.0) == MATCH_SCALE_MAX

    def test_the_engines_cap_is_the_bottom(self):
        assert match_from_penalty(30.0) == 0.0

    def test_the_bands_are_where_the_old_penalties_were(self):
        # The old curve put penalty 6 at 0.9 and penalty 12 at 0.7, which were
        # the Excellent and Moderate edges. The same two penalties, same two
        # edges, stated in the one place they now live.
        assert match_from_penalty(6.0) == EXCELLENT_MATCH
        assert match_from_penalty(12.0) == MODERATE_MATCH

    def test_the_map_is_one_to_one(self):
        scores = [match_from_penalty(p / 2) for p in range(61)]
        assert len(set(scores)) == len(scores)
        assert scores == sorted(scores, reverse=True)


class TestTheBandsAreDecidedOnce:
    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (15.0, MatchQuality.Excellent),
            (12.0, MatchQuality.Excellent),
            (11.999, MatchQuality.Moderate),
            (9.0, MatchQuality.Moderate),
            (8.999, MatchQuality.Poor),
            (0.0, MatchQuality.Poor),
        ],
    )
    def test_the_edges_belong_to_the_better_band(self, score, expected):
        assert MatchQuality.of(score) == expected

    def test_a_comparator_with_its_own_thresholds_is_obeyed(self):
        assert MatchQuality.of(10.0, excellent=10.0, moderate=5.0) == MatchQuality.Excellent

    def test_a_result_bands_itself_when_nobody_says(self):
        assert RecordComparisonResult(overall_score=13.0).quality == MatchQuality.Excellent

    def test_a_band_that_was_stated_is_not_second_guessed(self):
        # The comparator applies the configured thresholds; re-deriving the
        # band here would quietly overrule them.
        result = RecordComparisonResult(overall_score=13.0, quality=MatchQuality.Poor)

        assert result.quality == MatchQuality.Poor

    def test_a_result_says_which_scale_it_is_on(self):
        # A stored 0.9 and a stored 9.0 are both valid readings of their own
        # scale. This is the only thing that tells them apart.
        assert RecordComparisonResult(overall_score=9.0).scale == MATCH_SCALE


class TestTheEngineReportsTheBudgetItUsed:
    def test_a_tag_with_no_overall_answer_still_reports_its_cap(self):
        # 250 is priced by category but has no `field_250_overall`, so the
        # engine falls back to the largest of its own weights. It used to
        # report None here and the one caller there is substituted 10.0.
        weights = _load_weights()
        assert _field_overall_cap(weights, "250") is None

        contribution = _contribution(score_differences([_difference("250")]), "250")

        assert contribution["cap"] == float(_field_max_weight(weights, "250"))
        assert contribution["cap_source"] == "max_weight"

    def test_a_tag_nobody_priced_is_capped_at_the_default_cost(self):
        # 505 is absent from the table entirely. One unpriced difference costs
        # the default of 1 and that is the whole of the field's budget — so it
        # cannot outweigh a field somebody did price.
        contribution = _contribution(score_differences([_difference("505")]), "505")

        assert contribution["cap"] == 1.0
        assert contribution["spent"] == 1.0

    def test_a_priced_tag_reports_where_its_cap_came_from(self):
        contribution = _contribution(score_differences([_difference("245")]), "245")

        assert contribution["cap_source"] == "overall"
        assert contribution["cap"] > 0


class TestTheThreeLevelsAgree:
    def test_a_subfields_share_is_its_cost_over_the_budget(self):
        scoring = score_differences([_difference("245")])
        component = scoring["components"][0]
        cap = _contribution(scoring, "245")["cap"]

        assert component["cost"] == pytest.approx(cap * component["share"])

    def test_a_field_spends_the_sum_of_its_subfields_shares(self):
        scoring = score_differences([_difference("245", "a"), _difference("245", "b")])
        shares = sum(c["share"] for c in scoring["components"])

        assert _contribution(scoring, "245")["spent"] == pytest.approx(min(1.0, shares))

    def test_a_field_cannot_spend_more_than_it_has(self):
        many = [_difference("245", code) for code in "abcnp"]

        contribution = _contribution(score_differences(many), "245")

        assert contribution["proportional_sum"] > contribution["cap"]
        assert contribution["spent"] == 1.0
        assert contribution["applied"] == contribution["cap"]


MARC_XML = """
<record xmlns="http://www.loc.gov/MARC21/slim">
  <leader>     nam a22      a 4500</leader>
  <controlfield tag="001">mzk00001</controlfield>
  <controlfield tag="005">20170113091406.0</controlfield>
  <controlfield tag="008">120529s2012    xr a   f f    000 0 cze d</controlfield>
  <datafield tag="245" ind1="1" ind2="0">
    <subfield code="a">{title}</subfield>
  </datafield>
  <datafield tag="856" ind1="4" ind2="0">
    <subfield code="u">{url}</subfield>
  </datafield>
</record>
"""


def _record(title: str, url: str) -> MarcRecord:
    xml = MARC_XML.strip().format(title=title, url=url).encode()
    return MarcRecord.from_xml(etree.fromstring(xml))


class TestWhatTheComparatorShows:
    async def _compare(self, a: MarcRecord, b: MarcRecord):
        return await DefaultComparator(DefaultComparatorConfig()).run(a, b)

    def _field(self, result, tag: str):
        return next(f for f in (result.field_results or []) if f.tag == tag)

    async def test_two_identical_records_score_the_top_of_the_scale(self):
        record = _record("Kytice", "https://example.org/a")

        result = await self._compare(record, record)

        assert result.overall_score == MATCH_SCALE_MAX
        assert result.quality == MatchQuality.Excellent

    async def test_an_unpriced_tag_that_spent_its_budget_scores_zero(self):
        # 856 is absent from the weight table, so the engine scores it against
        # a budget of 1.0 and one difference spends the lot. Normalizing that
        # against a hardcoded 10.0 showed it as 0.95 out of 1 — a field that
        # could not be more wrong, displayed as very nearly right.
        result = await self._compare(
            _record("Kytice", "https://example.org/a"),
            _record("Kytice", "https://elsewhere.test/b"),
        )

        assert self._field(result, "856").score == 0.0

    async def test_every_score_is_on_the_one_scale(self):
        result = await self._compare(
            _record("Kytice", "https://example.org/a"),
            _record("Máj", "https://elsewhere.test/b"),
        )

        scores = [result.overall_score]
        for field in result.field_results or []:
            scores.append(field.score)
            scores.extend(sub.score for sub in field.subfield_results or [])

        assert scores
        assert all(0.0 <= score <= MATCH_SCALE_MAX for score in scores)

    async def test_a_field_reads_as_the_share_of_its_budget_left(self):
        # The one number a cataloguer can act on: half the field's budget
        # spent is half the scale.
        result = await self._compare(
            _record("Kytice", "https://example.org/a"),
            _record("Kytice", "https://elsewhere.test/b"),
        )
        field = self._field(result, "856")
        subfield = (field.subfield_results or [])[0]

        assert field.score == subfield.score


class TestWhatTheEngineMeasured:
    """A label says what the engine concluded; the numbers say how close it was."""

    def test_the_reason_is_still_reported_on_its_own(self):
        assert _explain({"details": {"reason": "missing_in_test"}}) == "missing_in_test"

    def test_a_text_comparison_carries_its_measurements(self):
        detail = _explain({"details": {"reason": "typo", "sim": 94.0, "jaccard": 0.91}})

        assert detail == "typo, sim 94%, jaccard 0.91"

    def test_measurements_without_a_reason_still_show(self):
        assert _explain({"details": {"sim": 88.0}}) == "sim 88%"

    def test_a_group_with_nothing_to_say_says_nothing(self):
        assert _explain({}) is None
        assert _explain({"details": {}}) is None

    def test_a_measurement_that_is_not_a_number_is_left_out(self):
        assert _explain({"details": {"reason": "typo", "sim": "high"}}) == "typo"
