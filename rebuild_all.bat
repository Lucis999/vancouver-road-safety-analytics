@echo off
setlocal
cd /d "%~dp0"
echo WARNING: This rebuild can overwrite processed data and quality outputs.
echo Back up data_source\processed before continuing.
choice /M "Continue full rebuild"
if errorlevel 2 exit /b 1
python 01_add_coordinates.py || goto :failed
python 02_add_block_info.py || goto :failed
python 03_audit_and_clean.py || goto :failed
python 05_collision_extension.py || goto :failed
python 06_review_collision_matches.py || goto :failed
python 04_vancouver_road_safety_dashboard_v12_4.py || goto :failed
echo Rebuild complete. Review QA outputs before copying HTML to site\index.html.
pause
exit /b 0
:failed
echo Pipeline failed. Review console output and input data.
pause
exit /b 1
