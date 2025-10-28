@echo off
REM TOM v3.0 - Sync von G: (Cloud) nach E: (lokal)
REM Kopiert nur relevante Dateien, ignoriert .venv, node_modules, große Dateien

echo ===== SYNC: G: -^> E: =====
echo.
echo Quelle (Cloud):  G:\Meine Ablage\_____1111____Projekte-Programmierung\___TelefonAssistent_3.0
echo Ziel (Privat):   E:\_____1111____Projekte-Programmierung\___TelefonAssistent_3.0
echo.

SET SOURCE=G:\Meine Ablage\_____1111____Projekte-Programmierung\___TelefonAssistent_3.0
SET DEST=E:\_____1111____Projekte-Programmierung\___TelefonAssistent_3.0

REM Prüfe ob Quelle existiert
if not exist "%SOURCE%" (
    echo FEHLER: Quelle existiert nicht: %SOURCE%
    pause
    exit /b 1
)

REM Prüfe ob Ziel existiert
if not exist "%DEST%" (
    echo FEHLER: Ziel existiert nicht: %DEST%
    pause
    exit /b 1
)

echo Starte Robocopy...
echo.

REM Robocopy mit Excludes
robocopy "%SOURCE%" "%DEST%" /E ^
    /XD .venv node_modules __pycache__ .pytest_cache ^
          data\audio data\models\whisperx logs zip MagicMock ^
    /XF *.pyc *.pyo *.log *.zip *.7z ^
    /XD apps\__pycache__ apps\realtime\__pycache__ ^
    /R:3 /W:5 /MT:4 ^
    /NFL /NDL /NP

REM Robocopy Exit Codes
SET EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE% GTR 7 (
    echo FEHLER: Robocopy ist fehlgeschlagen (Exit Code: %EXIT_CODE%)
    pause
    exit /b 1
)

echo.
echo ===== SYNC ABGESCHLOSSEN =====
echo.
echo Alle Aenderungen wurden von G: nach E: kopiert.
echo.
pause

