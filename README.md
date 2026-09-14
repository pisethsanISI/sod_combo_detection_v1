# SOD Combination Ruleset Detector

Detects SAP segregation-of-duties combination risks — rules that fire only
when a single person holds **three or more specific functions together**,
not just a pair — and produces both a PDF and an Excel report, organized by
SAP process module.

This is a **separate project** from [`SOD_Detection`](../SOD_Detection),
which handles the approved 144-rule (two-function) ruleset. This project
exists specifically because that detection engine only knows how to check
pairs — combination rules need genuinely different matching logic (every
function must match, not just two sides), so rather than bolt that onto
the existing tool, it's its own small, focused package.

## Important: this ruleset is a DRAFT, not approved policy

`ruleset/sap_sod_combination_ruleset.json` was **not** transcribed from
ISI's SOD guideline — that document only defines two-function risks. These
16 rules are a proposal, reasoned out from real T-codes already in the
approved ruleset, meant to be reviewed by IT Governance before being
treated as real policy. Every rule carries a `status` field saying so, and
every generated report repeats this disclaimer on its cover page. See
`../SOD_Detection/docs/COMBINATION_RULESET_PROPOSAL.docx` for the business
case behind these rules.

## What it does

For each of the 16 combination rules, checks whether any user's resolved
SAP T-code access covers **every** function in that rule (not just some).
Composite roles are resolved down to single roles first, same as the main
SOD_Detection project — a user assigned only a composite role still gets
correctly checked against what its bundled single roles actually grant.

Every run writes **both** a PDF and an Excel workbook — not one or the
other. The PDF is organized by SAP module (Procure-to-Pay, Order-to-Cash,
Treasury, Fixed Assets, Record-to-Report, Produce-to-Deliver, Warehouse
Management, Basis & Security) — **every module appears, even ones with
zero findings**, so nothing silently disappears from the report. Each rule
shows its full function chain, whether it's even checkable via T-code
data, and — if a real user matches — which role(s) granted each piece of
access.

The Excel workbook covers the same findings in a more filterable/sortable
shape, across three sheets:
- **Read Me** — DRAFT status, summary counts
- **Findings** — one row per (user, rule) match, wide format (one column
  triple per function: name / matched T-code(s) / granting role(s)),
  severity-colored the same way as `SOD_Detection`'s own Excel reports
  (light red/orange/yellow for High/Medium/Low)
- **Manual Controls** — rules that can never be detected via T-code data at
  all, same principle as `SOD_Detection`'s manual-controls checklist

## Setup and running it

```powershell
.\setup.ps1     # one-time: creates .venv, installs the package
.\run.ps1       # runs against the bundled sample data
```

Open `output\sod_combination_report.pdf` and `output\sod_combination_report.xlsx` afterward.

### Running it without the command line (GUI)

```powershell
.\run_gui.ps1
```

Opens a small desktop window: browse to your role/T-code, user/role, and
(optional) composite-role CSVs -- whatever you just exported fresh from
SAP -- pick where to write the PDF and Excel reports, and click **Run
Detection**. Progress and any error shows in the on-screen log instead of
a terminal. It remembers your last-used paths (in
`~/.combo_detection_gui_settings.json`, outside the repo) so the next run
after a new export doesn't mean re-browsing everything. This is the same
`combo-detect` pipeline underneath -- `cli.py` and `gui.py` both call the
shared `pipeline.run_detection()`, so the two never drift apart.

### Running against real data

```powershell
.venv\Scripts\combo-detect.exe `
    --ruleset ruleset\sap_sod_combination_ruleset.json `
    --role-tcodes ..\SOD_Detection\data\from_manual_export\role_tcodes.csv `
    --user-roles ..\SOD_Detection\data\from_manual_export\user_roles.csv `
    --composite-roles ..\SOD_Detection\data\from_manual_export\composite_roles.csv `
    --output output\sod_combination_report.pdf `
    --excel-output output\sod_combination_report.xlsx `
    --for "ISI Group"
