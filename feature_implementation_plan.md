# GenDA Feature Plan: MySQL Metadata Store and Workspace Keys

**Project:** GenDA — Generative Data Analyst  
**Document:** `feature_implementation_plan.md`  
**Extends:** `implementation.md` v2.0 (Phases 7, 9 and 10)  
**Status:** Proposed. Includes a review of the original feature ideas, the recommended changes, and a phased plan.

---

## Part 1 — Review of the two requested features

### Feature 1 (as requested)
Connect the application to MySQL to store dataset metadata and the techniques/algorithms used in analysis, so they can be reused on similar datasets, with protection against SQL injection.

### Feature 2 (as requested)
Enhance the token key so operations and tasks are saved and secured per key. When the key is removed, the dataset, the operations/analysis, and the cache are removed completely.

### Findings

| # | Finding | Why it matters | Recommended change |
|---|---|---|---|
| 1 | **The two features conflict.** Feature 1 keeps knowledge for reuse on future datasets; Feature 2 deletes all operations and analysis when the key is removed. | Without a rule, either reuse breaks or deletion is incomplete. | Split stored data into two classes: **session data** (datasets, in-memory frames, caches, temp files) and **workspace knowledge** (metadata, recipes, outcomes). Both are scoped to the key and both are purged on removal. The reusable library is **workspace-private by default**. An opt-in export or anonymized sharing can come later. |
| 2 | **The current token is per-launch.** In v2.0 a random token is generated each time the service starts. | A key that changes every launch cannot own persistent metadata. | Introduce a **workspace key**: a high-entropy secret created by the user, shown once, and never stored by the server. The existing per-launch token stays as the transport guard. |
| 3 | **"Removed completely" is hard in MySQL.** Deleted rows can remain in InnoDB pages, binary logs, and backups. | A plain `DELETE` does not guarantee unrecoverability. | Use **envelope encryption with crypto-shredding**: sensitive columns are encrypted in the app with a per-workspace data key (DEK), wrapped with a key derived from the workspace key. Removing the wrapped DEK makes leftover ciphertext unreadable. Row deletion and cache purge still run, but the guarantee no longer depends on them alone. |
| 4 | **Metadata can leak sensitive information.** Column names, category values, and frequency tables can reveal business or personal details. | "Metadata only" is not automatically safe. | Define a **data classification** (Part 3). Never store raw rows or sample values. Store aggregates only, encrypt sensitive fields, and enforce minimum-count thresholds on categorical statistics. |
| 5 | **Parameterized queries alone are not a complete SQL-injection defense.** | Column names from uploaded CSVs are untrusted and could be reused later (second-order injection). | Layer the defenses: SQLAlchemy bind parameters only, fixed schema with no dynamic identifiers, input validation, least-privilege DB user, risky MySQL features disabled, static analysis, and dynamic testing. Treat everything derived from a CSV as untrusted data forever. |
| 6 | **Caches can leak across keys.** A global `lru_cache` or shared temp directory keyed by anything but the workspace would survive key removal or serve another key's data. | Cache purge cannot be verified if caches are scattered. | A single **workspace resource registry**: every cache, temp file, dataframe, and DuckDB connection is registered under a workspace ID. Purge iterates the registry. Ban un-namespaced global caches in code review and by lint rule. |
| 7 | **Key removal must handle in-flight work.** | A running analysis could recreate data after the purge. | Purge is a state machine: `active → revoking → revoked`. New requests are rejected immediately, running tasks are cancelled, and the purge job is resumable after a crash. |
| 8 | **Browser-side state is also cache.** | Server purge leaves previews, charts, and keys in the browser. | The frontend keeps the key in memory only and clears all client state on removal. The server also sends `Clear-Site-Data` on revocation. |
| 9 | **MySQL is heavy for a local-first tool.** | Operational burden and a larger attack surface for single-user installs. | Keep MySQL as requested, but access it through a **repository layer on SQLAlchemy** so SQLite can serve tests and lightweight installs later. Run MySQL on loopback or a Unix socket with a dedicated least-privilege account. |
| 10 | **"Similar datasets" is undefined.** | Without a definition, reuse is unmeasurable and risks wrong recommendations. | Define similarity in stages (Part 4, Phase F5). Recommendations are suggestions only: the user confirms, the recipe is re-validated on the new data, and it is compared against a baseline. |
| 11 | **Stored techniques must never become executable content.** | A tampered record could become a code-execution path. | Recipes are **structured, schema-validated specs** (the existing allowlisted operations with column *roles*), loaded through Pydantic. No pickled models, no stored code or SQL. |
| 12 | **Users need control.** | Persistent storage changes the privacy expectations set in v2.0. | **Opt-in per dataset** ("save metadata for reuse"), plus a viewer to inspect, export, and delete stored metadata, and a configurable retention period. |

