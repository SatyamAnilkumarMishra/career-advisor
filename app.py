#!/usr/bin/env python3
"""Convenience runner for Career Advisor: api / cli / mcp / install / setup / status / doctor."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

# Ensure UTF-8 output encoding across Windows / Linux / macOS terminals
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def check_requirements() -> bool:
    try:
        import fastapi  # noqa: F401
        import langchain  # noqa: F401
        import uvicorn  # noqa: F401

        return True
    except ImportError as exc:
        print(f"[X] Missing required packages: {exc}")
        print("Install them with: pip install -r requirements.txt")
        return False


def check_env() -> bool:
    if not os.path.exists(".env"):
        print("[X] .env file not found")
        print("Run: python app.py setup   (then edit .env with your API key)")
        return False

    try:
        from backend.config import ConfigError, get_settings

        get_settings()
    except ConfigError as exc:
        print(f"[X] Configuration problem: {exc}")
        return False
    except Exception as exc:  # pragma: no cover
        print(f"[X] Unexpected configuration error: {exc}")
        return False

    print("[OK] Environment configured correctly")
    return True


def run_api(host: str = "127.0.0.1", port: int = 8000, reload: bool = True) -> None:
    print("=" * 60)
    print("🚀 Career Advisor AI Platform")
    print(f"👉 Web App & API: http://{host}:{port}")
    print("=" * 60)
    try:
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.server:app",
            "--host",
            host,
            "--port",
            str(port),
        ]
        if reload:
            cmd.append("--reload")
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"[X] Failed to start server: {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Server stopped")


def run_mcp() -> None:
    print("Starting Career Advisor MCP server...")
    try:
        subprocess.run([sys.executable, "-m", "backend.mcp_server"], check=True)
    except subprocess.CalledProcessError as exc:
        print(f"[X] Failed to start MCP server: {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nMCP server stopped")


def run_cli() -> None:
    print("Starting CLI interface...")
    try:
        subprocess.run([sys.executable, "-m", "backend.main"], check=True)
    except subprocess.CalledProcessError as exc:
        print(f"[X] Failed to start CLI: {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCLI stopped")


def install_requirements() -> None:
    req_path = "backend/requirements.txt" if os.path.exists("backend/requirements.txt") else "requirements.txt"
    print(f"Installing backend requirements from {req_path}...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req_path], check=True
        )
        print("[OK] Backend requirements installed successfully")
    except subprocess.CalledProcessError as exc:
        print(f"[X] Failed to install requirements: {exc}")
        sys.exit(1)


def create_sample_env() -> None:
    if os.path.exists(".env"):
        print("[!] .env already exists")
        if input("Overwrite it? (y/N): ").strip().lower() != "y":
            print("[X] Cancelled")
            return

    with open(".env.example") as src, open(".env", "w") as dst:
        dst.write(src.read())

    print("[OK] Created .env from .env.example")
    print("Edit .env and add your API key (GROQ_API_KEY or GOOGLE_API_KEY)")


def show_status() -> None:
    print("Career Advisor Project Status")
    print("=" * 40)

    for file in [
        "requirements.txt",
        "backend/requirements.txt",
        "backend/__init__.py",
        "backend/server.py",
        "backend/main.py",
        "backend/llm_providers.py",
        "backend/rag_pipeline.py",
        "backend/rag_service.py",
        "backend/config.py",
        "backend/career_tools.py",
        "backend/resume_pipeline.py",
        "backend/mcp_server.py",
        "backend/tracing.py",
        "backend/evaluation.py",
        "frontend/package.json",
    ]:
        print(f"[OK] {file}" if os.path.exists(file) else f"[X] {file}")

    if os.path.exists(".env"):
        print("[OK] .env")
        check_env()
    else:
        print("[X] .env (run: python app.py setup)")

    print("\nPackage status:")
    for pkg in [
        "fastapi",
        "uvicorn",
        "groq",
        "google-genai",
        "langchain",
        "chromadb",
        "python-dotenv",
        "langsmith",
        "mcp",
        "docx",
    ]:
        module = {"google-genai": "google.genai", "python-dotenv": "dotenv"}.get(
            pkg, pkg.replace("-", "_")
        )
        try:
            __import__(module)
            print(f"[OK] {pkg}")
        except ImportError:
            print(f"[X] {pkg}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Career Advisor project runner")
    parser.add_argument(
        "command",
        nargs="?",
        default="api",
        choices=["api", "cli", "mcp", "install", "setup", "status", "doctor"],
        help="Command to run (default: api - launches app on port 8000)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind server (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind server (default: 8000)")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload in development")
    args = parser.parse_args()

    if args.command == "doctor":
        from backend.doctor import main as doctor_main

        sys.exit(doctor_main())
    elif args.command == "install":
        install_requirements()
    elif args.command == "setup":
        create_sample_env()
    elif args.command == "status":
        show_status()
    elif args.command == "api":
        if not check_requirements() or not check_env():
            sys.exit(1)
        run_api(host=args.host, port=args.port, reload=not args.no_reload)
    elif args.command == "cli":
        if not check_requirements() or not check_env():
            sys.exit(1)
        run_cli()
    elif args.command == "mcp":
        if not check_requirements() or not check_env():
            sys.exit(1)
        run_mcp()


if __name__ == "__main__":
    main()
