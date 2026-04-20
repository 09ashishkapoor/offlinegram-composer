@echo off
setlocal

cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
    echo Virtual environment not found. Run setup.bat first.
    exit /b 1
)

call venv\Scripts\activate
start "" http://127.0.0.1:8000
python -m uvicorn app:app --host 127.0.0.1 --port 8000