### Decisions to confirm before building

| Decision | Recommendation |
|---|---|
| Is the reusable library shared across keys? | **No.** Private per workspace for v1. Opt-in anonymized sharing is a later feature. |
| Are raw datasets ever stored in MySQL? | **No.** Datasets stay in memory or a controlled, encrypted temp workspace. MySQL stores metadata only. |
| Does a lost key recover data? | **No, by design.** Document this clearly. A recovery code can be considered later. |
| Is metadata saving opt-in? | **Yes**, per dataset and per workspace default. |
| Key expiry | Configurable idle and absolute expiry. Expiry triggers the same purge as manual removal. |
| What does "key removed" cover? | Manual revoke, expiry, and an emergency "clear everything" action all run the same purge path. |

---

## Part 2 — Revised feature definitions

### Feature 1 (revised): Workspace-scoped metadata and technique library in MySQL
- Persist dataset fingerprints, profile aggregates, analysis-run records, and reusable **recipes** (structured technique specs) in MySQL.
- Encrypt sensitive fields at the application layer before they reach the database.
- Recommend recipes for new, similar datasets, with explanations, user confirmation, re-validation, and baseline comparison.
- Defend the database layer against SQL injection in depth, and prove it with tests.

### Feature 2 (revised): Workspace key with scoped storage and complete purge
- A workspace key identifies and authenticates one workspace. The server stores only a verifier, never the key.
- Every stored record, cache entry, and temp file belongs to exactly one workspace and is accessible only with that workspace's key.
- Removing the key (or expiry) triggers a verified, resumable purge across memory, caches, temp files, MySQL, and browser state, plus crypto-shredding.

---

## Part 3 — Design

### 3.1 Architecture additions

```text
React UI
  key entry/creation · metadata consent · library viewer · remove-key flow
        |  HTTP to 127.0.0.1 · launch token · workspace key (Authorization header)
        v
FastAPI service
  auth middleware → WorkspaceContext (workspace_id, DEK in memory only)
        |
  +-----+--------------------------------------------------+
  |                                                        |
  v                                                        v
Analysis core (Polars / DuckDB)                   Repository layer (SQLAlchemy)
  datasets, caches, temp files                      every method requires WorkspaceContext
  registered in WorkspaceResourceRegistry           bind parameters only · encrypt/decrypt
        |                                                  |
        +------------------ Purge engine ------------------+
                                                           v
                                                 MySQL (loopback / socket)
                                                 least-privilege app account
```

### 3.2 Workspace key design
- **Format:** `gk_<key_id>_<secret>` where `key_id` is a public lookup ID and `secret` is 256 bits from `secrets.token_urlsafe(32)`. Shown to the user once.
- **Server storage:** only a **verifier** derived from the secret with HKDF (label `verify`). The encryption key derivation uses a different HKDF label (`kek`), so the stored verifier cannot be used to decrypt anything.
- **Comparison:** constant-time (`hmac.compare_digest`).
- **Transport:** `Authorization` header only. Never in URLs, logs, or error messages.
- **Browser storage:** in memory only. No `localStorage`, `sessionStorage`, or cookies for the key.
- **Abuse protection:** rate limiting and temporary lockout on failed attempts per `key_id`.
- **Lifecycle:** create → active → (rotate) → revoking → revoked. Expiry (idle and absolute) is enforced server-side.

