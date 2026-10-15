"""
Chart specification builder using Plotly.
Converts AnalysisResult objects into Plotly JSON figure dictionaries.
Frontend renders the returned spec without recomputing data.
"""

from __future__ import annotations
from typing import Any
import plotly.graph_objects as go
from genda.core.models import AnalysisResult


DARK_CHART_LAYOUT = {
    "paper_bgcolor": "rgba(15, 23, 42, 0.95)",  # Slate 900
    "plot_bgcolor": "rgba(30, 41, 59, 0.6)",    # Slate 800
    "font": {"color": "#94a3b8", "family": "Inter, system-ui, sans-serif", "size": 12},
    "margin": {"l": 50, "r": 30, "t": 60, "b": 50},
    "xaxis": {
        "gridcolor": "#334155",
        "zerolinecolor": "#475569",
        "showgrid": True,
    },
    "yaxis": {
        "gridcolor": "#334155",
        "zerolinecolor": "#475569",
        "showgrid": True,
    },
    "legend": {"font": {"color": "#cbd5e1"}},
}


def build_chart_for_result(result: AnalysisResult) -> dict[str, Any] | None:
    """
    Generate an interactive Plotly figure specification based on the operation and result.
    Returns a dict matching Plotly JSON schema ({data: [...], layout: {...}}).
    """
    op = result.operation
    data = result.result

    if op == "numeric_summary":
        # Box plot / summary indicators
        col = data.get("column", "Metric")
        fig = go.Figure()
        fig.add_trace(go.Box(
            q1=[data.get("q25", 0)],
            median=[data.get("median", 0)],
            q3=[data.get("q75", 0)],
            lowerfence=[data.get("min", 0)],
            upperfence=[data.get("max", 0)],
            mean=[data.get("mean", 0)],
            name=col,
            marker_color="#38bdf8",  # Sky 400
            boxmean=True,
        ))
        fig.update_layout(
            title={"text": f"Distribution Summary for '{col}'", "font": {"color": "#f8fafc", "size": 15}},
            **DARK_CHART_LAYOUT,
        )
        return fig.to_plotly_json()

    elif op in ("group_agg", "group_sum"):
        groups = data.get("groups", [])
        if not groups:
            return None

        # Limit to top 25 categories for legible display
        display_groups = groups[:25]
        metric_field = data.get("metric_field", "value")
        group_by = data.get("group_by", "Category")
        agg = data.get("agg", "agg")

        x_vals = [str(g.get(group_by, "")) for g in display_groups]
        y_vals = [g.get(metric_field, 0) for g in display_groups]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=x_vals,
            y=y_vals,
            marker={
                "color": y_vals,
                "colorscale": "Tealgrn",
                "line": {"color": "#38bdf8", "width": 1},
            },
            name=f"{agg.upper()}({data.get('metric', '')})",
        ))
        fig.update_layout(
            title={
                "text": f"{agg.upper()} of {data.get('metric')} by {group_by}" + (" (Top 25)" if len(groups) > 25 else ""),
                "font": {"color": "#f8fafc", "size": 15},
            },
            xaxis_title=group_by,
            yaxis_title=f"{agg.upper()}({data.get('metric')})",
            **DARK_CHART_LAYOUT,
        )
        return fig.to_plotly_json()

    elif op == "category_rank":
        rankings = data.get("rankings", [])
        if not rankings:
            return None

        # Limit to top 20
        display_items = rankings[:20]
        categories = [r.get("category", "") for r in display_items]
        values = [r.get("value", 0) for r in display_items]

        # Horizontal bar chart for clean ranking
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=categories,
            x=values,
            orientation="h",
            marker={"color": "#6366f1", "line": {"color": "#818cf8", "width": 1}},
            name="Ranked Metric",
        ))
        fig.update_layout(
            title={"text": result.title, "font": {"color": "#f8fafc", "size": 15}},
            xaxis_title=f"{data.get('agg', '').upper()}({data.get('metric_column', '')})",
            yaxis={"autorange": "reversed"},
            **DARK_CHART_LAYOUT,
        )
        return fig.to_plotly_json()

    elif op == "missing_summary":
        columns = data.get("columns", [])
        if not columns:
            return None

        # Filter to columns that have missing values or top 15
        miss_cols = [c for c in columns if c.get("null_percentage", 0) > 0][:20]
        if not miss_cols:
            miss_cols = columns[:10]

        names = [c["column"] for c in miss_cols]
        pcts = [c["null_percentage"] for c in miss_cols]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=names,
            y=pcts,
            marker={"color": "#f43f5e", "line": {"color": "#fb7185", "width": 1}},
            name="% Missing",
        ))
        fig.update_layout(
            title={"text": "Missing Values Percentage by Column", "font": {"color": "#f8fafc", "size": 15}},
            xaxis_title="Column",
            yaxis_title="% Missing / Null",
            **DARK_CHART_LAYOUT,
        )
        return fig.to_plotly_json()

    elif op == "date_comparison":
        p1 = data.get("period_1", {})
        p2 = data.get("period_2", {})
        labels = [
            f"Period 1 ({p1.get('start', '')} - {p1.get('end', '')})",
            f"Period 2 ({p2.get('start', '')} - {p2.get('end', '')})",
        ]
        values = [p1.get("metric_value", 0), p2.get("metric_value", 0)]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=labels,
            y=values,
            marker={"color": ["#3b82f6", "#10b981"]},
            name=f"{data.get('agg', '').upper()} Metric",
        ))
        fig.update_layout(
            title={"text": result.title, "font": {"color": "#f8fafc", "size": 15}},
            yaxis_title=f"{data.get('agg', '').upper()}({data.get('metric')})",
            **DARK_CHART_LAYOUT,
        )
        return fig.to_plotly_json()

    return None
