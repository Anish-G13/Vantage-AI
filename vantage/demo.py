"""Fictional demonstration data. None of these ratings is market research."""

from .models import Analysis, Assessment, Discovery, Feature, ResearchRequest, cell_id, utc_now


def demonstration() -> Analysis:
    request = ResearchRequest(product="Northstar PM", competitors=["Orbit Plan", "Cedar Work"])
    names = [
        "Workflow automation",
        "Reporting & dashboards",
        "API & integrations",
        "Access controls",
        "Portfolio planning",
    ]
    discovery = Discovery(
        category="Fictional work-management products",
        features=[
            Feature(
                name=name,
                description="Illustrative feature for exploring the demonstration workflow.",
            )
            for name in names
        ],
    )
    ratings = [
        ["Partial", "Yes", "No", "Unverified", "Partial"],
        ["Yes", "Yes", "Yes", "Yes", "Partial"],
        ["Yes", "Partial", "Partial", "Unverified", "No"],
    ]
    assessments = {
        cell_id(p, f): Assessment(
            rating=ratings[p][f],
            basis="Sample data",
            origin="Sample",
            explanation="Fictional sample assessment. No external evidence or real product claim.",
        )
        for p in range(3)
        for f in range(5)
    }
    return Analysis(
        request=request,
        discovery=discovery,
        assessments=assessments,
        researched_at=utc_now(),
        mode="Demonstration",
        model="No AI call",
        notices=[
            "Demonstration: fictional products and sample ratings. Explore the workflow without making AI requests."
        ],
    )
