@echo off
cd /d "%~dp0"

echo 🚀 Quick Flask App Launcher
echo ==========================

echo.
echo 📦 Installing Flask (this may take a moment)...
pip install flask --quiet
if errorlevel 1 (
    echo ❌ Failed to install Flask using pip
    echo 💡 Try running as Administrator or check your Python installation
    pause
    exit /b 1
)

echo ✅ Flask installed successfully!

echo.
echo 🌐 Starting server on http://localhost:5000
echo 📍 Opening browser automatically...
echo 🛑 Press Ctrl+C in this window to stop the server

echo.

REM Start Flask app
python test_flask.py

echo.
echo Server stopped.
pause