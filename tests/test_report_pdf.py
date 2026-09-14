import os

from combo_detection.access import build_user_tcode_roles
from combo_detection.detect import detect_combination_conflicts
from combo_detection.report_pdf import build_pdf_report
from combo_detection.ruleset import load_combination_ruleset


def test_build_pdf_report_creates_a_valid_pdf(tmp_path):
    rules = load_combination_ruleset("ruleset/sap_sod_combination_ruleset.json")
    user_tcode_roles = build_user_tcode_roles(
        "data/sample_role_tcodes.csv", "data/sample_user_roles.csv", "data/sample_composite_roles.csv"
    )
    user_tcodes = {u: set(t.keys()) for u, t in user_tcode_roles.items()}
    findings = detect_combination_conflicts(rules, user_tcodes, user_tcode_roles)

    out_path = str(tmp_path / "report.pdf")
    build_pdf_report(rules, findings, out_path, generated_for="Test Run")

    assert os.path.exists(out_path)
    assert os.path.getsize(out_path) > 1000
    with open(out_path, "rb") as f:
        assert f.read(5) == b"%PDF-"


def test_build_pdf_report_handles_zero_findings(tmp_path):
    rules = load_combination_ruleset("ruleset/sap_sod_combination_ruleset.json")
    out_path = str(tmp_path / "empty.pdf")

    build_pdf_report(rules, [], out_path)

    assert os.path.exists(out_path)
    with open(out_path, "rb") as f:
        assert f.read(5) == b"%PDF-"
