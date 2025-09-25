@echo off
echo 🚀 Setting up Volunteer Recommendation System
echo ================================

echo.
echo � Finding Python installation...
where python >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Python not found in PATH, trying conda...
    where conda >nul 2>&1
    if errorlevel 1 (
        echo ❌ Neither python nor conda found. Please install Python or Anaconda.
        echo 💡 Visit: https://www.anaconda.com/products/distribution
        pause
        exit /b 1
    ) else (
        echo ✅ Using conda environment
        set PYTHON_CMD=conda run python
    )
) else (
    echo ✅ Python found in PATH
    set PYTHON_CMD=python
)

echo.
echo �📦 Installing required packages...
%PYTHON_CMD% -m pip install flask pandas numpy lightfm scikit-learn

echo.
echo 📊 Checking data files...
if exist students.csv (
    echo ✅ students.csv found
) else (
    echo ❌ students.csv missing
)

if exist opportunities.csv (
    echo ✅ opportunities.csv found  
) else (
    echo ❌ opportunities.csv missing
)

if exist interactions.csv (
    echo ✅ interactions.csv found
) else (
    echo ❌ interactions.csv missing
)

echo.
echo 🧪 Testing Flask installation...
%PYTHON_CMD% test_flask.py
if errorlevel 1 (
    echo ❌ Flask test failed. Trying to install Flask again...
    %PYTHON_CMD% -m pip install --upgrade flask
)

echo.
echo 🌐 Starting Flask application...
echo ================================
echo 📍 Access your website at: http://localhost:5000
echo 🛑 Press Ctrl+C to stop the server
echo ================================
echo.

%PYTHON_CMD% simple_app.py

echo.
echo 🔄 Server stopped. Press any key to exit...
pause