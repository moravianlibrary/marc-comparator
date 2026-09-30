import asyncio
from collections import defaultdict
from typing import Any

from marcdantic import MarcRecord
from pydantic import BaseModel

from ._base import (
    EXCELLENT_MATCH,
    MATCH_SCALE_MAX,
    MODERATE_MATCH,
    BaseComparator,
    Explanation,
    FieldComparisonResult,
    MatchQuality,
    RecordComparisonResult,
    SubfieldComparisonResult,
    match_from_penalty,
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


def _is_fixed_field_tag(tag: str) -> bool:
    """Whether a tag names a fixed field — the 00X block and the leader.

    MARC reserves 000-009 for data held positionally, with no indicators and no
    subfields; everything from 010 up is a variable field whose value is its
    subfields. Anything unnumbered belongs to no such block and is treated as
    variable, which is the safe side: a variable field misread as fixed is what
    puts a subfield mapping where a plain string is expected.
    """

    return tag.isdigit() and int(tag) < 10


def _match(spent: float) -> float:
    """A spent share of a budget, as a score on the match scale.

    Rounded, because these are stored: `15 * (1 - 0.8)` is 2.999999999999999
    in binary floating point, and a stored score is read back by people as
    well as by code. Four places is finer than anything displayed and matches
    what the scoring engine rounds its own output to.
    """

    return round(MATCH_SCALE_MAX * (1.0 - min(1.0, spent)), 4)


def _explain(group: dict[str, Any]) -> str | None:
    """What the engine measured about this difference, in one line.

    The reason it recorded, plus the numbers behind it where there are any.
    A label on its own — "TYPO" — says what the engine concluded; `sim` and
    `jaccard` say how close the two strings actually were, which is what
    tells a cataloguer whether to believe the conclusion. The checks that
    compare text record both; the ones that decide on structure record
    neither, so this stays a reason string for them.
    """

    details = group.get("details") or {}
    parts = [str(details["reason"])] if details.get("reason") else []

    if isinstance(details.get("sim"), (int, float)):
        parts.append(f"sim {float(details['sim']):.0f}%")
    if isinstance(details.get("jaccard"), (int, float)):
        parts.append(f"jaccard {float(details['jaccard']):.2f}")

    return ", ".join(parts) or None


class DefaultComparatorConfig(BaseModel):
    ollama_url: str = "http://localhost:11434"
    llm_enabled: bool = False
    nonstandard_llm_enabled: bool = False
    #: Where the quality bands sit on the 0-15 match scale. Both used to be
    #: penalties, read the other way round — 6 and 12 out of 30 — and they were
    #: the two ends of a curve this comparator laid over the engine's output.
    #: There is no curve now, so all they do is cut the scale into bands.
    excellent_threshold: float = EXCELLENT_MATCH
    moderate_threshold: float = MODERATE_MATCH


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

        # Every score below is the same arithmetic the record score is built
        # from, read at a different level: what share of a budget a difference
        # spent. The engine prices each difference at `cost` out of the field's
        # `cap`, and `share` is that as a fraction; a field's `spent` is the
        # sum of its differences' shares, clipped at its budget. So a subfield,
        # its field and the record are one story told three times, and a field
        # showing 7.5 means it used half of what it had.
        #
        # What stood here instead was a second curve — `normalize_score` —
        # with its own thresholds, applied on top of the engine's own hinge,
        # against a cap of 10.0 that the engine had not necessarily used. For
        # the twelve tags absent from the weight table altogether — 856, 505,
        # 520, 310, 362, 501, 550, 561, 765, 780, 810, 222 — the engine scores
        # against a budget of 1.0, and normalizing that against 10.0 showed a
        # field that had spent everything it had as 0.95 out of 1.
        field_scoring = {
            f["tag"]: _match(f["spent"]) for f in scoring.get("field_contributions", [])
        }
        subfield_shares = {
            f"{s['tag']}|{s['code']}|{s['value_main']}": min(1.0, s["share"])
            for s in scoring.get("components", [])
        }

        all_comparison_results = comparison.get("differences", []) + comparison.get("identical", [])

        field_results_groupped: dict[str, list[Any]] = {}

        for field_diff in all_comparison_results:
            tag = field_diff["tag"]
            field_results_groupped.setdefault(tag, []).append(field_diff)

        field_results: list[FieldComparisonResult] = []

        for tag, groups in field_results_groupped.items():
            # Diff results on fixed fields.
            #
            # Decided by tag, not by the absence of a subfield code: the engine
            # also emits a codeless group for a variable field it compared as a
            # whole, and its value is then the field's subfield mapping. Reading
            # that as a fixed field put a dict where a string belongs and raised
            # two string_type errors on a 336 ($a/$b/$2), which failed the
            # linker and with it the record.
            if _is_fixed_field_tag(tag) and len(groups) == 1:
                group = groups[0]
                field_results.append(
                    FieldComparisonResult(
                        tag=group["tag"],
                        idxA=0 if group.get("value_main", "") != "" else None,
                        idxB=0 if group.get("value_test", "") != "" else None,
                        value_a=group.get("value_main") or None,
                        value_b=group.get("value_test") or None,
                        score=field_scoring.get(tag, MATCH_SCALE_MAX),
                        explanation=_LABEL_TO_EXPLANATION.get(group.get("label")),
                        details=_explain(group),
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
            group_shares: list[float] = []
            # strict=True: these are parallel per-group lists built from `groups`, so a
            # length mismatch means a bug — silently comparing fewer subfields is worse.
            for group, (idxA, idxB) in zip(
                groups, zip(indexes_A, indexes_B, strict=True), strict=True
            ):
                # A group the engine reported no difference for spent nothing,
                # which is what the 0.0 default means.
                share = subfield_shares.get(f"{tag}|{group['code']}|{group.get('value_main')}", 0.0)
                group_shares.append(share)
                subfield_results.append(
                    SubfieldComparisonResult(
                        code=group["code"],
                        idxA=idxA[2],
                        idxB=idxB[2],
                        value_a=group.get("value_main"),
                        value_b=group.get("value_test"),
                        score=_match(share),
                        explanation=_LABEL_TO_EXPLANATION.get(group.get("label")),
                        details=_explain(group),
                    )
                )

            # Group subfield results by field index (idxA / idxB)
            fields_by_idx: dict[
                tuple[str, int | None, str, int | None],
                list[SubfieldComparisonResult],
            ] = defaultdict(list)
            # The shares of the same subfields, kept beside them so each field
            # instance can be scored the way the tag as a whole was: a tag that
            # occurs once then reads exactly as its `field_contributions` entry,
            # and one that occurs several times splits between them instead of
            # showing the same number on each.
            shares_by_idx: dict[tuple[str, int | None, str, int | None], list[float]] = defaultdict(
                list
            )
            for subfield, share, (idxA, idxB) in zip(
                subfield_results, group_shares, zip(indexes_A, indexes_B, strict=True), strict=True
            ):
                fields_by_idx[(idxA[0], idxA[1], idxB[0], idxB[1])].append(subfield)
                shares_by_idx[(idxA[0], idxA[1], idxB[0], idxB[1])].append(share)

            # Build FieldComparisonResult objects
            for key, subfields in fields_by_idx.items():
                field_tagA, field_idxA, field_tagB, field_idxB = key
                # Use first subfield's tag for the field tag (all same)
                field_results.append(
                    FieldComparisonResult(
                        tag=field_tagA,
                        tagB=field_tagB if field_tagA != field_tagB else None,
                        idxA=field_idxA,
                        idxB=field_idxB,
                        score=_match(sum(shares_by_idx[key])),
                        subfield_results=subfields,
                    )
                )

        overall_score = round(match_from_penalty(scoring["record_score_30_exact"]), 4)

        return RecordComparisonResult(
            overall_score=overall_score,
            quality=MatchQuality.of(
                overall_score,
                excellent=self.config.excellent_threshold,
                moderate=self.config.moderate_threshold,
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
