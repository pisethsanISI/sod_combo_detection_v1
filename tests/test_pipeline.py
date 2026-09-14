import openpyxl
import pytest

from combo_detection.pipeline import run_detection


def test_run_detection_writes_both_reports_and_returns_a_summary(tmp_path):
    out_pdf = tmp_path / "nested" / "report.pdf"
    out_xlsx = tmp_path / "nested" / "report.xlsx"

    summary = run_detection(
        "ruleset/sap_sod_combination_ruleset.json",
        "data/sample_role_tcodes.csv",
        "data/sample_user_roles.csv",
        "data/sample_composite_roles.csv",
        str(out_pdf),
        str(out_xlsx),
    )

    assert out_pdf.exists()
    assert out_xlsx.exists()
    assert summary["rule_count"] == 16
    assert summary["user_count"] == 2
    assert summary["finding_count"] == 1
    assert summary["affected_users"] == ["U1"]

    wb = openpyxl.load_workbook(str(out_xlsx))
    assert wb["Findings"].max_row == 2  # header + the one finding


def test_run_detection_logs_progress_via_the_given_callback(tmp_path):
    lines = []
    run_detection(
        "ruleset/sap_sod_combination_ruleset.json",
        "data/sample_role_tcodes.csv",
        "data/sample_user_roles.csv",
        None,
        str(tmp_path / "report.pdf"),
        str(tmp_path / "report.xlsx"),
        log=lines.append,
    )

    assert any("Loaded 16 combination rules" in line for line in lines)
    assert any("PDF report written to" in line for line in lines)
    assert any("Excel report written to" in line for line in lines)


def test_run_detection_raises_file_not_found_for_a_missing_input(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_detection(
            "ruleset/sap_sod_combination_ruleset.json",
            str(tmp_path / "does_not_exist.csv"),
            "data/sample_user_roles.csv",
            None,
            str(tmp_path / "report.pdf"),
            str(tmp_path / "report.xlsx"),
        )


def test_run_detection_raises_value_error_for_a_malformed_csv(tmp_path):
    bad_csv = tmp_path / "role_tcodes.csv"
    bad_csv.write_text("role_id,wrong_column\nZ_AP_FULL,FK01\n", encoding="utf-8")

    with pytest.raises(ValueError, match="tcode"):
        run_detection(
            "ruleset/sap_sod_combination_ruleset.json",
            str(bad_csv),
            "data/sample_user_roles.csv",
            None,
            str(tmp_path / "report.pdf"),
            str(tmp_path / "report.xlsx"),
        )