### 3.3 Envelope encryption
1. On workspace creation, generate a random 256-bit **DEK**.
2. Derive a **KEK** from the workspace key with HKDF; wrap the DEK with AES-256-GCM; store `wrapped_dek`.
3. On login, derive the KEK, unwrap the DEK, and hold it in memory for the session only.
4. Encrypt sensitive columns with AES-GCM using the DEK. Bind each ciphertext to its context with associated data (workspace ID, table, column, row ID) so ciphertexts cannot be swapped between rows or workspaces.
5. On revoke, **delete `wrapped_dek` first**. Anything left in pages, logs, or backups is then unreadable.

Use a well-reviewed library (Python `cryptography`). Do not implement primitives yourself.

### 3.4 Data classification

| Class | Examples | Storage rule |
|---|---|---|
| **Never stored** | Raw rows, sample values, free-text cell contents | Not persisted in MySQL, logs, or caches beyond the session |
| **Sensitive metadata** | Column names, dataset name, operation parameters, categorical value frequencies, profile statistics | Encrypted with the workspace DEK; categorical frequencies only above a minimum count |
| **Operational metadata** | Operation type, validation status, runtime, row/column counts, library versions, timestamps | Plaintext allowed (low leakage risk). Coarse bucketing optional |
| **Secrets** | Workspace key, DEK, DB credentials | Key and DEK never stored in plaintext; DB credentials from environment or secret store, never committed |

### 3.5 Data model (illustrative)

Every table carries `workspace_id` as the leading primary-key column. This gives natural scoping, fast per-workspace queries, and simple purge. Child tables use **composite foreign keys** `(workspace_id, parent_id)`, so a child can never reference another workspace's parent.

