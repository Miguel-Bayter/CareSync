"""Vercel entry point — re-exports the FastAPI app as the ASGI handler."""

import os
import sys

# Guarantee that medication-management-api/ is on the path regardless of
# what directory Vercel sets as the working directory at invocation time.
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from app.main import app
except Exception:
    import traceback

    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI()
    _startup_error = traceback.format_exc()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def _error(path: str = "") -> JSONResponse:
        return JSONResponse({"startup_error": _startup_error}, status_code=500)
