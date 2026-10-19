"""Pin the rule simulation's copy of the repair reasons to the validator's.

`scripts/audit_kramerius_rules.py` reimplements the validator's rules on
purpose, so that an audit cannot agree with the code it audits by
construction. The price of that is drift, and the repair reason set is the
one part of the copy that is a plain shared constant rather than a
configurable pattern — so it can be pinned, and a change to the validator
fails here instead of quietly changing what an audit run means.

The constant is read out of the source rather than imported, because the
script parses `sys.argv` as it loads.
"""

import ast
from pathlib import Path

from marc_comparator.validators.kramerius_links import REPAIR_REASONS

AUDIT_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "audit_kramerius_rules.py"


def _top_level_literal(name: str) -> set[str]:
    tree = ast.parse(AUDIT_SCRIPT.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return set(ast.literal_eval(node.value))

    raise AssertionError(f"{name} is not assigned at the top level of {AUDIT_SCRIPT}")


def test_the_rule_simulation_repairs_the_same_reasons_as_the_validator():
    simulated = _top_level_literal("REPAIR")

    assert simulated == set(REPAIR_REASONS)  # a drifted copy audits rules nobody ships
