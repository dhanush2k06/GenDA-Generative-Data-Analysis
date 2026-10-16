# GenDA — Generative Data Analyst

A local-first data analysis assistant. Select a CSV, profile its quality, run validated analyses, and get charts and a report that show exactly how each result was computed. A React interface talks to a Python analysis service that runs on your own machine.

> **Status: early development.** This repository follows the plan in [`implementation.md`](./implementation.md). Features are listed by roadmap phase, and nothing here should be read as already shipped unless it is checked off in the [roadmap](#roadmap).

## Why GenDA

Many "AI data analyst" tools execute generated code on your data and give you a confident answer you can't easily check. GenDA takes the opposite approach:

- **Deterministic first.** Analyses come from an allowlist of validated operations, not from arbitrary generated code or SQL.
- **Evidence over assertion.** Every result carries its operation, inputs, warnings, and a validation status.
- **Honest about limits.** Unsupported or ambiguous questions get a clear explanation or a clarifying question, not a guess.
- **Local by design.** Your data goes only from your browser to a service on your own machine.

## Features

Planned for the first working version (MVP):

- Explicit CSV selection and bounded preview
- Dataset profiling: types, missing values, duplicates, numeric summaries, category frequencies, quality warnings
- Allowlisted analyses: filtered counts, grouped sums/averages, numeric summaries, ranked categories, date-range comparisons
- Result validation, including cross-checks between two independent engines
- Charts rendered from computed results, with exact-value tables alongside
- HTML report with the question, operations, results, warnings, and limitations
- A **Clear session** action that deletes server-side session data

Later phases (see the roadmap): predictive analytics with baselines and proper validation, a reusable workflow library, and packaging as a standalone local app.

## Architecture

```text
React + TypeScript (Vite)
  file picker · question input · preview · charts · report · clear session
        |
        |  HTTP to 127.0.0.1 only
        |  per-launch token · Origin and Host validation
        v
Local Python service (FastAPI + Uvicorn)
  Pydantic validation → Polars / DuckDB analysis → Pandera quality checks
  → cross-engine verification → chart specs (Plotly) → reports (Jinja2)
        |
        v
In-memory session store (deletable, with expiry)
```

The analysis code lives in `backend/src/genda/core/` and has no web-framework dependencies, so it can be tested in isolation and reused elsewhere.

## Privacy model & Workspace Security

GenDA implements a two-class data model backed by envelope encryption and crypto-shredding:

1. **Session Data (Never Persisted to MySQL):**
   - Raw CSV rows, in-memory Polars DataFrames, DuckDB connections, and cache files reside only in RAM or ephemeral local temp files.
   - Cleared via `Clear Session` or when the workspace key is removed.
2. **Workspace Knowledge (Opt-in Encrypted Metadata):**
   - Stored in MySQL and strictly scoped to a user-owned **workspace key** (`gk_<key_id>_<secret>`).
   - The server stores only an HKDF verifier and a wrapped Data Encryption Key (DEK). The key itself is never stored by the server or in browser storage (RAM only).
   - Sensitive metadata (column names, statistical profiles) is encrypted using AES-256-GCM with context-bound Associated Authenticated Data (AAD).
   - Raw data rows and sample values are never stored. Categorical frequencies below 5 are suppressed to prevent differential leakage.
3. **8-Step Purge & Crypto-Shredding:**
   - Removing the key or triggering an emergency purge destroys the wrapped DEK and verifier, wipes in-memory caches and frames, deletes MySQL rows, verifies zero residual data, and leaves a clean tombstone.

### Honest Limits

- **Physical disk erasure:** Deleting session or database data does not guarantee immediate physical erasure from solid-state storage (SSD wear-leveling), OS swap space, or OS disk caches.
- **External backups:** Backups or database snapshots made outside GenDA are outside its control. Crypto-shredding ensures sensitive columns in backups become unreadable once the wrapped DEK is destroyed, but unencrypted operational metadata remains in historical backups.
- **Process memory:** Application-level encryption protects data at rest in MySQL and defends against SQL-read extraction attacks. It cannot protect against a compromised operating system, kernel rootkit, or a process debugger attached to RAM.
- **No key recovery:** If you lose your workspace key, encrypted metadata cannot be decrypted or recovered, by cryptographic design.
- **Local single-user threat model:** GenDA is engineered for local, single-user (or small trusted team) analysis on loopback interfaces, not as a public multi-tenant SaaS cloud.


## Tech stack

| Layer | Tools |
|---|---|
| Frontend | React, TypeScript, Vite, `react-plotly.js`, Vitest |
| API | FastAPI, Uvicorn, Pydantic v2 |
| Data engines | Polars, DuckDB, pandas (interop only) |
| Statistics / ML | NumPy, SciPy, statsmodels, scikit-learn |
| Data quality | Pandera, charset-normalizer, RapidFuzz |
| Visualization | Plotly (chart specs), Kaleido (static images) |
| Reporting | Jinja2, WeasyPrint (PDF, later) |
| Quality tooling | pytest, Hypothesis, Ruff, mypy, uv |

## Getting started

> These steps describe the intended workflow once the scaffolding from roadmap Phase 1 is in place. Commands may change as the project develops.

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/), Node.js 20+ and npm.

