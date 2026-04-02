"""Vercel entry point — exposes the FastAPI app as the ASGI handler."""

import os
import sys

# Ensure medication-management-api/ is on sys.path so `app.*` imports resolve
# correctly regardless of what working directory Vercel sets at invocation time.
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from app.main import app  # noqa: E402, F401