```

This project never reaches into `SOD_Detection`'s files automatically —
you point it at whatever role/user CSVs you want via command-line flags,
same convention as `SOD_Detection`'s own CLI.

## Project structure

```
ruleset/sap_sod_combination_ruleset.json  - the 16 draft rules (own copy, not a live link to SOD_Detection)
src/combo_detection/
  ruleset.py      - loads the combination ruleset JSON
  access.py       - resolves user -> role -> T-code access (composite-role-aware)
  detect.py       - the N-way matching logic (every function must match, not just 2)
  report_pdf.py   - builds the PDF, grouped by module
  report_excel.py - builds the Excel workbook (Read Me / Findings / Manual Controls)
  pipeline.py     - shared run_detection() pipeline used by both cli.py and gui.py
  cli.py          - the `combo-detect` command
  gui.py          - the `combo-detect-gui` windowed command (see "Running it without the command line" above)
  drift_check.py  - the `combo-check-drift` command (see below)
tests/            - pytest suite (46 tests)
data/             - sample CSVs (synthetic, safe to share)
output/           - generated PDF + Excel reports (git-ignored -- may contain real user IDs once run for real)
run_gui.ps1       - double-click launcher for the GUI
```

## Running the tests

```powershell
.venv\Scripts\pytest.exe
```

46 tests: ruleset loading, composite-role resolution, the N-way matching
logic (including that a rule with any function missing a T-code can never
produce a false match), PDF- and Excel-generation smoke tests (including a
regression test that a rule with more than 3 functions doesn't get
truncated), pipeline tests covering the shared `run_detection()` used by
both the CLI and the GUI, one end-to-end test that runs the real 16-rule
ruleset against the bundled sample data and confirms the expected match,
drift-check logic tests (see below) -- one of which runs against the real
sibling `SOD_Detection` ruleset when that repo is present, and skips
cleanly when it isn't -- and CLI tests confirming a missing file or
malformed CSV/JSON input produces a clean one-line error and exit code 1,
not a raw traceback. (`gui.py` itself isn't exercised by pytest, to keep
the suite runnable on a headless CI machine with no display / Tk
installed -- it's a thin widget layer over the same `pipeline.run_detection()`
the tests do cover.)

## Checking for ruleset drift against SOD_Detection

Since this ruleset's T-code mappings were reused from the main 144-rule
ruleset rather than independently re-validated (see below), `combo-check-drift`
cross-checks every function in this ruleset against the pairwise ruleset's
`function_a`/`function_b` T-code mappings, so the two never silently drift
apart as either one is edited:

```powershell
.venv\Scripts\combo-check-drift.exe `
    --combination-ruleset ruleset\sap_sod_combination_ruleset.json `
    --pairwise-ruleset ..\SOD_Detection\ruleset\sap_sod_ruleset.json
```

It flags two kinds of issue: a function whose T-codes here are no longer a
subset of what the pairwise ruleset defines for that same function name
(real drift -- one of the two rulesets is stale), and a function name that
doesn't appear in the pairwise ruleset at all (not necessarily wrong, but
worth a human look). This is a standalone, opt-in check -- it takes both
ruleset paths explicitly and isn't run by `combo-detect` or wired into CI,
since this project deliberately has no filesystem dependency on
`SOD_Detection` at runtime.

## Known limitations

- Same T-code-level ceiling as `SOD_Detection` — a function with no T-code
  mapping at all (a physical or organizational-only step) can never be
  matched here either; the report says so explicitly per rule rather than
  hiding it.
- The T-code mappings in this ruleset were reused directly from the main
  144-rule ruleset, not independently re-validated -- run `combo-check-drift`
  after editing either ruleset to catch the two falling out of sync.
- No API, no scheduled automation, no web portal — this is a standalone
  CLI tool. If real-time combination checking is ever needed, that would
  be a separate integration project, the same way `SOD_Detection`'s API
  was built after its CLI/report tooling was already solid.
