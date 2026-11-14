"""
Vercel Serverless Function entry point.
Wraps the FastAPI app for Vercel's Python runtime.

This file lives in frontend/api/index.py. The backend source is at
../backend (frontend/backend/app/) relative to this file.
"""
import sys
import os
import traceback

# Add backend directory to Python path
# From frontend/api/ -> ../backend
backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, backend_dir)

# Set Vercel environment flag
os.environ["VERCEL"] = "1"
os.environ["GBA_DB_PATH"] = "sqlite:///:memory:"
os.environ["UPLOAD_DIR"] = "/tmp/uploads"

# Import the FastAPI app — initialize eagerly so errors surface at cold start
try:
    from app.models import init_db, get_session_maker
    from app.seed import seed_database
    from app.main import app, get_db
except Exception as e:
    # Fallback: create a minimal FastAPI app that returns the error
    from fastapi import FastAPI
    app = FastAPI()

    @app.get("/api/{path:path}")
    async def error_handler(path: str):
        return {"error": f"Import failed: {e}", "traceback": traceback.format_exc()}

    @app.get("/api/health")
    async def health():
        return {"status": "error", "detail": str(e)}
