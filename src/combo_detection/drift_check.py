"""Checks whether this project's combination ruleset has drifted from the
T-code mappings in the main SOD_Detection pairwise ruleset it was reasoned
out from (see README "Known limitations" -- these mappings were reused
once, not independently re-validated, and the two rulesets are never
linked at runtime).

This is a standalone, opt-in check, not part of combo-detect or the
pytest suite: it takes an explicit --pairwise-ruleset path so it never
assumes SOD_Detection lives next to this project (same standalone
principle as access.py), and it's meant to be run by a person after
either ruleset changes, not on every CI run.
"""

import argparse
import json
import sys
from collections import defaultdict


def build_canonical_functions(pairwise_rules):
    """From the pairwise ruleset's function_a/function_b pairs, build
    {function_name: {tcode, ...}} -- the same function name can appear on
    either side of many different pairwise rules, so tcodes are unioned
    across every occurrence.
    """
    canonical = defaultdict(set)
    for rule in pairwise_rules:
        canonical[rule["function_a_name"]].update(t.strip().upper() for t in rule["function_a_tcodes"])
        canonical[rule["function_b_name"]].update(t.strip().upper() for t in rule["function_b_tcodes"])
    return dict(canonical)


def find_drift(combo_rules, canonical_functions):
    """Compare every function in the combination ruleset against the
    pairwise ruleset's canonical name -> tcodes mapping. Returns a list of
    issue dicts, most severe first:

    - "tcode_mismatch": the function name is recognized, but this
      ruleset's tcodes for it are not a subset of the pairwise ruleset's
      -- real drift, one of the two rulesets is stale.
    - "unknown_function": the function name doesn't appear in the
      pairwise ruleset at all -- not necessarily wrong (this ruleset can
      define genuinely new functions), but worth a human's attention.
    """
    issues = []
    for rule in combo_rules:
        for fn in rule["functions"]:
            name = fn["name"]
            tcodes = {t.strip().upper() for t in fn["tcodes"]}
            canonical_tcodes = canonical_functions.get(name)
            if canonical_tcodes is None:
                issues.append(
                    {
                        "issue": "unknown_function",
                        "combo_id": rule["combo_id"],
                        "function_name": name,
                        "combo_tcodes": sorted(tcodes),
                        "canonical_tcodes": [],
                    }
                )
            elif not tcodes.issubset(canonical_tcodes):
                issues.append(
                    {
                        "issue": "tcode_mismatch",
                        "combo_id": rule["combo_id"],
                        "function_name": name,
                        "combo_tcodes": sorted(tcodes),
                        "canonical_tcodes": sorted(canonical_tcodes),
                    }
                )
    return issues


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Check the combination ruleset's function T-code mappings against the main "
            "SOD_Detection pairwise ruleset they were reasoned out from, to catch drift "
            "if either ruleset changes independently."
        )
    )
    parser.add_argument(
        "--combination-ruleset",
        default="ruleset/sap_sod_combination_ruleset.json",
        help="Path to this project's combination ruleset JSON",
    )
    parser.add_argument(
        "--pairwise-ruleset",
        required=True,
        help="Path to SOD_Detection's sap_sod_ruleset.json (the approved 144-rule ruleset)",
    )
    return parser


def _load_json(path):
    """Open and parse a ruleset JSON file, raising ValueError (not a bare
    JSONDecodeError) with the path attached if it's malformed -- same
    convention as ruleset.load_combination_ruleset.
    """
    with open(path, encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}: not valid JSON ({e})") from e


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        combo_rules = _load_json(args.combination_ruleset)
        pairwise_rules = _load_json(args.pairwise_ruleset)
    except FileNotFoundError as e:
        print(f"Error: file not found -- {e.filename}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    canonical_functions = build_canonical_functions(pairwise_rules)
    issues = find_drift(combo_rules, canonical_functions)

    if not issues:
        print(f"No drift found: every function in {args.combination_ruleset} matches {args.pairwise_ruleset}.")
        return 0

    mismatches = [i for i in issues if i["issue"] == "tcode_mismatch"]
    unknowns = [i for i in issues if i["issue"] == "unknown_function"]

    if mismatches:
        print(f"{len(mismatches)} T-CODE MISMATCH(ES) -- one ruleset is stale relative to the other:")
        for i in mismatches:
            print(f"  {i['combo_id']} / {i['function_name']}: combo has {i['combo_tcodes']}, pairwise has {i['canonical_tcodes']}")
        print()

    if unknowns:
        print(f"{len(unknowns)} function name(s) not found anywhere in the pairwise ruleset (may be intentional):")
        for i in unknowns:
            print(f"  {i['combo_id']} / {i['function_name']}: {i['combo_tcodes']}")

    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
