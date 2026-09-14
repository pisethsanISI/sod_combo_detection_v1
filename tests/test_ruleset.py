import pytest

from combo_detection.ruleset import (
    load_combination_ruleset,
    rules_needing_manual_tracking,
    summarize_by_module,
)


def test_load_combination_ruleset_parses_real_file():
    rules = load_combination_ruleset("ruleset/sap_sod_combination_ruleset.json")
    assert len(rules) == 16
    assert all("combo_id" in r for r in rules)
    assert all(isinstance(fn["tcodes"], set) for r in rules for fn in r["functions"])


def test_load_combination_ruleset_uppercases_tcodes(tmp_path):
    path = tmp_path / "combo.json"
    path.write_text(
        '[{"combo_id": "C1", "process_area": "P2P", "category": "Test", "risk_level": "High", '
        '"functions": [{"name": "A", "tcodes": ["fk01"]}, {"name": "B", "tcodes": []}], '
        '"business_impact": "x", "suggested_mitigation": "y", "status": "DRAFT"}]',
        encoding="utf-8",
    )
    rules = load_combination_ruleset(str(path))
    assert rules[0]["functions"][0]["tcodes"] == {"FK01"}
    assert rules[0]["functions"][1]["tcodes"] == set()


def test_rules_needing_manual_tracking_finds_rules_with_a_blank_function():
    rules = load_combination_ruleset("ruleset/sap_sod_combination_ruleset.json")
    manual = rules_needing_manual_tracking(rules)
    ids = {r["combo_id"] for r in manual}
    assert "COMBO-TR-02" in ids  # all three legs blank
    assert "COMBO-P2P-01" not in ids  # all three legs have real tcodes


def test_summarize_by_module_counts_two_per_domain():
    rules = load_combination_ruleset("ruleset/sap_sod_combination_ruleset.json")
    counts = summarize_by_module(rules)
    assert counts["P2P"] == 2
    assert counts["Basis & Security"] == 2
    assert sum(counts.values()) == 16


def test_load_combination_ruleset_raises_clear_error_on_malformed_json(tmp_path):
    path = tmp_path / "combo.json"
    path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ValueError, match="not valid JSON"):
        load_combination_ruleset(str(path))


def test_load_combination_ruleset_raises_clear_error_on_missing_rule_field(tmp_path):
    path = tmp_path / "combo.json"
    path.write_text(
        '[{"combo_id": "C1", "process_area": "P2P", "category": "Test", "risk_level": "High", '
        '"functions": [{"name": "A", "tcodes": ["FK01"]}]}]',  # missing business_impact/suggested_mitigation
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required field"):
        load_combination_ruleset(str(path))


def test_load_combination_ruleset_raises_clear_error_on_function_missing_tcodes(tmp_path):
    path = tmp_path / "combo.json"
    path.write_text(
        '[{"combo_id": "C1", "process_area": "P2P", "category": "Test", "risk_level": "High", '
        '"functions": [{"name": "A"}], "business_impact": "x", "suggested_mitigation": "y"}]',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing 'name' or 'tcodes'"):
        load_combination_ruleset(str(path))
