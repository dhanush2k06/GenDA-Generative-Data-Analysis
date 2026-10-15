# GenDA — Generative Data Analyst (v2.0)

A local-first, privacy-preserving data analysis application built according to [`implementation.md`](./implementation.md).

- **Architecture:** React + TypeScript + Vite frontend with a local loopback Python service (FastAPI + Polars + DuckDB).
- **Privacy Model:** 100% loopback (`127.0.0.1`). Datasets reside only in local RAM. Zero cloud leakage, zero remote telemetry.
- **Verification:** Cross-engine calculation checks comparing Polars and DuckDB independently.
- **Visuals & Reports:** Interactive Plotly visual specifications and downloadable Jinja2 self-contained HTML reports.

---

## Quick Start (One Command)

### Option A: Windows PowerShell
```powershell
.\run.ps1
```

### Option B: Windows Command Prompt (CMD)
```cmd
run.bat
```

---

## Manual Step-by-Step Commands

### 1. Start the Python Backend Service

From the project root:

```powershell
backend\.venv\Scripts\python.exe -m genda --port 8000 --token dev-token-local-genda-123
```

- Binds strictly to `http://127.0.0.1:8000` (loopback only)
- Interactive API Documentation (Swagger): `http://127.0.0.1:8000/docs`
- Security Token: `dev-token-local-genda-123`

### 2. Start the Frontend Development Server

In a second terminal window:

```powershell
npm run dev
```

- Open in your browser: `http://127.0.0.1:5173/`
- All `/api` requests are automatically proxied to the loopback backend at `http://127.0.0.1:8000`

---

## Production / Single-Origin Mode

You can also run the entire application from a single port (`127.0.0.1:8000`), where the Python backend directly serves the pre-built frontend:

```powershell
# 1. Build the frontend production bundle
npm run build

# 2. Start the backend service
backend\.venv\Scripts\python.exe -m genda --port 8000 --token dev-token-local-genda-123
```

Then visit: **`http://127.0.0.1:8000/`**

---

## Running the Verification Test Suite

To run all 11 backend unit and security tests:

```powershell
cd backend
.venv\Scripts\pytest.exe -v
```
