"""The end-to-end detection pipeline: load ruleset -> resolve user access ->
detect N-way combination conflicts -> write PDF + Excel reports.

Both `cli.py` (the `combo-detect` command) and `gui.py` (the `combo-detect-gui`
window) call run_detection() directly rather than duplicating this
sequence -- one implementation, two front ends. Raises FileNotFoundError /
ValueError on bad input (missing files, malformed CSV/JSON); callers decide
how to present that (CLI: stderr + exit code, GUI: a dialog).
"""

import os

from .access import build_user_tcode_roles
from .detect import detect_combination_conflicts
from .report_excel import build_excel_report
from .report_pdf import build_pdf_report
from .ruleset import load_combination_ruleset, rules_needing_manual_tracking


def _ensure_parent_dir(path):
    """Create an output path's parent directory if it doesn't exist yet --
    neither reportlab nor openpyxl do this for you, and without it a fresh
    output path fails with a FileNotFoundError that reads like the report
    file itself was expected to already exist.
    """
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def run_detection(
    ruleset_path,
    role_tcodes_path,
    user_roles_path,
    composite_roles_path,
    output_pdf_path,
    output_excel_path,
    generated_for="",
    log=print,
):
    """Run the full pipeline and write both reports. `log` is called with
    each progress line (defaults to `print`; the GUI passes something that
    appends to its on-screen log widget instead). Returns a summary dict.
    """
    rules = load_combination_ruleset(ruleset_path)
    manual_only = rules_needing_manual_tracking(rules)
    log(f"Loaded {len(rules)} combination rules ({len(manual_only)} have at least one function with no T-code).")

    user_tcode_roles = build_user_tcode_roles(role_tcodes_path, user_roles_path, composite_roles_path)
    user_tcodes = {user_id: set(tcode_roles.keys()) for user_id, tcode_roles in user_tcode_roles.items()}
    log(f"Resolved effective T-code access for {len(user_tcodes)} users.")

    findings = detect_combination_conflicts(rules, user_tcodes, user_tcode_roles)
    affected = sorted({f["user_id"] for f in findings})
    log(f"Findings: {len(findings)} across {len(affected)} user(s): {', '.join(affected) if affected else '(none)'}")

    _ensure_parent_dir(output_pdf_path)
    build_pdf_report(rules, findings, output_pdf_path, generated_for=generated_for)
    log(f"PDF report written to: {output_pdf_path}")

    _ensure_parent_dir(output_excel_path)
    build_excel_report(rules, findings, output_excel_path, generated_for=generated_for)
    log(f"Excel report written to: {output_excel_path}")

    return {
        "rule_count": len(rules),
        "manual_only_count": len(manual_only),
        "user_count": len(user_tcodes),
        "finding_count": len(findings),
        "affected_users": affected,
    }
