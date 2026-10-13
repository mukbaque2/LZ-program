"""Double-click launcher for the lz desktop app.

A .pyw file is run by pythonw.exe on Windows, so no console window appears.
Keep this at the project root: it adds the project directory to sys.path so
the app runs from a checkout without being installed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lz.gui import main

raise SystemExit(main())
