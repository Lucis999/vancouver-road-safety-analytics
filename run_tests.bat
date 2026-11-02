@echo off
cd /d "%~dp0"
python run_tests.py %*
set "QA_EXIT=%ERRORLEVEL%"
echo.
echo QA report: validation_results\validation_report.html
pause
exit /b %QA_EXIT%
