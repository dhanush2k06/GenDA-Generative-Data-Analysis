# GenDA Implementation Guide

**Project:** GenDA — Generative Data Analyst  
**Document:** `implementation.md`  
**Version:** 2.0  
**Status:** Proposed implementation plan (Python analysis stack)

## 1. Purpose

This document describes an incremental plan for implementing GenDA: a local-first data-analysis application that accepts user-selected datasets, profiles and prepares data, answers defined analytical questions, validates results, generates reports, and eventually reuses successful analytical workflows.

**What changed in v2.0:** the frontend (React + TypeScript + Vite) is unchanged, but all analysis, validation, visualization-spec generation, and report building now run in a **local Python service** instead of in the browser. This replaces the browser-only MVP architecture from v1.0. The privacy model changes accordingly (see Section 3 and Phase 7).

This is an implementation guide, not a claim that all features already exist. Build and verify one stage before moving to the next.

## 2. MVP Scope

### Include in the first working version

- React + TypeScript + Vite user interface (unchanged).
- A local Python service (FastAPI) bound to loopback only.
- Explicit user selection of a CSV file in the browser, sent only to the local service.
- Parsing and preview of the selected data by the Python service.
- Dataset metadata and data-quality profiling.
- A small set of deterministic analyses, such as counts, missing-value summaries, numeric summaries, and grouped totals.
- Chart specifications generated from computed results and rendered by the frontend.
- A report showing the question, operations, results, and limitations.
- A **Clear session** action that deletes server-side session data and resets the interface.
- Network inspection confirming raw file contents go only to the local service and nowhere else.

### Defer until the MVP is reliable

- Arbitrary natural-language-to-SQL or generated code execution.
- General-purpose agent loops.
- A locally hosted language model.
- Full AutoML and advanced forecasting.
- Broad filesystem or database access by the local service.
- Remote accounts, collaboration, and cloud synchronization.
- Claims that the application has learned autonomously or has a universal accuracy score.

## 3. Architecture

### MVP architecture: React UI + local Python service

```text
User
  |
  v
React + TypeScript interface (Vite)
  |-- file picker (user-selected files only)
  |-- question and analysis controls
  |-- preview, charts, report, clear-session control
  |
  |  HTTP to 127.0.0.1 only
  |  per-launch token + origin and Host validation
  v
Local Python service (FastAPI + Uvicorn)
  |-- request validation (Pydantic)
  |-- CSV loading and schema detection (Polars)
  |-- profiler and data-quality checks (Polars, Pandera)
  |-- allowlisted analytical operations (Polars, DuckDB, SciPy, statsmodels)
  |-- result validation and cross-engine checks
  |-- chart-spec builder (Plotly / Altair)
  |-- report builder (Jinja2, optional WeasyPrint)
  |
  v
In-memory session store (per-session, deletable)
  + controlled temporary workspace (only if needed for large files)
```

### Privacy model (revised)

The v1.0 claim "raw data never leaves the browser" no longer applies. The accurate claim for v2.0 is:

> Raw data is sent only from the browser to a service running on the user's own machine (loopback). It is not transmitted to any remote server, and it is not persisted by default.

This claim must be verified (Phase 7), not assumed. The service must therefore:

- Bind to `127.0.0.1` only, never `0.0.0.0`.
- Require a random token generated at each launch.
- Validate the `Origin` and `Host` headers (this also defends against DNS-rebinding attacks).
- Use a strict CORS allowlist, never a wildcard.
- Expose only the allowlisted analytical operations. No shell execution, no arbitrary file reads, no `eval`/`exec` of user-derived text.

**Serving option:** in development, Vite serves the UI on its own port and proxies API calls. For a packaged build, have the Python service serve the built frontend from the same origin. This removes cross-origin complexity.

### Fallback architecture: Pyodide (Python in the browser)

If a pure no-backend privacy claim is more important than performance, the same Python analysis modules can be run in the browser with Pyodide inside a Web Worker. Trade-offs: slow first load, memory limits, and some packages unavailable or different (verify the current Pyodide package list for Polars, DuckDB, and others before committing). Keep the analysis package free of FastAPI imports so it can be reused in either mode.

