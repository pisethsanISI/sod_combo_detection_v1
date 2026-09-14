import os

import pytest

from combo_detection.drift_check import build_canonical_functions, find_drift

PAIRWISE_RULESET_PATH = os.path.join("..", "SOD_Detection", "ruleset", "sap_sod_ruleset.json")


def _pairwise_rule(fn_a_name, fn_a_tcodes, fn_b_name, fn_b_tcodes):
    return {
        "function_a_name": fn_a_name,
        "function_a_tcodes": fn_a_tcodes,
        "function_b_name": fn_b_name,
        "function_b_tcodes": fn_b_tcodes,
    }


def _combo_rule(combo_id, functions):
    return {"combo_id": combo_id, "functions": [{"name": n, "tcodes": t} for n, t in functions]}


def test_build_canonical_functions_unions_both_sides_across_rules():
    pairwise_rules = [
        _pairwise_rule("Create Vendor", ["FK01"], "Run Payment", ["F110"]),
        _pairwise_rule("Change Bank Details", ["FK02"], "Create Vendor", ["XK01"]),
    ]
    canonical = build_canonical_functions(pairwise_rules)

    assert canonical["Create Vendor"] == {"FK01", "XK01"}
    assert canonical["Run Payment"] == {"F110"}
    assert canonical["Change Bank Details"] == {"FK02"}


def test_find_drift_is_clean_when_combo_tcodes_are_a_subset_of_canonical():
    pairwise_rules = [_pairwise_rule("Create Vendor", ["FK01", "MK01", "XK01"], "Run Payment", ["F110"])]
    canonical = build_canonical_functions(pairwise_rules)
    combo_rules = [_combo_rule("COMBO-1", [("Create Vendor", ["FK01", "XK01"]), ("Run Payment", ["F110"])])]

    assert find_drift(combo_rules, canonical) == []


def test_find_drift_flags_tcode_not_covered_by_pairwise_ruleset():
    pairwise_rules = [_pairwise_rule("Create Vendor", ["FK01"], "Run Payment", ["F110"])]
    canonical = build_canonical_functions(pairwise_rules)
    # ZK01 isn't in the pairwise ruleset's mapping for "Create Vendor" -- real drift.
    combo_rules = [_combo_rule("COMBO-1", [("Create Vendor", ["FK01", "ZK01"])])]

    issues = find_drift(combo_rules, canonical)

    assert len(issues) == 1
    assert issues[0]["issue"] == "tcode_mismatch"
    assert issues[0]["combo_id"] == "COMBO-1"
    assert issues[0]["function_name"] == "Create Vendor"
    assert issues[0]["combo_tcodes"] == ["FK01", "ZK01"]


def test_find_drift_flags_function_name_absent_from_pairwise_ruleset():
    canonical = build_canonical_functions([_pairwise_rule("Create Vendor", ["FK01"], "Run Payment", ["F110"])])
    combo_rules = [_combo_rule("COMBO-1", [("Approve Budget", ["FM_APPROVE"])])]

    issues = find_drift(combo_rules, canonical)

    assert len(issues) == 1
    assert issues[0]["issue"] == "unknown_function"
    assert issues[0]["function_name"] == "Approve Budget"


@pytest.mark.skipif(
    not os.path.exists(PAIRWISE_RULESET_PATH),
    reason="sibling SOD_Detection repo not present -- this integration check only runs when it's checked out alongside this project",
)
def test_real_combination_ruleset_has_no_drift_from_the_real_pairwise_ruleset():
    import json

    from combo_detection.ruleset import load_combination_ruleset

    with open(PAIRWISE_RULESET_PATH, encoding="utf-8") as f:
        pairwise_rules = json.load(f)

    combo_rules = load_combination_ruleset("ruleset/sap_sod_combination_ruleset.json")
    canonical = build_canonical_functions(pairwise_rules)

    issues = find_drift(combo_rules, canonical)
    mismatches = [i for i in issues if i["issue"] == "tcode_mismatch"]

    assert mismatches == [], f"Combination ruleset has drifted from the pairwise ruleset: {mismatches}"
