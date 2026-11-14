"""
Vercel Serverless Function entry point for the backend API.
Wraps the FastAPI app for Vercel's Python runtime.

This file lives at backend/api/index.py. The app source is at ../app/
relative to this file.
"""
import sys
import os

# Add app source directory to Python path
app_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, app_dir)

# Set Vercel environment flag — forces in-memory SQLite
os.environ["VERCEL"] = "1"
os.environ["GBA_DB_PATH"] = "sqlite:///:memory:"
os.environ["UPLOAD_DIR"] = "/tmp/uploads"

# Import the FastAPI app
from app.main import app  # noqa: E402

# Vercel Python runtime expects an ASGI app named `app`