## 4. Recommended technology choices

### Frontend (unchanged)

| Area | Choice | Notes |
|---|---|---|
| Framework | React, TypeScript, Vite | Keep the UI separate from analytics logic. |
| Styling | Tailwind CSS or CSS modules | Choose one approach initially. |
| Charts | `react-plotly.js` (or `vega-embed` if Altair is chosen) | Render only from chart specs returned by the service. |
| API types | Generated from the service's OpenAPI / JSON Schema | Avoid hand-maintained duplicate types. |
| Tests | Vitest and Testing Library | UI behavior and API-client behavior (mocked). |

### Backend and analysis (new)

| Area | Choice | Notes |
|---|---|---|
| API service | FastAPI + Uvicorn | Loopback only. Auto-generates OpenAPI. |
| Validation / schemas | Pydantic v2 | Python equivalent of `AnalysisRequest` / `AnalysisResult`. |
| Dataframes | Polars | Primary engine. Strict dtypes, lazy `scan_csv` for large files. |
| SQL-style analytics | DuckDB (Python) | Same engine family as the earlier DuckDB-Wasm plan. |
| Interop | pandas | Only where statsmodels / scikit-learn require it. |
| Encoding detection | charset-normalizer | Handles the "encoding issues" edge case. |
| Data-quality rules | Pandera | Declarative checks feeding `validationStatus`. |
| Fuzzy label matching | RapidFuzz | Flags near-duplicate category labels. Report only; never auto-merge. |
| Statistics | NumPy, SciPy, statsmodels, Pingouin | Tests, intervals, effect sizes, regression, basic time series. |
| Machine learning (Phase 8) | scikit-learn | Pipelines, baselines, splits, metrics. Add LightGBM / XGBoost later. |
| Forecasting (later) | statsmodels, then statsforecast or sktime | Only after deterministic analysis is dependable. |
| Chart specs | Plotly (`fig.to_json()`) or Altair (Vega-Lite JSON) | Pick one for the first version. Plotly is the default recommendation. |
| Static chart images | Kaleido (Plotly) | For report exports. Verify current system requirements. |
| Reports | Jinja2 → HTML; WeasyPrint → PDF | PDF only after the HTML report is correct. WeasyPrint needs system libraries (Pango). |
| Metadata store (later) | SQLite via `sqlite3` or SQLModel | Approved workflow metadata only; no raw datasets by default. |
| Paths / config | platformdirs | Safe app-specific temp and config locations. |
| Logging | structlog with a redaction filter | Audit events without raw data. |
| Packaging (later) | PyInstaller or Nuitka | For a distributable local agent. |

### Testing and tooling

| Area | Choice | Notes |
|---|---|---|
| Python tests | pytest, pytest-cov | Known-answer tests on synthetic fixtures. |
| Property-based tests | Hypothesis | Edge cases: negatives, empty columns, mixed types, odd strings. |
| API tests | FastAPI `TestClient` / httpx | Origin, token, and validation tests. |
| Dependency management | uv | Lockfile for reproducible environments. |
| Lint / format | Ruff | |
| Type checking | mypy or pyright | Especially for Pydantic models. |
| Dependency advisories | pip-audit, `npm audit` | Part of the Phase 7 checklist. |

Check compatibility, licensing, maintenance, install size, and security before selecting dependencies for production.

### Minimal starting set

```text
FastAPI · Uvicorn · Pydantic v2 · Polars · DuckDB · pandas
SciPy · statsmodels · scikit-learn
Plotly · Jinja2 · Pandera
pytest · Hypothesis · Ruff · uv
```

Add Kaleido, WeasyPrint, RapidFuzz, Pingouin, SQLite tooling, and packaging tools when the phase that needs them begins.

## 5. Suggested repository structure

