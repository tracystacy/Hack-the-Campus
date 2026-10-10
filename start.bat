@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Creating Python environment...
  py -m venv .venv
  if errorlevel 1 goto error
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto error
python app.py
pause
goto end
:error
echo.
echo Setup failed. Check that Python is installed and try again.
pause
:end
