# Linking candidates and cataloguer review

This page describes the current linking model. Scores use the comparator's
0–15 match scale; higher means a closer match. A shared identifier is evidence
for retrieval, not proof that two records describe the same work.

For each main record and target base, `authority_links` stores one answer at
rank 0. The answer may be `Linked`, or it may explain why no link is accepted:
`BelowFloor`, `Conflicting`, `Refused`, `NoCandidate`, or `LookupFailed`.
Additional ranked rows are `Rejected` candidates considered but not selected.
`candidate_count` records how many candidates were considered even when most
were pruned from storage. The candidate's `(authority_base,
authority_sysno)` is its stable identity; `rank` can change on a relink.
Candidate MARC is retained separately, so review does not require a candidate
to become a catalog record.

The default `confident_threshold` is 12/15. When an accepted link scores below
it, the system retains its runner-ups. Above it, a runner-up is kept when it is
within `candidate_margin` points of the winner; the current default margin is
1.5. These thresholds are settings, and the margin is an uncalibrated default.
Changing thresholds can change the accepted machine link on a subsequent
linking pass. When it does, the rank-0 row remains and records the outcome.

Cataloguers with `ReviewRecords` permission can create, list and withdraw
claims through `/authority-linking/records/{main_record_id}/claims`. A claim is
keyed by the main record, target base and candidate natural key. `SameWork`
chooses that candidate even when the linker preferred another. `NotSameWork`
rules that candidate out; it does not automatically accept the next runner-up.
Claims persist across linking runs. The API records a verdict immediately and
enqueues a scoped linking pass to refresh machine outcomes. `needs_review` is
an advisory flag when evidence moves against an accepted claim; it never
withdraws the claim. Record search and plots expose the review flag as a facet.
Candidate MARC can be read at
`/authority-linking/candidates/{authority_base}/{authority_sysno}/marc` with
`ReadRecords` permission. The selected candidate's field comparison is
calculated on demand at
`/authority-linking/records/{main_base}/{main_sysno}/candidates/{authority_base}/{authority_sysno}/comparison`;
it does not create a persisted `Comparison` row.

Built-in linkers report `comparison.overall_score` as confidence. A custom
linker should use a comparable 0–15 score and provide retrieval provenance so
cross-linker ranking remains interpretable. Scoring and margin calibration
requires cataloguer judgments and is scheduled after release in the
[execution plan](../completion-plan.md).