```text
genda/
├── README.md
├── implementation.md
├── frontend/
│   ├── package.json
│   ├── index.html
│   ├── src/
│   │   ├── app/
│   │   │   ├── App.tsx
│   │   │   └── routes.tsx
│   │   ├── components/
│   │   │   ├── FilePicker.tsx
│   │   │   ├── DataPreview.tsx
│   │   │   ├── ProfileSummary.tsx
│   │   │   ├── AnalysisPanel.tsx
│   │   │   ├── ChartPanel.tsx
│   │   │   └── ReportPanel.tsx
│   │   ├── api/
│   │   │   ├── client.ts          # token + base URL handling, typed calls
│   │   │   └── generated/         # types generated from the OpenAPI schema
│   │   ├── state/
│   │   │   └── sessionState.ts
│   │   ├── utils/
│   │   │   ├── safeFormat.ts
│   │   │   └── errors.ts
│   │   └── main.tsx
│   ├── tests/
│   └── public/
├── backend/
│   ├── pyproject.toml
│   ├── src/genda/
│   │   ├── api/
│   │   │   ├── app.py             # FastAPI app factory
│   │   │   ├── security.py        # token, Origin/Host checks, CORS
│   │   │   ├── routes_session.py
│   │   │   ├── routes_analysis.py
│   │   │   └── routes_report.py
│   │   ├── core/                  # no FastAPI imports: reusable, e.g. under Pyodide
│   │   │   ├── loading.py         # CSV loading, encoding, limits
│   │   │   ├── profiling.py
│   │   │   ├── operations.py      # allowlisted operations
│   │   │   ├── validation.py      # Pandera checks, cross-engine checks
│   │   │   ├── charts.py          # result -> chart spec
│   │   │   ├── reporting.py       # Jinja2 / WeasyPrint
│   │   │   └── models.py          # Pydantic request/result models
│   │   ├── session/
│   │   │   └── store.py           # in-memory sessions, TTL, clear/cleanup
│   │   └── __main__.py            # launcher: pick port, generate token
│   └── tests/
│       ├── fixtures/              # small synthetic CSVs with known answers
│       ├── test_profiling.py
│       ├── test_operations.py
│       ├── test_validation.py
│       ├── test_security.py
│       └── privacy-checklist.md
└── scripts/
```

Keep `core/` independent of FastAPI and of the session store. This makes the analytical core easy to test, reuse in a packaged agent, or run under Pyodide if you choose the fallback.

## 6. Implementation phases

### Phase 0 — Define requirements and test data

1. Define supported file types and initial file-size limits.
2. Prepare small synthetic CSV fixtures with known answers (computed independently, for example by hand or in a spreadsheet).
3. Define the first supported analytical questions.
4. Write privacy requirements before implementing uploads, logging, or persistence. Include the revised loopback-only claim from Section 3.
5. Define a visible error state for invalid files, unsupported questions, and an unreachable local service.

**Exit criteria:** The MVP's supported behavior and known-answer tests are documented.

### Phase 1 — Create the frontend and the service skeleton

