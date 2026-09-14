"""Builds the combination-ruleset detection report as a PDF, one section
per SAP process module (P2P, O2C, Treasury, Assets, R2R, P2D, EWM,
Basis & Security) -- every module is shown even if it has zero findings,
so nothing silently disappears from the picture.
"""

import datetime
from collections import defaultdict

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

INK = colors.HexColor("#1B2430")
INK_SOFT = colors.HexColor("#4B5768")
ACCENT = colors.HexColor("#2C5AA0")
WARN_BG = colors.HexColor("#FBE5DB")
WARN_FG = colors.HexColor("#8A4A1F")
BAND_BG = colors.HexColor("#F2F1EC")

LEVEL_FG = {
    "High": colors.HexColor("#8A1F1F"),
    "Medium": colors.HexColor("#8A4A1F"),
    "Low": colors.HexColor("#6E5A14"),
}

MODULE_ORDER = ["P2P", "O2C", "Treasury", "Assets", "R2R", "P2D", "EWM", "Basis & Security"]
MODULE_LABELS = {
    "P2P": "Procure-to-Pay",
    "O2C": "Order-to-Cash",
    "Treasury": "Treasury",
    "Assets": "Fixed Assets",
    "R2R": "Record-to-Report",
    "P2D": "Produce-to-Deliver",
    "EWM": "Warehouse Management",
    "Basis & Security": "Basis & Security",
}


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("TitleBig", parent=ss["Title"], textColor=INK, fontSize=22, leading=26))
    ss.add(ParagraphStyle("SubtitleAccent", parent=ss["Normal"], textColor=ACCENT, fontSize=13, spaceAfter=10))
    ss.add(ParagraphStyle("ModuleHeading", parent=ss["Heading1"], textColor=INK, fontSize=16, spaceBefore=14, spaceAfter=4))
    ss.add(ParagraphStyle("RuleHeading", parent=ss["Heading2"], textColor=INK, fontSize=11.5, spaceBefore=10, spaceAfter=2))
    ss.add(ParagraphStyle("Body", parent=ss["Normal"], textColor=INK, fontSize=9.5, leading=13))
    ss.add(ParagraphStyle("BodySoft", parent=ss["Normal"], textColor=INK_SOFT, fontSize=9, leading=12))
    ss.add(ParagraphStyle("FunctionChain", parent=ss["Normal"], textColor=ACCENT, fontSize=9.5, leading=13))
    ss.add(ParagraphStyle("NoMatch", parent=ss["Normal"], textColor=INK_SOFT, fontSize=9, leading=12, spaceAfter=8))
    return ss


def _level_para(level, styles):
    style = ParagraphStyle(
        f"Level{level}", parent=styles["Body"], textColor=LEVEL_FG.get(level, INK), fontName="Helvetica-Bold"
    )
    return Paragraph(level.upper(), style)


def build_pdf_report(rules, findings, output_path, generated_for=""):
    """rules: full combination ruleset (list of rule dicts, tcodes as sets).
    findings: output of detect.detect_combination_conflicts().
    """
    styles = _styles()
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title="SOD Combination Ruleset -- Detection Report",
    )

    story = []

    # --- Title page ---
    story.append(Spacer(1, 1.2 * inch))
    story.append(Paragraph("SOD Combination Ruleset", styles["TitleBig"]))
    story.append(Paragraph("Detection Report -- by SAP Module", styles["SubtitleAccent"]))

    checkable = [r for r in rules if all(fn["tcodes"] for fn in r["functions"])]
    affected_users = sorted({f["user_id"] for f in findings})
    meta_lines = [
        f"Generated: {datetime.date.today():%d %B %Y}" + (f"  |  For: {generated_for}" if generated_for else ""),
        f"Rules in ruleset: {len(rules)}  |  Checkable via T-code data: {len(checkable)}",
        f"Findings: {len(findings)}  |  Users affected: {len(affected_users)}",
    ]
    for line in meta_lines:
        story.append(Paragraph(line, styles["BodySoft"]))
    story.append(Spacer(1, 14))

    warn_table = Table([[Paragraph(
        "DRAFT ruleset -- not approved by IT Governance. These combination rules are proposed "
        "escalations of the existing 144-rule SOD ruleset, not transcribed policy. Any finding "
        "below is a candidate for review, not a confirmed violation.",
        ParagraphStyle("Warn", parent=styles["Body"], textColor=WARN_FG),
    )]], colWidths=[6.5 * inch])
    warn_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WARN_BG),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#D97706")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(warn_table)
    story.append(PageBreak())

    # --- Per-module sections ---
    rules_by_module = defaultdict(list)
    for r in rules:
        rules_by_module[r["process_area"]].append(r)
    findings_by_combo = defaultdict(list)
    for f in findings:
        findings_by_combo[f["combo_id"]].append(f)

    for module in MODULE_ORDER:
        module_rules = rules_by_module.get(module, [])
        module_finding_count = sum(len(findings_by_combo[r["combo_id"]]) for r in module_rules)
        story.append(Paragraph(f"{MODULE_LABELS[module]} ({module})", styles["ModuleHeading"]))
        story.append(Paragraph(
            f"{len(module_rules)} combination rule(s) defined for this module -- {module_finding_count} finding(s).",
            styles["BodySoft"],
        ))

        if not module_rules:
            story.append(Paragraph("No combination rules currently defined for this module.", styles["NoMatch"]))
            continue

        for rule in module_rules:
            block = []
            header_row = Table(
                [[Paragraph(f"{rule['combo_id']} -- {rule['category']}", styles["RuleHeading"]), _level_para(rule["risk_level"], styles)]],
                colWidths=[5.3 * inch, 1.0 * inch],
            )
            header_row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
            block.append(header_row)

            chain = " → ".join(
                f"{fn['name']} ({'/'.join(sorted(fn['tcodes'])) or 'no T-code'})" for fn in rule["functions"]
            )
            block.append(Paragraph(chain, styles["FunctionChain"]))
            block.append(Paragraph(rule["business_impact"], styles["Body"]))

            uncheckable = [fn["name"] for fn in rule["functions"] if not fn["tcodes"]]
            rule_findings = findings_by_combo.get(rule["combo_id"], [])

            if uncheckable:
                block.append(Paragraph(
                    f"Cannot be fully checked via T-code data -- \"{', '.join(uncheckable)}\" has no T-code "
                    "mapping; track as a manual/organizational control.",
                    styles["NoMatch"],
                ))
            elif not rule_findings:
                block.append(Paragraph("No real user currently matches all legs of this rule.", styles["NoMatch"]))
            else:
                table_data = [["User", "Function", "Matched T-code(s)", "Granting role(s)"]]
                for finding in rule_findings:
                    for i, fn in enumerate(finding["functions"]):
                        table_data.append([
                            finding["user_id"] if i == 0 else "",
                            fn["name"],
                            "/".join(fn["matched_tcodes"]),
                            ", ".join(fn["granting_roles"]) or "(unknown)",
                        ])
                t = Table(table_data, colWidths=[0.85 * inch, 1.55 * inch, 1.3 * inch, 2.6 * inch], repeatRows=1)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), INK),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#A6A6A6")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                block.append(Spacer(1, 4))
                block.append(t)
                block.append(Spacer(1, 4))
                block.append(Paragraph(f"Suggested mitigation: {rule['suggested_mitigation']}", styles["BodySoft"]))

            story.append(KeepTogether(block))
            story.append(Spacer(1, 8))

        story.append(PageBreak())

    # Remove trailing page break
    if story and isinstance(story[-1], PageBreak):
        story.pop()

    doc.build(story)
