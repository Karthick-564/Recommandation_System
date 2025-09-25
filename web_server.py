#!/usr/bin/env python3
"""
Ultra-Simple Web Server
No Flask needed - uses Python's built-in HTTP server
"""

import http.server
import socketserver
import webbrowser
import os
import json
from urllib.parse import parse_qs
import pandas as pd

# Load sample data
try:
    students_df = pd.read_csv('students.csv')
    opportunities_df = pd.read_csv('opportunities.csv')
    print("✅ Data loaded successfully!")
    DATA_LOADED = True
except:
    print("⚠️  Data files not found, using sample data")
    DATA_LOADED = False

# Sample recommendations
SAMPLE_RECOMMENDATIONS = {
    "0": [
        {"ngo_name": "TechForGood Initiative", "description": "Develop Python applications for local nonprofits", "required_skills": "Python, C++", "match_score": 95},
        {"ngo_name": "CodeCommunity", "description": "Teaching programming to underserved youth", "required_skills": "Python, Teaching", "match_score": 87},
        {"ngo_name": "Digital Education Foundation", "description": "Build educational software for schools", "required_skills": "C++, Software Development", "match_score": 82}
    ],
    "1": [
        {"ngo_name": "Youth Mentorship Program", "description": "Mentor high school students", "required_skills": "Public Speaking, Teaching", "match_score": 98},
        {"ngo_name": "Community Education Center", "description": "Teach adult literacy classes", "required_skills": "Teaching, Communication", "match_score": 92},
        {"ngo_name": "School Support Network", "description": "Assist teachers with activities", "required_skills": "Teaching, Organization", "match_score": 85}
    ]
}

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = """
<!DOCTYPE html>
<html>
<head>
    <title>🤝 Volunteer Match</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .login-section { margin: 20px 0; padding: 20px; border: 2px solid #ddd; border-radius: 8px; }
        .student { border-color: #3b82f6; }
        .ngo { border-color: #10b981; }
        input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
        button { width: 100%; padding: 12px; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }
        .student-btn { background: #3b82f6; color: white; }
        .ngo-btn { background: #10b981; color: white; }
        button:hover { opacity: 0.9; }
        .recommendations { margin-top: 20px; }
        .rec-card { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #3b82f6; }
        .match-score { float: right; background: #10b981; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤝 Volunteer Recommendation System</h1>
            <p>Connect students with volunteer opportunities</p>
        </div>
        
        <div class="login-section student">
            <h2>👨‍🎓 Student Login</h2>
            <input type="text" id="student-id" placeholder="Enter Student ID (0-99)" />
            <button class="student-btn" onclick="showRecommendations()">Get My Recommendations</button>
        </div>
        
        <div class="login-section ngo">
            <h2>🏢 NGO Portal</h2>
            <input type="text" id="ngo-name" placeholder="Enter NGO Name" />
            <button class="ngo-btn" onclick="showNgoInfo()">Login as NGO</button>
        </div>
        
        <div id="results"></div>
    </div>

    <script>
        const recommendations = """ + json.dumps(SAMPLE_RECOMMENDATIONS) + """;
        
        function showRecommendations() {
            const studentId = document.getElementById('student-id').value;
            const recs = recommendations[studentId] || recommendations['0'];
            
            let html = '<div class="recommendations"><h3>🎯 Your Top Recommendations:</h3>';
            
            recs.forEach((rec, index) => {
                html += `
                    <div class="rec-card">
                        <div class="match-score">${rec.match_score}% Match</div>
                        <h4>${index + 1}. ${rec.ngo_name}</h4>
                        <p>${rec.description}</p>
                        <small><strong>Skills:</strong> ${rec.required_skills}</small>
                    </div>
                `;
            });
            
            html += '</div>';
            document.getElementById('results').innerHTML = html;
        }
        
        function showNgoInfo() {
            const ngoName = document.getElementById('ngo-name').value;
            document.getElementById('results').innerHTML = `
                <div class="recommendations">
                    <h3>🏢 Welcome, ${ngoName}!</h3>
                    <p>✅ NGO Portal functionality coming soon!</p>
                    <p>📝 You can post volunteer opportunities and find matching students.</p>
                </div>
            `;
        }
    </script>
</body>
</html>
            """
            
            self.wfile.write(html.encode())
        else:
            super().do_GET()

def start_server():
    PORT = 5000
    Handler = MyHTTPRequestHandler
    
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print("🚀 Starting web server...")
            print(f"🌐 Server running at http://localhost:{PORT}")
            print("📍 Opening browser automatically...")
            print("🛑 Press Ctrl+C to stop the server")
            print()
            
            # Try to open browser
            try:
                webbrowser.open(f'http://localhost:{PORT}')
            except:
                pass
                
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n✅ Server stopped successfully!")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        print("💡 Port 5000 might be in use. Try closing other applications.")

if __name__ == "__main__":
    start_server()