Create the frontend:

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm run dev
```

Create the backend:

```bash
mkdir backend && cd backend
uv init --package genda
uv add fastapi uvicorn pydantic polars duckdb pandas
uv add --dev pytest pytest-cov hypothesis ruff mypy httpx
```

Build the basic page with:

- GenDA title and short description.
- File selection control.
- File metadata and preview area.
- Question input.
- Analysis results area.
- Clear-session button.
- A connection-status indicator for the local service.

Build the service skeleton with:

- A `/health` endpoint.
- Loopback-only binding and a random per-launch token.
- Origin and Host validation and a strict CORS allowlist.
- A security test suite (rejects missing token, wrong token, foreign origin, wrong Host).

Do not add login, cloud database, or remote endpoints in this phase.

**Exit criteria:** Both processes start locally, the UI renders its main states, and the service rejects unauthenticated or foreign-origin requests.

### Phase 2 — Add local CSV selection and preview

1. Let the user explicitly select a CSV file in the browser.
2. Send it to the local service as a multipart upload. Do not read or send any other file.
3. The service loads it with Polars, detecting encoding with charset-normalizer.
4. Validate file extension/MIME as hints, not as the only check. Enforce a size limit server-side.
5. Return file name, size, detected headers, row count, and a bounded preview (for example, the first N rows).
6. Handle empty files, malformed rows, encoding issues, and oversized inputs gracefully, with clear error responses.
7. Keep the dataframe in the in-memory session store only. If a temporary file is unavoidable for large inputs, use a controlled workspace and delete it on clear or expiry.

Avoid writing raw data to application databases, log files, analytics telemetry, or any remote endpoint. Do not log rows in error messages.

**Exit criteria:** A selected CSV can be previewed, invalid input is handled, and network inspection shows requests only to the local service.

### Phase 3 — Implement data profiling

Create pure functions in `core/profiling.py` for:

- Row and column counts.
- Column type inference with an `unknown` or `mixed` category.
- Missing and blank-value counts.
- Distinct-value counts where practical.
- Numeric minimum, maximum, mean, median, and range.
- Duplicate-row candidates.
- Basic categorical frequencies.
- Warnings for inconsistent formats and suspicious values (RapidFuzz may help flag near-duplicate labels).

Write the profiler yourself on top of Polars primitives so each metric is testable against known answers. Use Pandera schemas for declarative quality rules.

Do not automatically delete duplicates or fill missing values in the initial version. Report issues first and require a documented rule or user approval for transformations.

**Exit criteria:** Profiling output matches known-answer test fixtures.

### Phase 4 — Add deterministic analysis operations

Start with a small allowlist:

- Count rows matching a filter.
- Group by a selected categorical column.
- Sum/average/min/max a selected numeric column.
- Compare two explicitly selected date ranges when dates can be parsed safely.
- Rank categories by a computed metric.

Represent each operation as a validated, structured request. A discriminated union makes unsupported operations impossible to express:

```python
from typing import Literal, Annotated, Union
from pydantic import BaseModel, Field

class GroupSum(BaseModel):
    operation: Literal["group_sum"]
    group_by: str
    metric: str

class NumericSummary(BaseModel):
    operation: Literal["numeric_summary"]
    column: str

class MissingSummary(BaseModel):
    operation: Literal["missing_summary"]

AnalysisRequest = Annotated[
    Union[GroupSum, NumericSummary, MissingSummary],
    Field(discriminator="operation"),
]
```

Before running an operation, verify that referenced columns exist and have suitable types. Never build SQL by string-concatenating user text. If you use DuckDB, quote identifiers safely and bind values as parameters. Do not execute arbitrary Python or SQL generated from user text. If a request is unsupported or ambiguous, ask a clarifying question or explain the limitation.

**Exit criteria:** Each supported operation has unit tests and produces structured results.

### Phase 5 — Add validation and evidence-based insights

Every result should carry enough metadata to explain how it was computed:

```python
from typing import Any, Literal
from pydantic import BaseModel

class AnalysisResult(BaseModel):
    title: str
    operation: str
    inputs: dict[str, str | int | float | bool]
    result: Any
    warnings: list[str]
    validation_status: Literal["passed", "warning", "failed"]
