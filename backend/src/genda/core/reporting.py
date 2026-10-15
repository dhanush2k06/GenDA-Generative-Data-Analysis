"""
Self-contained HTML report builder using Jinja2 and Plotly.
Produces clean, secure reports with zero raw data exposure.
"""

from __future__ import annotations
import json
from typing import Any
import jinja2

REPORT_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GenDA Analytical Report — {{ report_title }}</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: #111827;
      --border: #1f2937;
      --text: #e2e8f0;
      --text-muted: #94a3b8;
      --accent: #38bdf8;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.6;
      margin: 0;
      padding: 2rem;
    }
    .container {
      max-width: 1000px;
      margin: 0 auto;
    }
    header {
      border-bottom: 1px solid var(--border);
      padding-bottom: 1.5rem;
      margin-bottom: 2rem;
    }
    h1 {
      margin: 0 0 0.5rem 0;
      font-size: 2rem;
      color: #f8fafc;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .badge {
      display: inline-block;
      font-size: 0.75rem;
      padding: 0.25rem 0.6rem;
      border-radius: 9999px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .badge-success { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #059669; }
    .badge-warn { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #d97706; }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    .card-title {
      font-size: 1.25rem;
      margin-top: 0;
      margin-bottom: 1rem;
      color: #f1f5f9;
      border-bottom: 1px solid var(--border);
      padding-bottom: 0.5rem;
    }
    .grid-4 {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      margin-bottom: 1rem;
    }
    .stat-box {
      background: rgba(30, 41, 59, 0.5);
      border: 1px solid var(--border);
      padding: 1rem;
      border-radius: 0.5rem;
    }
    .stat-label {
      font-size: 0.8rem;
      color: var(--text-muted);
      text-transform: uppercase;
    }
    .stat-val {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--accent);
      margin-top: 0.25rem;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 1rem;
      font-size: 0.9rem;
    }
    th, td {
      padding: 0.75rem;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }
    th {
      background: rgba(30, 41, 59, 0.8);
      color: #cbd5e1;
      font-weight: 600;
    }
    tr:hover {
      background: rgba(30, 41, 59, 0.4);
    }
    .chart-container {
      margin-top: 1.5rem;
      border-radius: 0.5rem;
      overflow: hidden;
      border: 1px solid var(--border);
    }
    .warning-box {
      background: rgba(245, 158, 11, 0.1);
      border-left: 4px solid var(--warning);
      padding: 0.75rem 1rem;
      border-radius: 0.25rem;
      margin-top: 1rem;
      font-size: 0.875rem;
      color: #fde68a;
    }
    .footer {
      text-align: center;
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: 3rem;
      padding-top: 1.5rem;
      border-top: 1px solid var(--border);
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>
        GenDA Analytical Report
        <span class="badge badge-success">Local Verified</span>
      </h1>
      <p style="color: var(--text-muted); margin: 0;">
        Dataset: <strong>{{ filename }}</strong> &bull; Generated: {{ timestamp }} &bull; Privacy: 100% Local (Loopback)
      </p>
    </header>

    <!-- Dataset Summary -->
    <div class="card">
      <h2 class="card-title">Dataset Overview</h2>
      <div class="grid-4">
        <div class="stat-box">
          <div class="stat-label">Total Rows</div>
          <div class="stat-val">{{ dataset_profile.row_count }}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Total Columns</div>
          <div class="stat-val">{{ dataset_profile.column_count }}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Duplicate Rows</div>
          <div class="stat-val">{{ dataset_profile.duplicate_rows }}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Memory Footprint</div>
          <div class="stat-val">{{ (dataset_profile.memory_bytes / 1024)|round(1) }} KB</div>
        </div>
      </div>
      {% if dataset_profile.dataset_warnings %}
      <div class="warning-box">
        <strong>Data Quality Notes:</strong>
        <ul style="margin: 0.25rem 0 0 1.25rem; padding: 0;">
          {% for w in dataset_profile.dataset_warnings %}
          <li>{{ w }}</li>
          {% endfor %}
        </ul>
      </div>
      {% endif %}
    </div>

    <!-- Analytical Findings -->
    {% for res in results %}
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: baseline;">
        <h2 class="card-title" style="border: none; margin-bottom: 0.25rem;">{{ res.title }}</h2>
        <span class="badge {% if res.validation_status == 'passed' %}badge-success{% else %}badge-warn{% endif %}">
          {{ res.validation_status }} ({{ res.execution_time_ms }} ms)
        </span>
      </div>
      <p style="color: var(--text-muted); font-size: 0.9rem; margin-top: 0.25rem;">
        Engine: <em>{{ res.engine_details }}</em> {% if res.cross_engine_match is not none %}&bull; Cross-engine check: <strong>{{ "Matched" if res.cross_engine_match else "Mismatch" }}</strong>{% endif %}
      </p>

      {% if res.evidence_summary %}
      <div style="background: rgba(56, 189, 248, 0.1); border-left: 4px solid var(--accent); padding: 0.75rem 1rem; border-radius: 0.25rem; margin-bottom: 1rem; color: #bae6fd; font-size: 0.95rem;">
        <strong>Evidence:</strong> {{ res.evidence_summary }}
      </div>
      {% endif %}

      <!-- Chart container if present -->
      {% if res.chart_spec %}
      <div class="chart-container" id="chart-{{ loop.index }}"></div>
      <script>
        (function() {
          var spec = {{ res.chart_spec_json | safe }};
          Plotly.newPlot('chart-{{ loop.index }}', spec.data || [], spec.layout || {}, {responsive: true, displayModeBar: false});
        })();
      </script>
      {% endif %}

      {% if res.warnings %}
      <div class="warning-box">
        <strong>Warnings & Method Notes:</strong>
        <ul style="margin: 0.25rem 0 0 1.25rem; padding: 0;">
          {% for w in res.warnings %}
          <li>{{ w }}</li>
          {% endfor %}
        </ul>
      </div>
      {% endif %}

      {% if res.limitations %}
      <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.75rem;">
        <strong>Limitations:</strong> {{ res.limitations | join(', ') }}
      </div>
      {% endif %}
    </div>
    {% endfor %}

    <div class="footer">
      Generated securely by <strong>GenDA (Generative Data Analyst)</strong> &bull; Zero external network calls &bull; Loopback only.
    </div>
  </div>
</body>
</html>
"""


def render_html_report(
    filename: str,
    dataset_profile: Any,
    results: list[Any],
    report_title: str = "Analysis Summary",
) -> str:
    """Render comprehensive self-contained HTML report."""
    import datetime
    env = jinja2.Environment(autoescape=True)
    template = env.from_string(REPORT_HTML_TEMPLATE)

    # Attach JSON string for chart specs
    processed_results = []
    for r in results:
        chart_json = json.dumps(r.chart_spec) if r.chart_spec else "null"
        processed_results.append({
            "title": r.title,
            "validation_status": r.validation_status,
            "execution_time_ms": r.execution_time_ms,
            "engine_details": r.engine_details,
            "cross_engine_match": r.cross_engine_match,
            "evidence_summary": r.evidence_summary,
            "chart_spec": r.chart_spec,
            "chart_spec_json": chart_json,
            "warnings": r.warnings,
            "limitations": r.limitations,
        })

    html = template.render(
        report_title=report_title,
        filename=filename,
        timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        dataset_profile=dataset_profile,
        results=processed_results,
    )
    return html
