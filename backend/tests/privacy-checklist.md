# GenDA Privacy & Security Checklist (v2.0)

| Item | Requirement | Verification Method | Status |
|------|-------------|---------------------|--------|
| **1. Loopback Binding** | Service binds only to `127.0.0.1`, never `0.0.0.0`. | Checked in `__main__.py` & `SecurityHeadersMiddleware`. | Verified |
| **2. Per-launch Token** | Random cryptographic token generated on launch (`secrets.token_urlsafe`). | Enforced by `verify_token` via `X-GenDA-Token`. | Verified |
| **3. Origin Validation** | Strict CORS allowlist (`localhost:5173`, `127.0.0.1:5173`). No wildcard `*`. | `SecurityHeadersMiddleware` rejects foreign origins. | Verified |
| **4. Host Header Check** | Host header restricted to `127.0.0.1`, `localhost` to block DNS rebinding. | Enforced in `SecurityHeadersMiddleware`. | Verified |
| **5. Zero Outbound Telemetry** | No outbound tracking, analytics, or remote HTTP requests. | Code inspection: zero remote HTTP calls in backend analysis. | Verified |
| **6. In-Memory Persistence** | Raw CSV data parsed into RAM (Polars DataFrame) only. No raw dataset write to MySQL. | Datasets stay in RAM only; `SessionStore` & `WorkspaceResourceRegistry`. | Verified |
| **7. Explicit Session Deletion** | `DELETE /session/{id}` clears DataFrames and cached results. | Tested in `test_security.py`. | Verified |
| **8. No Raw Row Logging** | Exceptions and server logs must never dump raw rows or secret files. | Handled via custom exception handlers & access_log=False. | Verified |
| **9. Cross-Engine Verification** | Key aggregations cross-validated against DuckDB independently. | Tested in `test_validation.py`. | Verified |
| **10. Parameterized Queries Only** | Zero SQL built from string formatting, concatenation, or f-strings. | SQLAlchemy ORM & Core bind parameters only; verified in `test_sql_injection.py`. | Verified |
| **11. Untrusted CSV Metadata Guard** | Column names and categories from CSVs are untrusted data, never spliced into SQL identifiers. | Tested in `test_sql_injection.py` with payload corpus. | Verified |
| **12. Workspace Key Protection** | High-entropy secret (`gk_<id>_<secret>`); server stores verifier only; browser keeps in RAM only. | Tested in `test_envelope_encryption.py`; rate limiting and lockout verified. | Verified |
| **13. Envelope Encryption & AAD** | Sensitive fields encrypted with AES-256-GCM bound to workspace ID, table, column, row ID. | Tested in `test_envelope_encryption.py`. | Verified |
| **14. Multi-Tenant Schema Isolation** | Composite primary keys `(workspace_id, id)` and composite foreign keys block cross-workspace access. | Tested in `test_tenant_isolation.py`. | Verified |
| **15. Crypto-Shredding & Purge** | Key removal / purge executes 8-step pipeline: deletes wrapped DEK, clears memory, purges DB rows, and verifies zero residue. | Tested in `test_purge.py`. | Verified |
| **16. Purge Crash-Recovery Sweeper** | Interrupted purges in `revoking` status or expired workspaces are detected and completed on startup. | Tested in `test_purge.py` (`test_crash_recovery_sweeper`). | Verified |
