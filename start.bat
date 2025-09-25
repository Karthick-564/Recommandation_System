@echo off
cd /d "%~dp0"

echo 🚀 Starting Volunteer Recommendation System
echo ==========================================

echo.
echo 🔍 Finding Python...
if exist "C:\Users\Hp\anaconda3\python.exe" (
    echo ✅ Found Anaconda Python
    set PYTHON_PATH="C:\Users\Hp\anaconda3\python.exe"
) else (
    echo ✅ Using system Python
    set PYTHON_PATH=python
)

echo.
echo 🌐 Starting web server on http://localhost:5000
echo 📍 Open your browser to: http://localhost:5000
echo 🛑 Press Ctrl+C to stop the server
echo.

%PYTHON_PATH% web_server.py

echo.
echo Server stopped. Press any key to exit.
pause