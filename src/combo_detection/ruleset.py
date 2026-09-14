"""Loading the SOD combination ruleset (N-function rules, N >= 2) from JSON.

This is a DRAFT ruleset -- not derived from ISI's SOD guideline the way the
main 144-rule ruleset is (that document only defines two-function rules).
Every rule here carries its own "status" field saying so; never present a
finding from this tool as approved policy.
"""

import json
from collections import defaultdict

REQUIRED_RULE_FIELDS = {
    "combo_id",
    "process_area",
    "category",
    "risk_level",
    "functions",
    "business_impact",
    "suggested_mitigation",
}


def load_combination_ruleset(path):
    """Load the combination ruleset JSON into a list of rule dicts. Each
    rule's functions[].tcodes are normalized to uppercase sets (blank/empty
    stays an empty set -- a function with no T-code at all, same
    convention as the main ruleset, so it can never produce a false match).

    Raises ValueError (rather than a bare JSONDecodeError/KeyError) with a
    message naming the file and what's wrong, if the JSON is malformed or a
    rule/function is missing a field the rest of this package assumes is
    always present.
    """
    with open(path, encoding="utf-8") as f:
        try:
            rules = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}: not valid JSON ({e})") from e

    if not isinstance(rules, list):
        raise ValueError(f"{path}: expected a JSON list of rules, got {type(rules).__name__}")

    for i, rule in enumerate(rules):
        missing = REQUIRED_RULE_FIELDS - set(rule)
        if missing:
            raise ValueError(
                f"{path}: rule at index {i} (combo_id={rule.get('combo_id', '?')}) "
                f"missing required field(s) {sorted(missing)}"
            )
        for fn in rule["functions"]:
            if "name" not in fn or "tcodes" not in fn:
                raise ValueError(f"{path}: rule {rule['combo_id']} has a function missing 'name' or 'tcodes'")
            fn["tcodes"] = {t.strip().upper() for t in fn["tcodes"] if t.strip()}
    return rules


def rules_needing_manual_tracking(rules):
    """Rules where at least one function has no T-code at all -- these can
    never be flagged by T-code matching alone, same principle as the main
    ruleset's control_type logic."""
    return [r for r in rules if any(not fn["tcodes"] for fn in r["functions"])]


def summarize_by_module(rules):
    """Group rule *counts* by process_area, for a report's summary section."""
    counts = defaultdict(int)
    for r in rules:
        counts[r["process_area"]] += 1
    return dict(counts)