```sql
CREATE TABLE workspaces (
  id            BINARY(16)    NOT NULL PRIMARY KEY,
  key_id        CHAR(16)      NOT NULL UNIQUE,
  key_verifier  BINARY(32)    NULL,                -- cleared on revoke
  wrapped_dek   VARBINARY(96) NULL,                -- cleared first on revoke
  status        ENUM('active','revoking','revoked') NOT NULL,
  created_at    DATETIME(3)   NOT NULL,
  expires_at    DATETIME(3)   NULL,
  last_seen_at  DATETIME(3)   NULL,
  revoked_at    DATETIME(3)   NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE datasets (
  workspace_id  BINARY(16)     NOT NULL,
  id            BINARY(16)     NOT NULL,
  fingerprint   BINARY(32)     NOT NULL,           -- keyed hash of schema signature
  name_enc      VARBINARY(512) NULL,
  row_count     BIGINT UNSIGNED NOT NULL,
  col_count     INT UNSIGNED   NOT NULL,
  profile_enc   MEDIUMBLOB     NOT NULL,           -- encrypted aggregate profile
  created_at    DATETIME(3)    NOT NULL,
  PRIMARY KEY (workspace_id, id),
  KEY idx_fingerprint (workspace_id, fingerprint),
  FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE analysis_runs (
  workspace_id      BINARY(16)  NOT NULL,
  id                BINARY(16)  NOT NULL,
  dataset_id        BINARY(16)  NOT NULL,
  recipe_id         BINARY(16)  NULL,
  operation         VARCHAR(64) NOT NULL,
  params_enc        BLOB        NOT NULL,          -- encrypted parameters
  validation_status ENUM('passed','warning','failed') NOT NULL,
  runtime_ms        INT UNSIGNED NULL,
  library_versions  JSON        NOT NULL,
  created_at        DATETIME(3) NOT NULL,
  PRIMARY KEY (workspace_id, id),
  FOREIGN KEY (workspace_id, dataset_id)
    REFERENCES datasets(workspace_id, id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

Other tables follow the same pattern:

- `dataset_columns`: per-column type class, encrypted name, keyed name hash, null-rate and cardinality features.
- `recipes`: structured technique specs with column *roles*, prerequisites, and a version.
- `recipe_outcomes`: metrics, baseline delta, validation status, and user feedback per run.
- `purge_jobs`: workspace ID, state, completed steps, timestamps (no data).
- `audit_events`: action, key ID, timestamp. No dataset content.

The `workspaces` row is kept as a **tombstone** after revocation (key ID and `revoked_at` only), so a revoked key returns a clear error and cannot be re-registered by accident. All data rows are deleted.

### 3.6 SQL-injection defense in depth

1. **Bind parameters only.** All database access goes through SQLAlchemy Core/ORM. No SQL built with f-strings, `%`, `.format`, or concatenation.
2. **No dynamic identifiers.** The schema is fixed. Any sorting or filtering the UI needs maps from an allowlisted enum to a column object.
3. **Validate at the boundary.** Pydantic enforces types, lengths, and patterns on every request.
4. **Second-order safety.** Column names, categories, and file names from CSVs are untrusted data. They are stored and later passed only as bound values, never spliced into SQL. The same discipline applies to the DuckDB path: quote identifiers with the library's quoting function and bind values.
5. **Least privilege.** The application account has only `SELECT, INSERT, UPDATE, DELETE` on the GenDA schema. A separate migration account holds DDL rights and is used only by Alembic. No `FILE`, `SUPER`, or `GRANT OPTION`.
6. **Harden MySQL.** Bind to `127.0.0.1` or a Unix socket; `local_infile=OFF`; multi-statement execution off; strict `sql_mode`; general query log off; short binary-log retention; remove anonymous users and the test schema; set `max_user_connections` and a query timeout.
7. **Safe errors.** Return generic messages with a correlation ID. Never return raw SQL errors to the client.
8. **Bounded results.** Enforce `LIMIT`s and pagination on every list endpoint.
9. **Encryption as a backstop.** Even if an injection read were possible, sensitive columns are ciphertext without the in-memory DEK.
10. **Automated enforcement.** Static analysis (Ruff security rules such as `S608`, Bandit, and a Semgrep rule banning string-built SQL), plus the dynamic tests in Phase F7.

### 3.7 Purge design ("key removed → everything removed")

Triggered by: manual removal, key expiry, or an emergency "clear everything" action. All use one code path.

| Step | Action |
|---|---|
| 1 | Atomically set workspace status to `revoking`. All new requests for that key return `401`/`410`. |
| 2 | Cancel running tasks for the workspace (task registry with cancellation tokens) and wait with a timeout. |
| 3 | **Crypto-shred:** delete `wrapped_dek` and `key_verifier`. Wipe the in-memory DEK. |
| 4 | Drop in-memory dataframes, close DuckDB connections, and release the session. |
| 5 | Purge every cache and temp resource registered for the workspace. Delete the workspace's temp directory, generated reports, and chart images. |
| 6 | Delete all MySQL rows for the workspace (datasets cascade to dependents) in a transaction. Keep only the tombstone. |
| 7 | **Verify:** zero rows by `workspace_id`, registry empty, temp directory gone, no cache keys remaining. Record counts-only in `purge_jobs`. |
| 8 | Return a purge report (counts only) with a `Clear-Site-Data` header so the browser drops cached and stored state. The frontend also clears its in-memory state. |

The purge job is **idempotent and resumable**: if the process crashes midway, a startup sweeper finds workspaces in `revoking` state and finishes the job. The same sweeper handles expired keys and orphaned temp directories.

### 3.8 Honest limits (to document in the README)
- Deleting data does not guarantee immediate physical erasure from disk, SSD wear-leveling, OS swap, or the OS page cache.
- Backups and database replicas made outside GenDA are outside its control. Crypto-shredding makes sensitive columns in those copies unreadable once the wrapped DEK is gone, but plaintext operational metadata remains in old backups.
- App-level encryption protects data at rest and against SQL-read attacks. It does not protect against a compromised running process or a user with access to process memory.
- A lost key means unrecoverable data, by design.
- The key and the service run on the user's own machine, so the threat model is a local, single-user (or small-team) setting, not a hostile multi-tenant cloud.

---

## Part 4 — Implementation plan

Phase labels use an `F` prefix to avoid colliding with the Phase numbers in `implementation.md`. Build in order. Each phase has exit criteria that must pass before moving on.

### Phase F0 — Decisions, threat model, and data classification
1. Confirm the decisions table in Part 1.
2. Write a short threat model covering: SQL injection, cross-workspace access, key theft or guessing, stale caches, crash during purge, backups and logs, and browser-side leakage.
3. Finalize the data classification (Part 3.4) and the minimum-count threshold for categorical statistics.
4. Define the default retention period and the consent flow wording.
5. Update the privacy checklist (`backend/tests/privacy-checklist.md`) with persistence-related checks.

**Exit criteria:** Decisions, threat model, and classification are written and reviewed.

### Phase F1 — MySQL foundation
1. Add dependencies: SQLAlchemy 2.x, a MySQL driver (PyMySQL or mysqlclient), Alembic, `cryptography`.
2. Provide a dev setup (for example, a Docker Compose service) with the hardened configuration from Part 3.6, and document the same settings for local installs.
3. Create two accounts: a restricted **app** account and a **migration** account. Load credentials from environment variables or a secret store. Ignore `.env` files in Git.
4. Build the engine/session factory with connection pooling, timeouts, and `utf8mb4`. Enable strict SQL mode.
5. Add Alembic migrations for the Part 3.5 tables.
6. Add a database health check to `/health` that reports status only, never connection details.
7. Add MySQL as a service in CI for integration tests.

**Exit criteria:** Migrations apply cleanly from empty; the app account cannot perform DDL; the service starts and reports DB health.

### Phase F2 — Workspace key and authentication
1. Implement key generation, the `gk_<key_id>_<secret>` format, HKDF verifier derivation, and constant-time verification.
2. Implement workspace creation: generate the DEK, derive the KEK, wrap the DEK, and store only `key_id`, verifier, and wrapped DEK.
3. Add the auth middleware that resolves the `Authorization` header into a `WorkspaceContext` (workspace ID plus the in-memory DEK). The context comes only from the verified key, **never from a request parameter or body**.
4. Add rate limiting and lockout on failed key attempts.
5. Add key lifecycle endpoints: create, validate, rotate (re-wrap DEK), and remove (hands off to the purge engine).
6. Create the **WorkspaceResourceRegistry** now, before caches and temp files proliferate. Add a lint or review rule that bans un-namespaced global caches.
7. Update the frontend: key creation (show once, require acknowledgement), key entry, in-memory key storage, and a visible active-workspace indicator.

**Exit criteria:** A key authenticates a workspace; wrong keys, missing keys, and locked-out keys fail safely; the key never appears in URLs, logs, or browser storage.

### Phase F3 — Scoped persistence layer
1. Build repository classes (`WorkspaceRepo`, `DatasetRepo`, `RunRepo`, `RecipeRepo`). Every method requires a `WorkspaceContext` and adds the `workspace_id` condition itself. Route handlers never write queries.
2. Implement the envelope-encryption helper with context-bound AES-GCM and handle decryption failures as safe errors.
3. Use composite foreign keys so children cannot reference another workspace's parents.
4. Add a repository-level guard that raises an error if any query is built without a workspace scope.
5. Write tenant-isolation tests: workspace A can never read, update, or delete workspace B's records by ID guessing, even with valid IDs.

**Exit criteria:** Isolation tests pass; ciphertext in the database is unreadable without the DEK; swapping ciphertext between rows or workspaces fails authentication.

### Phase F4 — Metadata capture and user control
1. Add the consent flow: per-dataset "Save metadata for reuse", with a workspace-level default.
2. Build the dataset **fingerprint**: a keyed hash of the normalized schema signature (column-name hashes and type classes), plus per-column features (type class, null-rate bucket, distinct ratio, numeric skew bucket, date granularity).
3. Persist the profile aggregates, applying the minimum-count rule to categorical frequencies. Never persist sample values.
4. Record each analysis run: operation, parameters, validation status, runtime, and the versions of Polars, DuckDB, SciPy, statsmodels, scikit-learn, and the random seed.
5. Capture **recipes** from successful, validated runs as structured specs using column *roles* (for example `group_by: categorical`, `metric: numeric`) instead of column names.
6. Build a metadata viewer in the UI: list what is stored, export it, and delete individual items.
7. Apply the retention period with a scheduled cleanup.

**Exit criteria:** Opt-out stores nothing; opt-in stores only classified fields; a database dump contains no raw values and no plaintext sensitive fields.

### Phase F5 — Similarity matching and recipe reuse
Start with transparent heuristics, and tune them with test data instead of trusting initial weights.

1. **Stage 1, exact match:** same schema fingerprint within the workspace.
2. **Stage 2, structural match:** column-set overlap (Jaccard) with fuzzy name matching (RapidFuzz, done in memory after decrypting) and type compatibility.
3. **Stage 3, profile match:** similarity of null rates, cardinality ratios, skewness buckets, and size class.
4. Combine into a score with documented, tunable weights, and calibrate thresholds using pairs of known similar and known dissimilar synthetic datasets.
5. Return ranked suggestions with an **explanation** ("8 of 10 columns matched; types compatible").
6. Never auto-run. Show a proposed column mapping that the user can edit.
7. Bind the recipe to the new dataset, then **re-validate** (Phase 5 checks) and compare against a simple baseline before presenting results as improved.
8. Record outcomes and user feedback in `recipe_outcomes`, and use them to rank future suggestions.

**Exit criteria:** On benchmark pairs, similar datasets are matched and dissimilar ones are not, at documented precision/recall; reused recipes are validated before display; a failed validation never silently shows results.

### Phase F6 — Purge and revocation engine
1. Implement the `active → revoking → revoked` state machine and the request gate that rejects work for revoking workspaces.
2. Implement a task registry with cancellation tokens and a bounded wait.
3. Implement the purge steps in Part 3.7 in order, with crypto-shredding as step 3.
4. Persist progress in `purge_jobs`, make every step idempotent, and add the startup sweeper for interrupted purges, expired keys, and orphaned temp directories.
5. Add the frontend remove-key flow: show what will be deleted (counts only), require type-to-confirm, clear all client state, and handle the `Clear-Site-Data` response.
6. Add the emergency "clear everything" action using the same code path.
7. Write the post-purge verifier and expose its counts-only report.

**Exit criteria:** After removal, the verifier shows zero rows, an empty registry, no temp files, and no cache entries for the workspace; killing the process mid-purge and restarting completes the purge; the key no longer authenticates.

### Phase F7 — Security verification
**SQL injection**
- Unit tests with a payload corpus (classic, boolean/time-based, stacked statements, encoded, and second-order via CSV column names and category values) against every endpoint and repository method.
- Run **sqlmap** against a local test instance, and fuzz the OpenAPI schema with **Schemathesis**.
- Static checks in CI: Ruff security rules, Bandit, and the Semgrep rule for string-built SQL.
- Verify the app account cannot run DDL, read files, or touch other schemas.

**Isolation and key handling**
- Cross-workspace access tests, including ID guessing and forged workspace IDs in request bodies.
- Brute-force and lockout tests; confirm no key material in logs, errors, URLs, or browser storage.

**Purge**
- Completeness tests across memory, caches, temp files, MySQL, and browser state.
- Concurrency test: start an analysis, remove the key mid-run, and confirm nothing is recreated.
- Crash-recovery test for the sweeper.
- Confirm that after revoke, a raw database dump (including binary logs) contains no decryptable sensitive data.

**Configuration audit**
- Verify the MySQL hardening list from Part 3.6 against a running instance, and record the result in the privacy checklist.

**Exit criteria:** All suites pass in CI; the checklist is complete; known limits are documented in the README.

### Phase F8 — Hardening and optional extensions
- Short-lived **session tokens** exchanged from the workspace key, so the key is used only at login.
- Key rotation UI and an audit-event viewer (no data content).
- Backup guidance and an optional encrypted export/import of a workspace's library.
- Optional opt-in **anonymized** sharing of technique statistics across workspaces, only after a separate de-identification design and review.
- Optional SQLite backend for single-user installs through the same repository layer.

---

## Part 5 — Repository additions

```text
backend/src/genda/
├── auth/
│   ├── keys.py             # key format, HKDF, verification
│   ├── context.py          # WorkspaceContext, auth middleware
│   └── ratelimit.py
├── crypto/
│   └── envelope.py         # DEK/KEK, AES-GCM with bound associated data
├── db/
│   ├── engine.py
│   ├── models.py
│   ├── migrations/         # Alembic
│   └── repositories/       # workspaces, datasets, runs, recipes (workspace-scoped)
├── workspace/
│   ├── registry.py         # WorkspaceResourceRegistry (caches, temp files, frames)
│   ├── tasks.py            # task registry with cancellation
│   ├── purge.py            # purge state machine and verifier
│   └── sweeper.py          # startup/periodic cleanup
└── similarity/
    ├── fingerprint.py
    ├── matcher.py
    └── adapter.py          # bind recipes to a new dataset's columns

