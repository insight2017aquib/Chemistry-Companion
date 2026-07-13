"""
Thin launcher for the Chemistry Companion web application.

Prefer one of:

    chemistry-companion-server          # console script after install
    python -m api
    python run.py

Host/port: CHEM_COMPANION_HOST / CHEM_COMPANION_PORT (see api.__main__).
"""

from api.__main__ import main

if __name__ == "__main__":
    main()
