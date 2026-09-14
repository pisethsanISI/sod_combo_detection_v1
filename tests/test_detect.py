from combo_detection.detect import detect_combination_conflicts


def make_rule(combo_id, functions, risk_level="High", **overrides):
    rule = {
        "combo_id": combo_id,
        "process_area": "P2P",
        "category": "Test",
        "risk_level": risk_level,
        "control_type": "System",
        "functions": [{"name": name, "tcodes": set(tcodes)} for name, tcodes in functions],
        "business_impact": "impact",
        "suggested_mitigation": "mitigation",
        "status": "DRAFT",
        "notes": "",
    }
    rule.update(overrides)
    return rule


def test_flags_user_holding_all_three_legs():
    rules = [make_rule("C1", [("A", {"T1"}), ("B", {"T2"}), ("C", {"T3"})])]
    user_tcodes = {"U1": {"T1", "T2", "T3"}}

    findings = detect_combination_conflicts(rules, user_tcodes)

    assert len(findings) == 1
    assert findings[0]["user_id"] == "U1"
    assert findings[0]["combo_id"] == "C1"


def test_does_not_flag_user_missing_one_leg():
    rules = [make_rule("C1", [("A", {"T1"}), ("B", {"T2"}), ("C", {"T3"})])]
    user_tcodes = {"U1": {"T1", "T2"}}  # missing T3

    assert detect_combination_conflicts(rules, user_tcodes) == []


def test_rule_with_any_blank_function_never_matches():
    # A function with no T-code at all (physical/organizational-only step)
    # must never produce a false match, no matter what the user holds.
    rules = [make_rule("C1", [("A", {"T1"}), ("B", set()), ("C", {"T3"})])]
    user_tcodes = {"U1": {"T1", "T3", "ANYTHING"}}

    assert detect_combination_conflicts(rules, user_tcodes) == []


def test_multiple_users_only_the_matching_one_is_flagged():
    rules = [make_rule("C1", [("A", {"T1"}), ("B", {"T2"})])]
    user_tcodes = {
        "CLEAN": {"T1"},
        "FLAGGED": {"T1", "T2"},
    }

    findings = detect_combination_conflicts(rules, user_tcodes)

    assert len(findings) == 1
    assert findings[0]["user_id"] == "FLAGGED"


def test_two_way_rule_still_works_not_just_three_way():
    # N-way generalization must still handle N=2 correctly.
    rules = [make_rule("C1", [("A", {"T1"}), ("B", {"T2"})])]
    user_tcodes = {"U1": {"T1", "T2"}}

    assert len(detect_combination_conflicts(rules, user_tcodes)) == 1


def test_four_way_rule_works_too():
    rules = [make_rule("C1", [("A", {"T1"}), ("B", {"T2"}), ("C", {"T3"}), ("D", {"T4"})])]
    user_tcodes = {"U1": {"T1", "T2", "T3", "T4"}}

    assert len(detect_combination_conflicts(rules, user_tcodes)) == 1


def test_reports_granting_role_per_function_when_provenance_given():
    rules = [make_rule("C1", [("A", {"T1"}), ("B", {"T2"})])]
    user_tcodes = {"U1": {"T1", "T2"}}
    user_tcode_roles = {"U1": {"T1": {"ROLE_A"}, "T2": {"ROLE_B"}}}

    findings = detect_combination_conflicts(rules, user_tcodes, user_tcode_roles)

    assert findings[0]["functions"][0]["granting_roles"] == ["ROLE_A"]
    assert findings[0]["functions"][1]["granting_roles"] == ["ROLE_B"]


def test_granting_roles_blank_without_provenance():
    rules = [make_rule("C1", [("A", {"T1"}), ("B", {"T2"})])]
    user_tcodes = {"U1": {"T1", "T2"}}

    findings = detect_combination_conflicts(rules, user_tcodes)

    assert findings[0]["functions"][0]["granting_roles"] == []


def test_real_ruleset_flags_the_known_sample_data_case():
    from combo_detection.access import build_user_tcode_roles
    from combo_detection.ruleset import load_combination_ruleset

    rules = load_combination_ruleset("ruleset/sap_sod_combination_ruleset.json")
    user_tcode_roles = build_user_tcode_roles(
        "data/sample_role_tcodes.csv", "data/sample_user_roles.csv", "data/sample_composite_roles.csv"
    )
    user_tcodes = {u: set(t.keys()) for u, t in user_tcode_roles.items()}

    findings = detect_combination_conflicts(rules, user_tcodes, user_tcode_roles)

    combo_ids = {f["combo_id"] for f in findings if f["user_id"] == "U1"}
    assert "COMBO-P2P-01" in combo_ids
