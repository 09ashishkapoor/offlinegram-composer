@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

set "PYTHON_CMD="
py -3.11 -c "import sys" >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py -3.11"
    echo Using Python 3.11 for best skia-python compatibility.
) else (
    py -3 -c "import sys" >nul 2>nul
    if %errorlevel%==0 (
        set "PYTHON_CMD=py -3"
        echo Python 3.11 was not found. Falling back to the default Python 3 interpreter.
    ) else (
        python -c "import sys" >nul 2>nul
        if %errorlevel%==0 (
            set "PYTHON_CMD=python"
            echo Using python from PATH.
        ) else (
            echo Python 3.9+ is required but was not found.
            exit /b 1
        )
    )
)

for /f "delims=" %%v in ('%PYTHON_CMD% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set "PY_VER=%%v"
echo Detected Python version: %PY_VER%

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"
if errorlevel 1 (
    echo Python 3.9 or newer is required.
    exit /b 1
)

echo.
echo Visual C++ Redistributable may be required for skia-python wheels:
echo https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist
echo.

if exist venv (
    echo Removing existing venv...
    rmdir /s /q venv
)

echo Creating virtual environment...
%PYTHON_CMD% -m venv venv
if errorlevel 1 exit /b 1

call venv\Scripts\activate
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1

echo Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo.
echo Setup complete. Run launch.bat to start the app.
exit /b 0
