"""An unanswered weight is not a weight of zero.

The table is a survey: one answer per field and category, filled in by
cataloguers. Four cells came back blank, and reading a blank as 0 priced those
differences at nothing — a typo in 080 or 504, or in 600 $2, cost less than a
difference in a field nobody had ever been asked about.
"""

import json

import pytest
from marc_comparator.comparators.intiim_engine.scoring import (
    _field_overall_cap,
    _load_weights,
    _pick_weight,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    # The table is cached for the life of the process, so a test that reads it
    # from a file must not leave that behind for the next one.
    _load_weights.cache_clear()
    yield
    _load_weights.cache_clear()


def _weights_file(tmp_path, responses: dict[str, str]) -> str:
    path = tmp_path / "weights.json"
    path.write_text(json.dumps({"responses": responses}), encoding="utf-8")
    return str(path)


def test_a_blank_answer_falls_through_instead_of_pricing_at_zero(tmp_path):
    weights = _load_weights(_weights_file(tmp_path, {"field_245_typo": ""}))

    assert "field_245_typo" not in weights
    # _pick_weight's own default, which is what an unpriced difference gets.
    assert _pick_weight(weights, "245", None, "typo", default=1) == 1


def test_a_blank_subfield_answer_falls_back_to_the_field(tmp_path):
    weights = _load_weights(
        _weights_file(tmp_path, {"field_600_2_typo": "", "field_600_typo": "9"})
    )

    assert _pick_weight(weights, "600", "2", "typo") == 9


def test_an_unreadable_answer_is_left_out_and_reported(tmp_path, caplog):
    weights = _load_weights(_weights_file(tmp_path, {"field_245_typo": "nine"}))

    assert "field_245_typo" not in weights
    assert "field_245_typo" in caplog.text


def test_a_blank_cap_reads_the_same_as_an_absent_one(tmp_path):
    # This one was always harmless: _field_overall_cap already refused a cap of
    # 0, so dropping the key changes nothing.
    blank = _load_weights(_weights_file(tmp_path, {"field_250_overall": ""}))
    absent = _load_weights(_weights_file(tmp_path, {}))

    assert _field_overall_cap(blank, "250") is None
    assert _field_overall_cap(absent, "250") is None


class TestTheShippedTable:
    def test_none_of_the_four_blanks_prices_a_difference_at_zero(self):
        weights = _load_weights()

        # 080 and 504 were answered from the rest of their own rows, where
        # every other category is 9 or 10; nothing else in the table would have
        # caught a typo in either field.
        assert _pick_weight(weights, "080", None, "typo") == 10
        assert _pick_weight(weights, "504", None, "typo") == 9
        # 600 $2 was left blank on purpose: it falls back to the field answer.
        assert _pick_weight(weights, "600", "2", "typo") == 9
        # 250 likewise: an absent cap and a zero cap already read the same.
        assert _field_overall_cap(weights, "250") is None

    def test_a_typo_is_not_cheaper_than_the_other_answers_for_its_field(self):
        """What the blanks made possible: the cheapest way to be wrong.

        Scoring takes ``max_w`` over a tag's weights as its denominator, so a
        category priced far below its neighbours is not merely undercounted —
        it is the one difference in that field that barely registers.
        """

        weights = _load_weights()

        for tag in ("080", "504"):
            row = {
                category: _pick_weight(weights, tag, None, category)
                for category in ("typo", "wrong-value", "incomplete-value")
            }
            assert row["typo"] >= min(row.values()), row

    def test_every_answer_that_survives_is_a_usable_weight(self):
        assert all(isinstance(v, int) for v in _load_weights().values())


def test_the_table_is_built_once_per_path():
    _load_weights()
    first = _load_weights.cache_info().misses

    for _ in range(100):
        _load_weights()

    assert _load_weights.cache_info().misses == first
    assert _load_weights.cache_info().hits >= 100
