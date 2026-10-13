# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for the lz desktop app.

Build with:
    pyinstaller lz.spec --noconfirm

Produces a single dist/lz.exe with no console window.

Notes on the choices here
-------------------------
datas: data/zippers.json must be bundled, and `lz.library._data_dir`
    resolves it through sys._MEIPASS at run time. Without both halves the
    exe starts fine and then fails the moment you press "Screen known
    zippers".

excludes: numpy is imported only inside `lz.cli.cmd_calibrate`, which the
    GUI never reaches, and it is by far the largest dependency. Excluding it
    roughly halves the executable. `lz calibrate` still works from a source
    checkout; it is not part of the GUI build.
"""

import sys
from pathlib import Path

project = Path(SPECPATH)

a = Analysis(
    [str(project / "lz-gui.pyw")],
    pathex=[str(project)],
    binaries=[],
    datas=[
        (str(project / "data"), "data"),
        (str(project / "lz.ico"), "."),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Not reachable from the GUI; see the module docstring.
        "numpy",
        "pytest",
        # Tk is used, but these optional Tk extras are not.
        "tkinter.test",
        "test",
        # Common PyInstaller over-collection.
        "matplotlib",
        "PIL",
        "setuptools",
        "pip",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="lz",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,          # windowed: no console flashes up behind the GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project / "lz.ico") if (project / "lz.ico").exists() else None,
)
