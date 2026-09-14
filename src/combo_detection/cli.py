"""Command-line entry point (installed as `combo-detect`)."""

import argparse
import sys

from .pipeline import run_detection


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


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        run_detection(
            args.ruleset,
            args.role_tcodes,
            args.user_roles,
            args.composite_roles,
            args.output,
            args.excel_output,
            generated_for=args.generated_for,
            log=print,
        )
    except FileNotFoundError as e:
        print(f"Error: file not found -- {e.filename}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
