"""
GenDA service CLI launcher.
Binds to 127.0.0.1 (loopback) only, generates a random launch token,
and launches the Uvicorn server.
"""

from __future__ import annotations
import sys
import argparse
import uvicorn
from pathlib import Path

from genda.api.security import get_active_token, set_active_token
from genda.session.store import session_store


def main():
    parser = argparse.ArgumentParser(description="GenDA Local Analysis Service")
    parser.add_argument("--port", type=int, default=8000, help="Loopback port (default: 8000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host (strictly 127.0.0.1)")
    parser.add_argument("--token", type=str, default=None, help="Explicit token (random by default)")
    args = parser.parse_args()

    # Enforce loopback binding strictly
    if args.host not in ("127.0.0.1", "localhost"):
        print("[GenDA Error] For security, GenDA only binds to 127.0.0.1 (loopback).", file=sys.stderr)
        sys.exit(1)

    if args.token:
        set_active_token(args.token)

    token = get_active_token()

    # Save active token locally for development auto-configuration
    token_path = Path(".genda_token")
    try:
        token_path.write_text(token, encoding="utf-8")
    except Exception:
        pass

    print("=" * 60)
    print("  GenDA — Generative Data Analyst (Local Service v0.2.0)")
    print("=" * 60)
    print(f"  Loopback URL:  http://127.0.0.1:{args.port}")
    print(f"  Security Token: {token}")
    print("  Bound Strictly: 127.0.0.1 (Never exposes to public network)")
    print("=" * 60)

    try:
        uvicorn.run(
            "genda.api.app:app",
            host=args.host,
            port=args.port,
            log_level="info",
            access_log=False,  # Privacy: avoid logging raw query strings/payloads
        )
    finally:
        print("\nShutting down GenDA service... dereferencing all in-memory sessions.")
        session_store.clear_all()
        if token_path.exists():
            try:
                token_path.unlink()
            except Exception:
                pass


if __name__ == "__main__":
    main()
