"""
Vercel Serverless Function entry point for the backend API.
Wraps the FastAPI app for Vercel's Python runtime.

This file lives at backend/api/index.py. The app source is at ../app/
relative to this file.
"""
import sys
import os
import traceback

# Add app source directory to Python path
app_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, app_dir)

# Set Vercel environment flag — forces in-memory SQLite
os.environ["VERCEL"] = "1"
os.environ["GBA_DB_PATH"] = "sqlite:///:memory:"
os.environ["UPLOAD_DIR"] = "/tmp/uploads"

# Import the FastAPI app
from app.main import app  # noqa: E402

# Diagnostic endpoint to capture seed errors at runtime
from fastapi import FastAPI
from starlette.routing import Route

@app.get("/api/debug")
async def debug_info():
    import platform
    info = {"python": platform.python_version(), "vercel": os.environ.get("VERCEL")}
    # Test DB init
    try:
        from app.models import init_db, get_session_maker, Enterprise
        from app.seed import seed_database
        engine = init_db("sqlite:///:memory:")
        SL = get_session_maker(engine)
        with SL() as s:
            seed_database(s)
            s.commit()
            info["enterprises"] = s.query(Enterprise).count()
            info["db_status"] = "OK"
    except Exception as e:
        info["db_error"] = str(e)
        info["db_traceback"] = traceback.format_exc()
    return info

# Vercel Python runtime expects an ASGI app named `app`
