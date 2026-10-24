"""CSV and PDF exports use the same effective assessments and calculations as UI."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    TableStyle,
)

from .calculations import RoadmapItem, scores_for
from .models import Analysis, Assessment, Insight, Override, cell_id

NAVY = colors.HexColor("#123E68")
PALE = colors.HexColor("#EDF3F8")
INK = colors.HexColor("#172C43")


def comparison_rows(
    analysis: Analysis,
    effective: dict[str, Assessment],
    weights: list[float],
    overrides: dict[str, Override],
) -> list[dict]:
    scores = scores_for(analysis, effective, weights)
    rows = []
    for p, product in enumerate(analysis.request.products):
        for f, feature in enumerate(analysis.discovery.features):
            key = cell_id(p, f)
            assessment, original = effective[key], analysis.assessments[key]
            rows.append(
                {
                    "Product": product,
                    "Feature": feature.name,
                    "Importance weight": weights[f],
                    "Rating": assessment.rating,
                    "Origin": assessment.origin,
                    "Basis": assessment.basis,
                    "Confidence": assessment.confidence,
                    "Explanation": assessment.explanation,
                    "Original rating": original.rating,
                    "Original explanation": original.explanation,
                    "Override note": overrides[key].note if key in overrides else "",
                    "Original claim sources": " | ".join(s.url for s in original.sources),
                    "Original claim source context": " | ".join(
                        s.supported_text for s in original.sources
                    ),
                    "Research date UTC": analysis.researched_at,
                    "Mode": analysis.mode,
                    "Known-feature score (%)": scores[product].score,
                    "Assessed weight (%)": scores[product].assessed_weight_pct,
                    "Source-backed weight (%)": scores[product].source_backed_weight_pct,
                    "Possible overall lower bound (%)": scores[product].lower_bound,
                    "Possible overall upper bound (%)": scores[product].upper_bound,
                }
            )
    return rows


def roadmap_rows(items: list[RoadmapItem]) -> list[dict]:
    rows = []
    rank = 0
    for item in items:
        if item.priority is not None:
            rank += 1
        rows.append(
            {
                "Rank": str(rank) if item.priority is not None else "Research needed",
                "Feature": item.feature,
                "Your rating": item.own_rating,
                "Competitor reference": item.competitor_reference,
                "Competitive gap (0–1)": item.gap,
                "Importance (assumption, 0–10)": item.importance,
                "Impact (assumption, 1–5)": item.impact,
                "Effort (assumption, 1–5)": item.effort,
                "Priority score": item.priority,
                "Formula": "gap * importance * impact / effort",
                "Strategic rationale": item.rationale,
                "Recommended next action": item.next_action,
            }
        )
    return rows


def csv_bytes(rows: list[dict]) -> bytes:
    """UTF-8 BOM for spreadsheet compatibility; neutralize spreadsheet formulas."""
    if not rows:
        return b"\xef\xbb\xbf"
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\r\n")
    writer.writeheader()
    for row in rows:
        safe = {}
        for key, value in row.items():
            if isinstance(value, str) and (
                value.lstrip().startswith(("=", "+", "-", "@"))
                or value.startswith(("\t", "\r", "\n"))
            ):
                value = "'" + value
            safe[key] = value
        writer.writerow(safe)
    return stream.getvalue().encode("utf-8-sig")


def _register_fonts() -> None:
    if "Vantage" not in pdfmetrics.getRegisteredFontNames():
        root = Path(reportlab.__file__).parent / "fonts"
        pdfmetrics.registerFont(TTFont("Vantage", str(root / "Vera.ttf")))
        pdfmetrics.registerFont(TTFont("Vantage-Bold", str(root / "VeraBd.ttf")))
        pdfmetrics.registerFontFamily("Vantage", normal="Vantage", bold="Vantage-Bold")


def pdf_text(value) -> str:
    """Escape XML and expose unsupported glyphs as U+ codes, never black boxes."""
    text = "-" if value is None else str(value)
    for original, replacement in (("—", "-"), ("–", "-"), ("→", "->"), ("≥", ">="), ("≤", "<=")):
        text = text.replace(original, replacement)
    chars = pdfmetrics.getFont("Vantage").face.charToGlyph
    text = "".join(c if ord(c) in chars or c in "\n\t" else f"[U+{ord(c):04X}]" for c in text)
    return escape(text).replace("\n", "<br/>")


def executive_pdf(
    analysis: Analysis,
    effective: dict[str, Assessment],
    weights: list[float],
    roadmap: list[RoadmapItem],
    overrides: dict[str, Override],
    insights: Insight | None = None,
) -> bytes:
    _register_fonts()
    output = io.BytesIO()
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "VTitle",
            fontName="Vantage-Bold",
            fontSize=24,
            leading=29,
            textColor=NAVY,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            "VHeading",
            fontName="Vantage-Bold",
            fontSize=13,
            leading=18,
            textColor=NAVY,
            spaceBefore=17,
            spaceAfter=8,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            "VBody",
            fontName="Vantage",
            fontSize=9,
            leading=13,
            textColor=INK,
            spaceAfter=6,
            splitLongWords=True,
        )
    )
    styles.add(ParagraphStyle("VSmall", parent=styles["VBody"], fontSize=7.5, leading=10))
    styles.add(
        ParagraphStyle(
            "VHeader", parent=styles["VSmall"], fontName="Vantage-Bold", textColor=colors.white
        )
    )
    styles.add(ParagraphStyle("VCenter", parent=styles["VSmall"], alignment=TA_CENTER))

    def p(text, style="VBody"):
        return Paragraph(pdf_text(text), styles[style])

    def table(headers, rows, widths):
        t = LongTable(
            [[p(h, "VHeader") for h in headers], *[[p(v, "VSmall") for v in row] for row in rows]],
            colWidths=widths,
            repeatRows=1,
            hAlign="LEFT",
            splitByRow=1,
            rowSplitRange=(2, -3) if len(rows) > 10 else None,
        )
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, NAVY),
                ]
            )
        )
        return t

    doc = SimpleDocTemplate(
        output,
        pagesize=(612, 792),
        rightMargin=42,
        leftMargin=42,
        topMargin=45,
        bottomMargin=45,
        title="Vantage AI | Executive Competitive Report",
        author="Vantage AI",
    )
    story = [
        p("VANTAGE AI", "VTitle"),
        p("Executive competitive intelligence report", "VHeading"),
        p(f"Snapshot: {analysis.display_date} | Mode: {analysis.mode}"),
        p("Products: " + " | ".join(analysis.request.products)),
        p("Category: " + analysis.discovery.category),
    ]
    if analysis.mode == "Demonstration":
        story.append(
            p(
                "DEMONSTRATION: fictional products and assessments. Not research or user validation.",
                "VHeading",
            )
        )
    story += [
        p("Landscape at a glance", "VHeading"),
        p(
            "Five comparison criteria, editable importance weights, and traceable assessment provenance. "
            "Ratings are scoped to the reviewed evidence; source linkage is not independent feature testing."
        ),
    ]
    scores = scores_for(analysis, effective, weights)
    story.append(
        table(
            [
                "Product",
                "Known score",
                "Assessed weight",
                "Source-backed weight",
                "Possible overall range",
            ],
            [
                [
                    prod,
                    "N/A" if s.score is None else f"{s.score:.1f}%",
                    f"{s.assessed_weight_pct:.1f}%",
                    f"{s.source_backed_weight_pct:.1f}%",
                    f"{s.lower_bound:.1f}–{s.upper_bound:.1f}%",
                ]
                for prod, s in scores.items()
            ],
            [160, 77, 89, 99, 103],
        )
    )
    story.append(
        p(
            "Known score = 100 x sum(weight x rating) / assessed weight, where Yes=1, Partial=0.5 and No=0. "
            "Unverified is excluded, not counted as No. Assessed weight shows how much is known. The possible "
            "overall range assigns unknowns 0–1 only to illustrate uncertainty. Compare scores with coverage in mind.",
            "VSmall",
        )
    )
    own = [effective[cell_id(0, f)] for f in range(5)]
    strengths = [
        analysis.discovery.features[f].name for f, a in enumerate(own) if a.rating == "Yes"
    ]
    gaps = [item.feature for item in roadmap if item.gap is not None and item.gap > 0]
    missing = [
        analysis.discovery.features[f].name for f, a in enumerate(own) if a.rating == "Unverified"
    ]
    story += [
        p("Strengths and weaknesses", "VHeading"),
        p("Features rated Yes for your product: " + (", ".join(strengths) or "None established.")),
        p(
            "Positive gaps against assessed competitors: "
            + (", ".join(gaps) or "None established; this is not proof of parity.")
        ),
        p(
            "Your features needing further research: "
            + (", ".join(missing) or "None currently marked Unverified.")
        ),
    ]
    if insights:
        story += [
            p("AI-generated strategic interpretation", "VHeading"),
            p("Strengths: " + insights.strengths),
            p("Context: " + insights.neutral_observations),
            p("Risks / next decisions: " + insights.critical_gaps_risks),
        ]
    headers = ["Feature / importance", *analysis.request.products]
    feature_rows = [
        [
            f"{feature.name}\nWeight: {weights[f]}",
            *[
                effective[cell_id(i, f)].rating + (" *" if cell_id(i, f) in overrides else "")
                for i in range(len(analysis.request.products))
            ],
        ]
        for f, feature in enumerate(analysis.discovery.features)
    ]
    product_width = 368 / len(analysis.request.products)
    story += [
        PageBreak(),
        p("Feature comparison", "VHeading"),
        table(headers, feature_rows, [160, *[product_width] * len(analysis.request.products)]),
        p(
            "* User override. Original research and user notes remain visible in the evidence appendix and CSV.",
            "VSmall",
        ),
        p("Prioritized product opportunities", "VHeading"),
        p(
            "Priority = competitive gap x importance x impact / effort. Gap = max(0, strongest assessed competitor rating "
            "minus your rating). Importance, impact, and effort are assumptions, not measured business impact. "
            "Missing evidence yields Research needed, not a fabricated priority.",
            "VSmall",
        ),
    ]
    roadmap_table = []
    for row, item in zip(roadmap_rows(roadmap), roadmap):
        score = "Research needed" if item.priority is None else f"{item.priority:.2f}"
        roadmap_table.append(
            [
                f"{row['Rank']}. {item.feature}\nPriority: {score}",
                f"Gap: {item.gap if item.gap is not None else 'Unknown'}\nImportance: {item.importance}\nImpact: {item.impact}\nEffort: {item.effort}",
                item.rationale + "\nNext action: " + item.next_action,
            ]
        )
    story.append(
        table(
            ["Opportunity / priority", "Assumptions", "Rationale / next action"],
            roadmap_table,
            [125, 90, 313],
        )
    )
    source_numbers = {}
    source_objects = {}
    for assessment in analysis.assessments.values():
        for source in assessment.sources:
            if source.url not in source_numbers:
                source_numbers[source.url] = len(source_numbers) + 1
                source_objects[source.url] = source
    evidence_rows = []
    for row in comparison_rows(analysis, effective, weights, overrides):
        product_index = analysis.request.products.index(row["Product"])
        feature_index = next(
            i for i, f in enumerate(analysis.discovery.features) if f.name == row["Feature"]
        )
        original = analysis.assessments[cell_id(product_index, feature_index)]
        refs = (
            ", ".join(f"[{source_numbers[s.url]}]" for s in original.sources) or "No linked source"
        )
        provenance = f"{row['Origin']} / {row['Basis']}\n{row['Confidence']}"
        detail = row["Explanation"] + f"\nSources: {refs}"
        if row["Origin"] == "Manual":
            detail += f"\nOriginal: {row['Original rating']} — {row['Original explanation']}"
        evidence_rows.append(
            [f"{row['Product']}\n{row['Feature']}", row["Rating"], provenance, detail]
        )
    story += [
        PageBreak(),
        p("Evidence and assessment audit", "VHeading"),
        table(
            ["Product / feature", "Rating", "Provenance / confidence", "Explanation / sources"],
            evidence_rows,
            [133, 54, 137, 204],
        ),
        p("Supporting sources", "VHeading"),
    ]
    if not source_numbers:
        story.append(
            p(
                "No source-backed research is attached to this analysis. Demo/manual values are not verified facts."
            )
        )
    for url, index in source_numbers.items():
        source = source_objects[url]
        story.append(
            KeepTogether(
                [
                    p(f"[{index}] {source.title}", "VBody"),
                    Paragraph(
                        f'<link href="{escape(url, {chr(34): "&quot;"})}" color="#123E68">{pdf_text(url)}</link>',
                        styles["VSmall"],
                    ),
                    p(
                        "Model claim linked by the grounding provider: "
                        + source.supported_text[:500],
                        "VSmall",
                    ),
                ]
            )
        )
    story += [
        p("Limitations and uncertainty", "VHeading"),
        p(
            "Linked sources can be stale, incomplete, plan-specific, or interpreted incorrectly by the model. "
            "A citation establishes provenance, not independent verification. Absence of evidence does not establish No. "
            "User overrides are judgments and may be unsourced. Competitor coverage alone does not establish customer demand "
            "or ROI. Validate priorities with users and engineering. No interviews, adoption, satisfaction, or measured "
            "commercial outcomes are claimed. CSV preserves original Unicode; uncommon PDF glyphs use visible U+ codes."
        ),
    ]
    for notice in analysis.notices:
        story.append(p(notice, "VSmall"))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(NAVY)
        canvas.line(42, 34, 570, 34)
        canvas.setFont("Vantage", 8)
        canvas.setFillColor(INK)
        canvas.drawString(42, 22, "Vantage AI | Decision support, with evidence and uncertainty")
        canvas.drawRightString(570, 22, str(document.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