backend/tests/
├── test_sql_injection.py
├── test_tenant_isolation.py
├── test_envelope_encryption.py
├── test_purge.py
└── test_similarity.py
```

## Part 6 — Testing summary

| Area | Tests |
|---|---|
| SQL injection | Payload corpus, second-order cases, sqlmap, Schemathesis, static rules |
| Isolation | Cross-workspace read/update/delete attempts, forged IDs, composite-FK enforcement |
| Cryptography | Round trips, wrong key, tampered ciphertext, swapped ciphertext, DEK deletion |
| Key handling | Lockout, constant-time comparison, no secrets in logs or storage |
| Purge | Completeness, idempotence, crash recovery, concurrent analysis, verifier accuracy |
| Similarity | Benchmark pairs, threshold calibration, explanation correctness, baseline comparison |
| Frontend | Key flow, consent flow, removal flow, state cleared after removal |

## Part 7 — Definition of done

- [ ] MySQL runs with the documented hardening; the app account has only DML rights.
- [ ] No SQL in the codebase is built from strings; CI enforces this.
- [ ] The injection payload suite, sqlmap run, and schema fuzzing pass.
- [ ] The workspace key is never stored by the server or in browser storage, and never appears in logs.
- [ ] Every record, cache entry, and temp file belongs to exactly one workspace.
- [ ] Tenant-isolation tests pass, including forged-ID cases.
- [ ] Sensitive metadata columns are encrypted; a database dump reveals no raw values or plaintext sensitive fields.
- [ ] Removing a key purges memory, caches, temp files, MySQL rows, and browser state, and the verifier confirms it.
- [ ] A crash mid-purge is recovered on restart.
- [ ] Recipe suggestions are explained, user-confirmed, re-validated, and compared against a baseline.
- [ ] README and privacy checklist state the limits in Part 3.8 accurately.

## Part 8 — Updates needed in `implementation.md`
- **Section 2 (MVP scope):** note that metadata persistence is opt-in and workspace-scoped.
- **Section 3 (privacy model):** replace "does not persist by default" with the two data classes and the workspace-key model.
- **Phase 7:** add the persistence, injection, isolation, and purge checks from Phase F7.
- **Phase 9:** reference this plan as the implementation of the Analytical Experience Engine, using MySQL instead of SQLite.
- **Phase 10:** add the MySQL setup and secret handling to packaging requirements.
