@echo off
cd /d "%~dp0"
echo ==========================================
echo   LightFM Volunteer Matching System
echo   Full Flask Application with AI Training
echo ==========================================
echo.

:: Try to find Python
set "PYTHON_CMD="
for %%i in (python python3 py) do (
    %%i --version >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_CMD=%%i"
        goto :found_python
    )
)

:found_python
if "%PYTHON_CMD%"=="" (
    echo ERROR: Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

echo Using Python: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

:: Check if required packages are installed
echo Checking dependencies...
%PYTHON_CMD% -c "import flask, lightfm, pandas, numpy" 2>nul
if %errorlevel% neq 0 (
    echo Installing required packages...
    %PYTHON_CMD% -m pip install flask lightfm pandas numpy scikit-learn
    echo.
)

:: Start the full application
echo Starting LightFM Volunteer Matching System...
echo.
echo IMPORTANT: 
echo - First launch will train the LightFM model (may take 30-60 seconds)
echo - Server will be available at: http://localhost:5000
echo - Use Ctrl+C to stop the server
echo.
echo Please wait for model training to complete...
echo ==========================================
echo.

%PYTHON_CMD% full_app.py

if %errorlevel% neq 0 (
    echo.
    echo ==========================================
    echo ERROR: Failed to start the application.
    echo Possible solutions:
    echo 1. Check if port 5000 is already in use
    echo 2. Verify all dependencies are installed
    echo 3. Try running: python -m pip install --upgrade flask lightfm pandas numpy
    echo ==========================================
    echo.
    pause
)