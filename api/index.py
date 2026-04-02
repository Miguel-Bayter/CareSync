"""Vercel entry point — exposes the FastAPI app as the ASGI handler."""

import os
import sys

# Guarantee that the project root (medication-management-api/) is on sys.path.
# Vercel invokes functions from the repo root, so without this the relative
# `app.*` package would not be found at runtime.
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from app.main import app

__all__ = ["app"]