```

Validate calculations against independent test cases. A cheap and effective check is **cross-engine verification**: compute the same grouped sum in Polars and in DuckDB and compare the results, flagging any mismatch as `failed`. For business findings, show the metric, comparison, evidence, and limitations. Do not state that a correlation proves causation. If there is insufficient information, report that explicitly. When using SciPy or statsmodels tests, report effect sizes and sample sizes alongside p-values, and state the assumptions behind the test.

**Exit criteria:** Invalid requests fail safely, and outputs show warnings and method details.

### Phase 6 — Add visualizations and reports

1. Build chart specifications only from the `AnalysisResult` object. The service returns a Plotly figure JSON (or Vega-Lite spec); the frontend renders it. Do not let the frontend recompute results.
2. Label axes, units, time ranges, and filters.
3. Provide tables alongside charts when exact values matter.
4. Create an HTML report with Jinja2 containing the question, dataset profile, operations, results, charts, warnings, and limitations. Autoescape all template variables.
5. Add static chart images (Kaleido) and PDF export (WeasyPrint) only after the HTML report is correct.
6. Ensure the report does not unexpectedly embed the entire raw dataset.
7. Limit chart data volume (aggregate or sample for display, and say so in the chart) so large datasets do not produce huge payloads.

**Exit criteria:** The same inputs and workflow can reproduce the same report, apart from documented nondeterministic elements (for example, timestamps).

### Phase 7 — Privacy and security verification

Test these behaviors before describing the app as privacy-preserving:

- Inspect network traffic (browser DevTools plus a system-level check such as listing the service's listening sockets) while selecting and analyzing a file.
- Confirm the service listens only on `127.0.0.1` and that no raw-data requests go to any remote host.
- Confirm there are no hidden remote analytics or telemetry calls, including from dependencies.
- Search the code for outbound network calls (`requests`, `httpx`, `urllib`, `socket`) and persistence calls (file writes, SQLite, pickle), and review each.
- Confirm raw data is not written to disk or logs by default, and that exception messages and tracebacks do not include row contents.
- Verify the Clear Session action deletes the session's dataframes, temporary files, and cached results on the server, and resets previews and results in the UI.
- Verify session expiry (TTL) cleans up abandoned sessions.
- Run the security tests: missing or wrong token, foreign `Origin`, forged `Host`, oversized upload, malformed multipart body.
- Check dependency advisories (`pip-audit`, `npm audit`) and avoid unsafe HTML rendering in both the frontend and Jinja2 templates.
- Ensure exported reports are saved only when the user initiates export.

Clearing Python references or deleting temporary files does not guarantee immediate physical erasure from memory or storage. State privacy claims precisely and document limitations.

**Exit criteria:** The privacy checklist is completed and the observed behavior matches the documented claims.

### Phase 8 — Predictive analytics

Add prediction only after deterministic analysis is dependable.

1. Ask the user to identify or confirm the target column when it cannot be inferred safely.
2. Classify the task as classification, regression, or forecasting.
3. Establish a simple baseline (`DummyClassifier` / `DummyRegressor`, or a naive forecast).
4. Split data appropriately; use chronological splits for time-series tasks.
5. Fit preprocessing only on training data using scikit-learn `Pipeline` / `ColumnTransformer` to prevent leakage.
6. Compare a small, justified set of models (scikit-learn first; LightGBM or XGBoost only if justified).
7. Report task-appropriate metrics and uncertainty/limitations. Use permutation importance rather than overstating feature importance.
8. Keep the test set out of model selection.
9. Save model metadata only with clear permission and documented retention. Do not persist models trained on sensitive data by default.

Use statsmodels when inference (coefficients, confidence intervals) matters more than prediction. Never claim a universal accuracy score across all GenDA functions.

**Exit criteria:** Models are compared using reproducible validation procedures (fixed seeds, documented splits) and a baseline.

### Phase 9 — Analytical Experience Engine

Start with a workflow library, not a claim of autonomous learning.

Store structured recipes containing:

- Problem category and prerequisites.
- Workflow steps and version.
- Expected input types.
- Validation procedure and metrics.
- Known failure conditions.
- Aggregate outcomes and user-approved feedback.

Persist recipes in SQLite as metadata only. For a new problem, retrieve candidate recipes, verify prerequisites, adapt the workflow, and test it against the current data. Compare the outcome with a baseline workflow before claiming improvement. Provide controls to inspect and delete stored experience.

**Exit criteria:** Experiments demonstrate whether workflow reuse improves speed, reliability, or quality.

### Phase 10 — Packaging and optional expanded access

Because the Python service is now the core of the app, this phase covers distribution and any permissions beyond a user-selected CSV.

Packaging:

- Bundle the service and built frontend (PyInstaller or Nuitka), served from the same origin.
- Pin dependencies with the `uv` lockfile and document system requirements (for example, WeasyPrint libraries).
- Provide clear start, stop, and cancel controls.

Optional expanded access (folders, databases), only when required:

- Require explicit user approval for each folder or database permission.
- Never expose unrestricted filesystem or shell execution.
- Use parameterized database queries and validate all inputs.
- Use a controlled temporary directory (via platformdirs) and clean up app-created temporary files.
- Keep raw data out of diagnostic logs.
- Use short-lived tokens and restrict allowed operations.

**Exit criteria:** Threat-model review, permission tests, origin checks, and cleanup tests pass on the packaged build.

## 7. Data and session design

Keep session state in memory for the MVP. If persistence is added later, separate raw-data processing from metadata persistence.

Session store requirements:

- Each session has a random ID, a creation time, and a time-to-live.
- `DELETE /session/{id}` removes all dataframes, cached results, and temporary files for that session.
- On service shutdown, all sessions are cleared.
- Memory limits: reject or sample inputs above the configured threshold rather than crashing.

A possible workflow record:

```json
{
  "workflowVersion": 1,
  "taskType": "grouped_summary",
  "operation": "group_sum",
  "groupColumnType": "categorical",
  "metricType": "numeric",
  "validationStatus": "passed",
  "createdAt": "timestamp",
  "userApproved": true
}
```

This is an illustrative schema, not a complete database specification. Avoid including raw rows, personal identifiers, or sensitive business values. Even metadata can be sensitive and must be protected.

## 8. Testing strategy

### Backend unit tests (pytest, Hypothesis)

- Missing-value counts with empty strings and null values.
- Numeric summaries with negative numbers and outliers.
- Grouped sums with missing categories.
- Date parsing with mixed or ambiguous formats.
- Duplicate detection without deleting valid repeated transactions.
- Invalid columns and unsupported operations (rejected by Pydantic or by column checks).
- Property-based tests: for example, group sums always add up to the column total (accounting for nulls), and results are invariant to row order.
- Cross-engine checks: Polars and DuckDB agree on the same operation.

### Security and API tests

- Missing or wrong token is rejected.
- Foreign `Origin` and forged `Host` are rejected.
- Oversized and malformed uploads fail with safe error messages.
- Errors and logs do not contain raw rows.

### Frontend tests (Vitest, Testing Library)

- UI states: empty, loading, error, results, service unreachable.
- API client attaches the token and handles failures.

### Integration tests

- Select a CSV, profile it, run an analysis, and display the result.
- Clear the session and verify both the UI and the server-side session are empty.
- Export a report and confirm it contains expected metrics and warnings.

### Quality benchmarks

Use synthetic datasets with independently computed answers. Track:

- Calculation correctness.
- Data-cleaning precision and unintended changes.
- Insight correctness reviewed by a human.
- Predictive metrics using proper holdouts.
- Reproducibility.
- Runtime and memory use.
- Manual interventions and failure rate.

Do not combine these into one accuracy percentage unless a defensible, documented benchmark defines how the score is calculated.

## 9. Development workflow

For every feature:

1. Define the expected behavior and edge cases.
2. Write a small test dataset with known results.
3. Implement the analytical function in `core/` independently of the API and UI.
4. Add Pydantic validation and useful errors.
5. Expose it through the API, regenerate the frontend types, and connect it to the interface.
6. Run `pytest`, `ruff`, the type checker, and the frontend tests. Inspect network traffic.
7. Update documentation and the privacy checklist.
8. Commit the change with a clear Git message.

Keep test datasets synthetic or public. Do not commit confidential user datasets, secrets, local tokens, or generated reports containing sensitive data.

## 10. Definition of done for the first MVP

- [ ] Service binds to loopback only and rejects requests without a valid token or origin.
- [ ] User can select a CSV file explicitly.
- [ ] File metadata and bounded preview are displayed.
- [ ] Profiling results match known-answer tests.
- [ ] At least three deterministic analysis operations work.
- [ ] Unsupported or ambiguous requests are handled honestly.
- [ ] Charts and reports are generated from computed results.
- [ ] Clear Session deletes server-side data and resets UI state.
- [ ] No raw dataset is sent to any non-local host in the tested workflow.
- [ ] No raw data is persisted by default.
- [ ] Unit, security, and integration tests pass.
- [ ] Privacy claims match observed implementation behavior.

## 11. Final recommendation

Build GenDA as a dependable local analytics tool first, then add prediction, and only then add workflow reuse. Using Python gives you a stronger analysis ecosystem, but it also makes security of the local service part of the MVP: treat the loopback binding, token, and origin checks as core features, not later hardening. The project's long-term value depends on demonstrable correctness, transparent reasoning, measurable improvement, and verified privacy—not on the number of AI features shown in the interface.
