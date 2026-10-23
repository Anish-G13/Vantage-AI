import csv
import io

from pypdf import PdfReader

from vantage.calculations import effective_assessments, prioritize, scores_for
from vantage.exports import comparison_rows, csv_bytes, executive_pdf, roadmap_rows
from vantage.models import Assessment, Override, Source


def test_csv_and_scores_use_same_snapshot(demo):
    overrides = {"p0_f2": Override(rating="Yes", note="Manual correction.")}
    effective = effective_assessments(demo, overrides)
    weights = [1, 2, 3, 4, 5]
    rows = list(
        csv.DictReader(
            io.StringIO(
                csv_bytes(comparison_rows(demo, effective, weights, overrides)).decode("utf-8-sig")
            )
        )
    )
    assert len(rows) == 15
    own = [row for row in rows if row["Product"] == demo.request.product]
    score = scores_for(demo, effective, weights)[demo.request.product]
    assert all(float(row["Known-feature score (%)"]) == score.score for row in own)
    assert own[2]["Rating"] == "Yes" and own[2]["Original rating"] == "No"
    assert own[2]["Origin"] == "Manual" and own[2]["Override note"] == "Manual correction."


def test_csv_neutralizes_formulas_and_retains_unicode():
    data = csv_bytes(
        [
            {
                "Name": '=HYPERLINK("https://example.com")',
                "Note": "  +cmd",
                "Value": 2,
                "Unicode": "研究",
            }
        ]
    )
    row = next(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    assert row["Name"].startswith("'=") and row["Note"].startswith("'")
    assert row["Value"] == "2" and row["Unicode"] == "研究"


def test_roadmap_csv_values_and_missing_evidence(demo):
    roadmap = prioritize(demo, effective_assessments(demo, {}), [5] * 5, [3] * 5, [3] * 5)
    rows = roadmap_rows(roadmap)
    assert rows[0]["Priority score"] == 5.0 and rows[0]["Rank"] == "1"
    assert rows[-1]["Priority score"] is None and rows[-1]["Rank"] == "Research needed"


def test_executive_pdf_contents_and_calculations(demo):
    effective = effective_assessments(demo, {})
    roadmap = prioritize(demo, effective, [5] * 5, [3] * 5, [3] * 5)
    data = executive_pdf(demo, effective, [5] * 5, roadmap, {})
    reader = PdfReader(io.BytesIO(data))
    text = " ".join(page.extract_text() for page in reader.pages)
    assert data.startswith(b"%PDF-")
    assert "DEMONSTRATION" in text and "50.0%" in text and "90.0%" in text
    assert "Priority: 5.00" in text and "Research needed" in text
    assert "Limitations and uncertainty" in text and "Evidence and assessment audit" in text
    assert len(reader.pages) >= 2


def test_pdf_retains_original_sources_and_safe_manual_notes(demo):
    source = Source(
        url="https://docs.example.com/test-feature",
        title="Synthetic & test source",
        supported_text="Claim linked in this test.",
    )
    demo.assessments["p0_f2"] = Assessment(
        rating="No",
        basis="Source-backed",
        explanation="Synthetic original statement.",
        sources=[source],
    )
    overrides = {"p0_f2": Override(rating="Yes", note="User <reviewed> & corrected this claim.")}
    effective = effective_assessments(demo, overrides)
    data = executive_pdf(
        demo, effective, [5] * 5, prioritize(demo, effective, [5] * 5, [3] * 5, [3] * 5), overrides
    )
    reader = PdfReader(io.BytesIO(data))
    text = " ".join(page.extract_text() for page in reader.pages)
    links = [
        str(a.get_object().get("/A", {}).get("/URI", ""))
        for page in reader.pages
        for a in page.get("/Annots", [])
    ]
    assert source.url in links
    assert "User <reviewed> & corrected this claim." in text
    assert "Original: No" in text and "Synthetic original statement." in text