```bash
# clone
git clone https://github.com/<your-username>/genda.git
cd genda

# backend
cd backend
uv sync
uv run python -m genda        # starts the local service and prints a one-time token

# frontend (in a second terminal)
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite. The interface connects to the local service using the launch token.

## Project structure

```text
genda/
├── README.md
├── implementation.md        # phased implementation plan
├── frontend/                # React + TypeScript UI
│   └── src/{app,components,api,state,utils}
├── backend/
│   ├── pyproject.toml
│   ├── src/genda/
│   │   ├── api/             # FastAPI app, routes, security
│   │   ├── core/            # loading, profiling, operations, validation, charts, reporting
│   │   └── session/         # in-memory session store
│   └── tests/               # fixtures with known answers, security and privacy tests
└── scripts/
```

## Testing

```bash
# backend
cd backend
uv run pytest --cov
uv run ruff check .
uv run mypy src

# frontend
cd frontend
npm test
```

Tests use small synthetic datasets with answers computed independently. Property-based tests (Hypothesis) cover edge cases such as empty columns, negative values, and mixed types. Security tests check token, origin, and host handling.

## Roadmap

- [ ] **Phase 0:** requirements and known-answer test data
- [ ] **Phase 1:** frontend and local-service skeleton with security tests
- [ ] **Phase 2:** CSV selection and preview
- [ ] **Phase 3:** data profiling
- [ ] **Phase 4:** deterministic analysis operations
- [ ] **Phase 5:** validation and evidence-based insights
- [ ] **Phase 6:** visualizations and reports
- [ ] **Phase 7:** privacy and security verification
- [ ] **Phase 8:** predictive analytics
- [ ] **Phase 9:** workflow library (Analytical Experience Engine)
- [ ] **Phase 10:** packaging and optional expanded access

Details and exit criteria for each phase are in [`implementation.md`](./implementation.md).

## Non-goals (for now)

- Running arbitrary generated code or natural-language-to-SQL
- Cloud accounts, collaboration, or remote data storage
- A single "accuracy score" across all features
- Autonomous model retraining or claims of self-learning

## Contributing

Contributions are welcome once the project skeleton is in place. Please:

1. Open an issue describing the change before large pull requests.
2. Include tests with known answers for any new analytical behavior.
3. Keep raw data out of logs, fixtures, and commits. Use synthetic or public datasets only.
4. Run the test suites and linters before submitting.

## Security

If you discover a vulnerability, especially one affecting the local service's authentication, origin checks, or data handling, please report it privately rather than in a public issue. Add a contact method or a `SECURITY.md` before publishing.

## License

Add a license before publishing (for example MIT or Apache-2.0) and reference it here: `LICENSE`.
