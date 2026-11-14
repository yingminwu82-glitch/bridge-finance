"""
Vercel Serverless Function entry point.
Wraps the FastAPI app for Vercel's Python runtime.

This file lives in frontend/api/index.py so that Vercel's Next.js project
(with Root Directory = frontend/) can also serve Python serverless functions.
The backend source is at ../../backend relative to this file.
"""
import sys
import os

# Add backend directory to Python path
# From frontend/api/ -> ../../backend
backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

# Set Vercel environment flag
os.environ["VERCEL"] = "1"
os.environ["GBA_DB_PATH"] = "sqlite:///:memory:"
os.environ["UPLOAD_DIR"] = "/tmp/uploads"

# Import the FastAPI app
from app.main import app  # noqa: E402

# Vercel Python runtime expects an ASGI app named `app`
