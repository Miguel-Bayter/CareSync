"""Vercel entry point — re-exports the FastAPI app as the ASGI handler."""

from app.main import app  # noqa: F401  (Vercel expects a module-level `app`)
