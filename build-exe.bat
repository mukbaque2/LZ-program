@echo off
rem Build dist\lz.exe and verify it before claiming success.
rem
rem The verification step matters: a windowed exe with a missing data file
rem starts perfectly and only fails when the user clicks something. The
rem self-test exercises those paths headlessly and writes a report.

cd /d "%~dp0"

echo [1/3] regenerating icon...
python tools\make_icon.py || goto :failed

echo.
echo [2/3] building...
python -m PyInstaller lz.spec --noconfirm --clean || goto :failed

echo.
echo [3/3] verifying the build...
if exist "%TEMP%\lz-selftest.txt" del "%TEMP%\lz-selftest.txt"
dist\lz.exe --selftest "%TEMP%\lz-selftest.txt"
if errorlevel 1 goto :selftest_failed

type "%TEMP%\lz-selftest.txt"
echo.
echo Build OK: dist\lz.exe
goto :eof

:selftest_failed
echo.
echo BUILD IS BROKEN - self-test failed:
type "%TEMP%\lz-selftest.txt"
exit /b 1

:failed
echo.
echo Build failed.
exit /b 1
