@echo off
cls

:: Define the path to the requirements file
set "REQUIREMENTS_PATH=requirements.txt"

:: Check if Python is installed
echo Checking for Python installation...
py --version >NUL 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed.
    echo Downloading Python 3...
    start "" "https://www.python.org/downloads/"
    echo Please install Python 3 and rerun this script.
    pause
    exit /b
)

:: Check if pip is available
echo Checking for pip installation...
pip --version >NUL 2>&1
if %errorlevel% neq 0 (
    echo Pip is not installed. Attempting to install pip...
    py -m ensurepip
    pip --version >NUL 2>&1
    if %errorlevel% neq 0 (
        echo Pip could not be installed. Please ensure pip is available and rerun the script.
        pause
        exit /b
    )
)

:: Install required Python packages
echo Checking and installing required Python packages...
if exist "%REQUIREMENTS_PATH%" (
    pip install -r "%REQUIREMENTS_PATH%"
) else (
    echo Requirements file not found at "%REQUIREMENTS_PATH%"
)

:: Define relative path to the Python script
set "SCRIPT_PATH=UI.py"

:: Run the Python script
if exist "%SCRIPT_PATH%" (
    echo Running the UI script...
    py "%SCRIPT_PATH%"
) else (
    echo Error: Script not found at "%SCRIPT_PATH%"
)

pause
