@echo off
setlocal

SET PROJ=C:\Users\virat.arya\ETG\SoftsDatabase - Documents\Database\Hardmine\ICEBREAKER\Spec Proximity
SET LOG=%PROJ%\Automator\refresh.log

echo. >> "%LOG%"
echo ============================================ >> "%LOG%"
echo %DATE% %TIME% — Spec Proximity Refresh >> "%LOG%"
echo ============================================ >> "%LOG%"

:: ── 1. Ingest ─────────────────────────────────────────────────────────────
echo [1/3] Running ingest...
python "%PROJ%\Code\ingest.py" >> "%LOG%" 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Ingest failed. See log. >> "%LOG%"
    goto :send_email
)
echo [1/3] Ingest OK >> "%LOG%"

:: ── 2. Git commit + push ──────────────────────────────────────────────────
echo [2/3] Pushing to GitHub...
cd /d "%PROJ%"
git add Database\*.parquet >> "%LOG%" 2>&1
git diff --cached --quiet
IF %ERRORLEVEL% EQU 0 (
    echo [2/3] No parquet changes — skipping commit >> "%LOG%"
) ELSE (
    git commit -m "Data refresh %DATE% %TIME%" >> "%LOG%" 2>&1
    git push >> "%LOG%" 2>&1
    IF %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Git push failed. >> "%LOG%"
    ) ELSE (
        echo [2/3] Push OK >> "%LOG%"
    )
)

:: ── 3. Email ──────────────────────────────────────────────────────────────
:send_email
echo [3/3] Sending email...
powershell -ExecutionPolicy Bypass -File "%PROJ%\Automator\send_email.ps1" >> "%LOG%" 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Email failed. >> "%LOG%"
) ELSE (
    echo [3/3] Email OK >> "%LOG%"
)

echo Done. >> "%LOG%"
endlocal
