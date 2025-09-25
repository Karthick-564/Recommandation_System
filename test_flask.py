#!/usr/bin/env python3
"""
Test Flask App - Minimal version to check if Flask works
"""

print("🔍 Testing Flask setup...")

# Test 1: Check if Flask is installed
try:
    import flask
    print("✅ Flask imported successfully!")
    print(f"   Flask version: {flask.__version__}")
except ImportError as e:
    print(f"❌ Flask import failed: {e}")
    print("💡 Install with: pip install flask")
    exit(1)

# Test 2: Check if other packages are available
packages = ['pandas', 'numpy', 'os', 'secrets']
for pkg in packages:
    try:
        __import__(pkg)
        print(f"✅ {pkg} imported successfully!")
    except ImportError:
        print(f"❌ {pkg} import failed")

# Test 3: Check if data files exist
import os
data_files = ['students.csv', 'opportunities.csv', 'interactions.csv']
for file in data_files:
    if os.path.exists(file):
        print(f"✅ {file} found")
    else:
        print(f"❌ {file} missing")

# Test 4: Try to create a minimal Flask app
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return '''
    <html>
    <head><title>🎉 Flask Works!</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>🎉 Volunteer Recommendation System</h1>
        <h2 style="color: green;">✅ Flask is working!</h2>
        <p>Your server is running successfully on port 5000</p>
        <p><a href="/test">Click here to test another page</a></p>
    </body>
    </html>
    '''

@app.route('/test')
def test():
    return '''
    <html>
    <head><title>Test Page</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>🧪 Test Page</h1>
        <p style="color: green;">✅ Routing is working!</p>
        <p><a href="/">Back to home</a></p>
    </body>
    </html>
    '''

if __name__ == '__main__':
    print("\n🚀 Starting test Flask server...")
    print("🌐 Open your browser to: http://localhost:5000")
    print("⏹️  Press Ctrl+C to stop the server")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"❌ Error starting Flask server: {e}")
        input("Press Enter to continue...")