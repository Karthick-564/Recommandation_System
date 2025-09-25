#!/usr/bin/env python3
"""
Simple Flask App for Volunteer Recommendations
No complex ML training - loads instantly!
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import pandas as pd
import numpy as np
import secrets
import os

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Global data storage
app_data = {
    'students_df': None,
    'opportunities_df': None,
    'interactions_df': None,
    'loaded': False
}

def load_data():
    """Load CSV data quickly without ML training"""
    try:
        print("📊 Loading CSV data...")
        
        # Check if files exist
        required_files = ['students.csv', 'opportunities.csv', 'interactions.csv']
        for file in required_files:
            if not os.path.exists(file):
                print(f"❌ Missing file: {file}")
                return False
        
        # Load data
        app_data['students_df'] = pd.read_csv('students.csv')
        app_data['opportunities_df'] = pd.read_csv('opportunities.csv')
        app_data['interactions_df'] = pd.read_csv('interactions.csv')
        
        # Convert IDs to strings
        app_data['students_df']['student_id'] = app_data['students_df']['student_id'].astype(str)
        app_data['opportunities_df']['opportunity_id'] = app_data['opportunities_df']['opportunity_id'].astype(str)
        
        app_data['loaded'] = True
        print("✅ Data loaded successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return False

def calculate_match_score(student, opportunity):
    """Calculate simple matching score"""
    score = 0
    
    # Skill matching (most important)
    if pd.notna(student['skills']) and pd.notna(opportunity['required_skills']):
        student_skills = set(s.strip().lower() for s in str(student['skills']).split(','))
        required_skills = set(s.strip().lower() for s in str(opportunity['required_skills']).split(','))
        skill_matches = len(student_skills.intersection(required_skills))
        score += skill_matches * 15  # 15 points per skill match
    
    # Interest matching
    if pd.notna(student['interests']) and pd.notna(opportunity['description']):
        interests = str(student['interests']).lower()
        description = str(opportunity['description']).lower()
        
        # Check if any interest keyword appears in description
        interest_keywords = [i.strip() for i in interests.split(',')]
        for keyword in interest_keywords:
            if keyword in description:
                score += 8
    
    # Availability matching
    if pd.notna(student['work_calendar']) and pd.notna(opportunity['work_calendar']):
        student_days = set(d.strip().lower()[:3] for d in str(student['work_calendar']).split(','))
        opp_days = set(d.strip().lower()[:3] for d in str(opportunity['work_calendar']).split(','))
        day_matches = len(student_days.intersection(opp_days))
        score += day_matches * 3  # 3 points per matching day
    
    # Willingness factor
    willingness_scores = {'high': 5, 'medium': 3, 'low': 1}
    score += willingness_scores.get(str(student.get('willingness', '')).lower(), 0)
    
    # Importance boost
    importance_scores = {'emergency': 7, 'high': 5, 'standard': 2}
    score += importance_scores.get(str(opportunity.get('importance_level', '')).lower(), 0)
    
    return max(0, score)  # Ensure non-negative score

def get_recommendations(student_id, n_recs=5):
    """Get recommendations for a student"""
    if not app_data['loaded']:
        return []
    
    # Find student
    student_rows = app_data['students_df'][app_data['students_df']['student_id'] == student_id]
    if student_rows.empty:
        return []
    
    student = student_rows.iloc[0]
    
    # Calculate scores for all opportunities
    recommendations = []
    for _, opp in app_data['opportunities_df'].iterrows():
        score = calculate_match_score(student, opp)
        
        recommendations.append({
            'opportunity_id': str(opp['opportunity_id']),
            'ngo_name': str(opp['ngo_name']),
            'description': str(opp['description']),
            'required_skills': str(opp['required_skills']),
            'importance_level': str(opp['importance_level']),
            'work_calendar': str(opp['work_calendar']),
            'score': score,
            'match_percentage': min(100, max(10, int(score * 2)))  # Convert to percentage
        })
    
    # Sort by score and return top N
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    return recommendations[:n_recs]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    """Handle login"""
    data = request.get_json()
    user_type = data.get('user_type')
    user_id = data.get('user_id')
    
    if user_type == 'student':
        # Validate student ID
        if app_data['loaded']:
            student_exists = not app_data['students_df'][app_data['students_df']['student_id'] == user_id].empty
            if student_exists:
                session['user_type'] = 'student'
                session['user_id'] = user_id
                return jsonify({'success': True, 'redirect': '/student_dashboard'})
            else:
                return jsonify({'success': False, 'error': f'Student ID {user_id} not found. Try IDs 0-99.'})
        else:
            return jsonify({'success': False, 'error': 'System loading failed. Check console.'})
    
    elif user_type == 'ngo':
        session['user_type'] = 'ngo'
        session['user_id'] = user_id
        return jsonify({'success': True, 'redirect': '/ngo_dashboard'})
    
    return jsonify({'success': False, 'error': 'Invalid request'})

@app.route('/student_dashboard')
def student_dashboard():
    if session.get('user_type') != 'student':
        return redirect(url_for('index'))
    return render_template('student_dashboard.html')

@app.route('/ngo_dashboard')
def ngo_dashboard():
    if session.get('user_type') != 'ngo':
        return redirect(url_for('index'))
    return render_template('ngo_dashboard.html')

@app.route('/get_recommendations')
def get_recommendations_api():
    if session.get('user_type') != 'student':
        return jsonify({'error': 'Not logged in as student'})
    
    student_id = session.get('user_id')
    recommendations = get_recommendations(student_id, 5)
    
    # Get student profile
    student_profile = None
    if app_data['loaded']:
        student_rows = app_data['students_df'][app_data['students_df']['student_id'] == student_id]
        if not student_rows.empty:
            student_profile = student_rows.iloc[0].to_dict()
    
    return jsonify({
        'recommendations': recommendations,
        'profile': student_profile,
        'student_id': student_id
    })

@app.route('/add_opportunity', methods=['POST'])
def add_opportunity():
    if session.get('user_type') != 'ngo':
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    # For demo purposes, just return success
    return jsonify({'success': True, 'message': 'Opportunity posted successfully! (Demo mode)'})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'running',
        'data_loaded': app_data['loaded'],
        'students': len(app_data['students_df']) if app_data['loaded'] else 0,
        'opportunities': len(app_data['opportunities_df']) if app_data['loaded'] else 0
    })

if __name__ == '__main__':
    print("🚀 Starting Simple Flask App...")
    print("=" * 50)
    
    # Load data (fast, no ML training)
    success = load_data()
    
    if success:
        print("✅ App ready!")
        print("🌐 Access at: http://localhost:5000")
        print("👥 Test with Student IDs: 0, 1, 2, 3, 4, etc.")
        print("🏢 NGO login: Use any name")
    else:
        print("⚠️  Data loading failed, but app will still run")
        print("🌐 Access at: http://localhost:5000")
    
    print("=" * 50)
    
    # Start Flask app
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)