"""Command-line entry point (installed as `combo-detect`)."""

import argparse
import os
import sys

from .access import build_user_tcode_roles
from .detect import detect_combination_conflicts
from .report_excel import build_excel_report
from .report_pdf import build_pdf_report
from .ruleset import load_combination_ruleset, rules_needing_manual_tracking


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="SOD combination-rule detector (N-function rules) -- PDF + Excel report by SAP module"
    )
    parser.add_argument("--ruleset", required=True, help="Path to the combination ruleset JSON")
    parser.add_argument("--role-tcodes", required=True, help="Path to role_id,tcode CSV")
    parser.add_argument("--user-roles", required=True, help="Path to user_id,role_id CSV")
    parser.add_argument(
        "--composite-roles",
        help="Optional path to composite_role_id,single_role_id CSV, to resolve composite role assignments",
    )
    parser.add_argument("--output", default="output/sod_combination_report.pdf", help="Output PDF path")
    parser.add_argument(
        "--excel-output",
        default="output/sod_combination_report.xlsx",
        help="Output Excel path -- written alongside the PDF on every run, not instead of it",
    )
    parser.add_argument("--for", dest="generated_for", default="", help="Optional label shown on the report cover")
    return parser


def _ensure_parent_dir(path):
    """Create the output path's parent directory if it doesn't exist yet --
    neither reportlab nor openpyxl will do this for you, and without it a
    fresh --output path fails with a FileNotFoundError that reads like the
    report file itself was expected to already exist.
    """
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        rules = load_combination_ruleset(args.ruleset)
        manual_only = rules_needing_manual_tracking(rules)
        print(
            f"Loaded {len(rules)} combination rules ({len(manual_only)} have at least one function with no T-code)."
        )

        user_tcode_roles = build_user_tcode_roles(args.role_tcodes, args.user_roles, args.composite_roles)
        user_tcodes = {user_id: set(tcode_roles.keys()) for user_id, tcode_roles in user_tcode_roles.items()}
        print(f"Resolved effective T-code access for {len(user_tcodes)} users.")

        findings = detect_combination_conflicts(rules, user_tcodes, user_tcode_roles)
        affected = sorted({f["user_id"] for f in findings})
        print(
            f"Findings: {len(findings)} across {len(affected)} user(s): {', '.join(affected) if affected else '(none)'}"
        )

        _ensure_parent_dir(args.output)
        build_pdf_report(rules, findings, args.output, generated_for=args.generated_for)
        print(f"\nPDF report written to: {args.output}")

        _ensure_parent_dir(args.excel_output)
        build_excel_report(rules, findings, args.excel_output, generated_for=args.generated_for)
        print(f"Excel report written to: {args.excel_output}")
    except FileNotFoundError as e:
        print(f"Error: file not found -- {e.filename}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
