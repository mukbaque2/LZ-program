@echo off
rem Launch the lz desktop app. Uses pythonw so no console window lingers.
cd /d "%~dp0"
start "" pythonw "%~dp0lz-gui.pyw"
