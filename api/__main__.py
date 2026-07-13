"""
python -m api

Console entry point for the Chemistry Companion web application.

Launches Uvicorn with the FastAPI app defined in ``api.app:app``.
Host/port are overridable via environment variables:

    CHEM_COMPANION_HOST  (default: 127.0.0.1)
    CHEM_COMPANION_PORT  (default: 8000)
"""

from __future__ import annotations

import os


def main() -> None:
    """Start the Chemistry Companion ASGI server."""
    import uvicorn

    host = os.environ.get("CHEM_COMPANION_HOST", "127.0.0.1")
    port = int(os.environ.get("CHEM_COMPANION_PORT", "8000"))
    uvicorn.run(
        "api.app:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
