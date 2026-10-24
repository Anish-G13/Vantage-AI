"""Missing assessments remain gaps, never zeros, in interactive Plotly charts."""

import plotly.graph_objects as go

from .calculations import VALUES, Score
from .models import Analysis, Assessment, cell_id

PALETTE = ["#123E68", "#148E91", "#C48B34", "#8273B7"]


def bar_chart(scores: dict[str, Score]) -> go.Figure:
    fig = go.Figure()
    for i, (product, score) in enumerate(scores.items()):
        fig.add_trace(
            go.Bar(
                x=[product],
                y=[score.score],
                name=product,
                marker_color=PALETTE[i],
                customdata=[[score.assessed_weight_pct, score.source_backed_weight_pct]],
                hovertemplate="%{x}<br>Known-feature score: %{y:.1f}%<br>Assessed weight: %{customdata[0]:.1f}%<br>Source-backed weight: %{customdata[1]:.1f}%<extra></extra>",
            )
        )
    fig.update_layout(
        title="Weighted feature score",
        yaxis_title="Known-feature score (%)",
        yaxis_range=[0, 105],
        showlegend=False,
        height=350,
        margin=dict(l=20, r=20, t=55, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#172C43",
    )
    return fig


def radar_chart(analysis: Analysis, effective: dict[str, Assessment]) -> go.Figure:
    fig = go.Figure()
    names = [f.name for f in analysis.discovery.features]
    for p, product in enumerate(analysis.request.products):
        values = [VALUES[effective[cell_id(p, f)].rating] for f in range(5)]
        fig.add_trace(
            go.Scatterpolar(
                name=product,
                r=[*values, values[0]],
                theta=[*names, names[0]],
                mode="lines+markers",
                connectgaps=False,
                line=dict(color=PALETTE[p], width=2),
                fill="toself" if all(v is not None for v in values) else "none",
            )
        )
    fig.update_layout(
        title="Feature profile",
        height=350,
        margin=dict(l=50, r=50, t=55, b=45),
        polar=dict(
            radialaxis=dict(
                range=[0, 1.05], tickvals=[0, 0.5, 1], ticktext=["No", "Partial", "Yes"]
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        legend=dict(orientation="h", y=-0.15),
        font_color="#172C43",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig
