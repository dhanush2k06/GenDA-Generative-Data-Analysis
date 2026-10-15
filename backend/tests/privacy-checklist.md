# GenDA Privacy & Security Checklist (v2.0)

| Item | Requirement | Verification Method | Status |
|------|-------------|---------------------|--------|
| **1. Loopback Binding** | Service binds only to `127.0.0.1`, never `0.0.0.0`. | Checked in `__main__.py` & `SecurityHeadersMiddleware`. | Verified |
| **2. Per-launch Token** | Random cryptographic token generated on launch (`secrets.token_urlsafe`). | Enforced by `verify_token` via `X-GenDA-Token`. | Verified |
| **3. Origin Validation** | Strict CORS allowlist (`localhost:5173`, `127.0.0.1:5173`). No wildcard `*`. | `SecurityHeadersMiddleware` rejects foreign origins. | Verified |
| **4. Host Header Check** | Host header restricted to `127.0.0.1`, `localhost` to block DNS rebinding. | Enforced in `SecurityHeadersMiddleware`. | Verified |
| **5. Zero Outbound Telemetry** | No outbound tracking, analytics, or remote HTTP requests. | Code inspection: zero remote HTTP calls in backend analysis. | Verified |
| **6. In-Memory Persistence** | Raw CSV data parsed into RAM (Polars DataFrame) only. No database / disk write. | Stored in `SessionStore` memory only. | Verified |
| **7. Explicit Session Deletion** | `DELETE /session/{id}` clears DataFrames and cached results. | Tested in `test_security.py`. | Verified |
| **8. No Raw Row Logging** | Exceptions and server logs must never dump raw rows or secret files. | Handled via custom exception handlers & access_log=False. | Verified |
| **9. Cross-Engine Verification** | Key aggregations cross-validated against DuckDB independently. | Tested in `test_validation.py`. | Verified |
