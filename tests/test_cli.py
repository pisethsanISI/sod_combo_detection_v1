from combo_detection.cli import main


def test_main_reports_missing_ruleset_file_cleanly_instead_of_a_traceback(tmp_path, capsys):
    exit_code = main(
        [
            "--ruleset",
            str(tmp_path / "does_not_exist.json"),
            "--role-tcodes",
            "data/sample_role_tcodes.csv",
            "--user-roles",
            "data/sample_user_roles.csv",
        ]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "does_not_exist.json" in captured.err
    assert "Traceback" not in captured.err


def test_main_reports_malformed_csv_cleanly_instead_of_a_traceback(tmp_path, capsys):
    bad_role_tcodes = tmp_path / "role_tcodes.csv"
    bad_role_tcodes.write_text("role_id,wrong_column\nZ_AP_FULL,FK01\n", encoding="utf-8")

    exit_code = main(
        [
            "--ruleset",
            "ruleset/sap_sod_combination_ruleset.json",
            "--role-tcodes",
            str(bad_role_tcodes),
            "--user-roles",
            "data/sample_user_roles.csv",
        ]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "tcode" in captured.err
    assert "Traceback" not in captured.err


def test_main_succeeds_against_the_bundled_sample_data(tmp_path, capsys):
    exit_code = main(
        [
            "--ruleset",
            "ruleset/sap_sod_combination_ruleset.json",
            "--role-tcodes",
            "data/sample_role_tcodes.csv",
            "--user-roles",
            "data/sample_user_roles.csv",
            "--composite-roles",
            "data/sample_composite_roles.csv",
            "--output",
            str(tmp_path / "report.pdf"),
            "--excel-output",
            str(tmp_path / "report.xlsx"),
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "report.pdf").exists()
    assert (tmp_path / "report.xlsx").exists()
