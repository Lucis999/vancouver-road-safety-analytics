@echo off
setlocal
cd /d "%~dp0"
python 04_vancouver_road_safety_dashboard_v12_4.py
if errorlevel 1 goto :failed
if not exist "data_source\output\04_map_results\vancouver_road_safety_dashboard_v12_4.html" goto :failed
start "" "%~dp0data_source\output\04_map_results\vancouver_road_safety_dashboard_v12_4.html"
echo Dashboard v12.4 generated and opened.
pause
exit /b 0
:failed
echo Dashboard generation failed. Check input CSVs and Python dependencies.
pause
exit /b 1
