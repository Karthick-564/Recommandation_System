#!/usr/bin/env python3
"""
Complete Student Volunteer and NGO Matching Platform
A self-contained Flask web application with hybrid recommendation system
"""

import os
import sys
import pandas as pd
import numpy as np
from flask import Flask, render_template_string, request, jsonify, session
import logging
from datetime import datetime
import secrets

# Handle optional imports gracefully
try:
    from lightfm import LightFM
    from lightfm.data import Dataset
    from scipy.sparse import csr_matrix
    LIGHTFM_AVAILABLE = True
except ImportError:
    print("Warning: LightFM not available. Using fallback recommendation system.")
    LIGHTFM_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

class VolunteerMatchingSystem:
    def __init__(self):
        self.students_df = None
        self.opportunities_df = None
        self.interactions_df = None
        self.model = None
        self.dataset = None
        self.user_id_map = {}
        self.item_id_map = {}
        self.reverse_user_map = {}
        self.reverse_item_map = {}
        self.is_trained = False
        self.new_users = {}  # Store new registered users
        self.next_user_id = 1000  # Start new user IDs from 1000
        self.next_opportunity_id = 1000  # Start new opportunity IDs from 1000
        
    def load_data(self):
        """Load CSV data into DataFrames"""
        try:
            # Load students data
            if os.path.exists('students.csv'):
                self.students_df = pd.read_csv('students.csv')
                logger.info(f"Loaded {len(self.students_df)} students")
            else:
                # Create sample students data if file doesn't exist
                self.students_df = pd.DataFrame({
                    'student_id': range(10),
                    'name': [f'Student_{i}' for i in range(10)],
                    'email': [f'student{i}@example.com' for i in range(10)],
                    'skills': [f'skill_{i%3}' for i in range(10)],
                    'interests': [f'interest_{i%3}' for i in range(10)],
                    'university': [f'University_{i%3}' for i in range(10)]
                })
                
            # Load opportunities data
            if os.path.exists('opportunities.csv'):
                self.opportunities_df = pd.read_csv('opportunities.csv')
                logger.info(f"Loaded {len(self.opportunities_df)} opportunities")
            else:
                # Create sample opportunities data
                self.opportunities_df = pd.DataFrame({
                    'opportunity_id': range(20),
                    'ngo_name': [f'NGO_{i%5}' for i in range(20)],
                    'description': [f'Help with community project {i}' for i in range(20)],
                    'required_skills': [f'skill_{i%3}' for i in range(20)],
                    'importance_level': [['high', 'medium', 'low'][i%3] for i in range(20)],
                    'work_calendar': [f'{i%7+1} days/week' for i in range(20)]
                })
                
            # Load interactions data
            if os.path.exists('interactions.csv'):
                self.interactions_df = pd.read_csv('interactions.csv')
                logger.info(f"Loaded {len(self.interactions_df)} interactions")
            else:
                # Create sample interactions
                interactions_data = []
                for i in range(50):
                    interactions_data.append({
                        'student_id': i % 10,
                        'opportunity_id': i % 20,
                        'rating': np.random.choice([3, 4, 5], p=[0.2, 0.3, 0.5])
                    })
                self.interactions_df = pd.DataFrame(interactions_data)
                
            return True
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return False
            
    def build_lightfm_dataset(self):
        """Build LightFM dataset and train model"""
        if not LIGHTFM_AVAILABLE:
            logger.warning("LightFM not available, using fallback system")
            return False
            
        try:
            # Create dataset
            self.dataset = Dataset()
            
            # Get unique users and items
            users = list(self.students_df['student_id'].unique())
            items = list(self.opportunities_df['opportunity_id'].unique())
            
            # Fit the dataset
            self.dataset.fit(users=users, items=items)
            
            # Build mappings
            self.user_id_map, self.reverse_user_map = self.dataset.mapping()[0], self.dataset.mapping()[1]
            self.item_id_map, self.reverse_item_map = self.dataset.mapping()[2], self.dataset.mapping()[3]
            
            # Build interactions matrix
            interactions = []
            for _, row in self.interactions_df.iterrows():
                user_id = row['student_id']
                item_id = row['opportunity_id']
                rating = row['rating']
                if user_id in users and item_id in items:
                    interactions.append((user_id, item_id, rating))
                    
            # Build sparse matrix
            interaction_matrix, _ = self.dataset.build_interactions(interactions)
            
            # Train LightFM model
            self.model = LightFM(loss='warp', random_state=42)
            self.model.fit(interaction_matrix, epochs=30)
            
            self.is_trained = True
            logger.info("LightFM model trained successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error building LightFM dataset: {e}")
            return False
            
    def get_recommendations(self, student_id, n_recommendations=5):
        """Get recommendations for a student"""
        try:
            # Check if it's a new user
            if student_id in self.new_users:
                return self._get_content_based_recommendations(student_id, n_recommendations)
                
            # Check if student exists in original data
            if student_id not in self.students_df['student_id'].values:
                return []
                
            # Use LightFM if available and trained
            if LIGHTFM_AVAILABLE and self.is_trained and student_id in self.user_id_map:
                return self._get_lightfm_recommendations(student_id, n_recommendations)
            else:
                return self._get_fallback_recommendations(student_id, n_recommendations)
                
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return []
            
    def _get_lightfm_recommendations(self, student_id, n_recommendations):
        """Get recommendations using LightFM model"""
        try:
            user_internal_id = self.user_id_map[student_id]
            n_items = len(self.item_id_map)
            
            # Get predictions for all items
            item_ids = list(range(n_items))
            scores = self.model.predict(user_internal_id, item_ids)
            
            # Get top recommendations
            top_items = np.argsort(-scores)[:n_recommendations]
            
            recommendations = []
            for item_idx in top_items:
                item_id = self.reverse_item_map[item_idx]
                score = float(scores[item_idx])
                
                # Get opportunity details
                opp = self.opportunities_df[self.opportunities_df['opportunity_id'] == item_id].iloc[0]
                
                recommendations.append({
                    'ngo_name': opp['ngo_name'],
                    'description': opp['description'],
                    'required_skills': opp['required_skills'],
                    'importance_level': opp['importance_level'],
                    'work_calendar': opp['work_calendar'],
                    'score': min(1.0, max(0.0, (score + 2) / 4))  # Normalize to 0-1
                })
                
            return recommendations
            
        except Exception as e:
            logger.error(f"Error in LightFM recommendations: {e}")
            return self._get_fallback_recommendations(student_id, n_recommendations)
            
    def _get_content_based_recommendations(self, student_id, n_recommendations):
        """Get recommendations for new users based on content similarity"""
        try:
            user_profile = self.new_users[student_id]
            user_skills = set(user_profile.get('skills', []))
            user_interests = set(user_profile.get('interests', []))
            
            recommendations = []
            
            for _, opp in self.opportunities_df.iterrows():
                score = 0.0
                
                # Skill matching (60% weight)
                opp_skills = set(str(opp['required_skills']).lower().split(','))
                if user_skills and opp_skills:
                    skill_overlap = len(user_skills.intersection(opp_skills))
                    skill_score = skill_overlap / max(len(user_skills), len(opp_skills))
                    score += skill_score * 0.6
                
                # Interest matching (20% weight)  
                description_words = set(str(opp['description']).lower().split())
                interest_matches = sum(1 for interest in user_interests if interest.lower() in description_words)
                if user_interests:
                    interest_score = interest_matches / len(user_interests)
                    score += interest_score * 0.2
                
                # Importance level (20% weight)
                importance_weights = {'high': 1.0, 'medium': 0.7, 'low': 0.4}
                importance_score = importance_weights.get(opp['importance_level'], 0.5)
                score += importance_score * 0.2
                
                recommendations.append({
                    'ngo_name': opp['ngo_name'],
                    'description': opp['description'],
                    'required_skills': opp['required_skills'],
                    'importance_level': opp['importance_level'],
                    'work_calendar': opp['work_calendar'],
                    'score': min(1.0, max(0.0, score))
                })
            
            # Sort by score and return top recommendations
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            return recommendations[:n_recommendations]
            
        except Exception as e:
            logger.error(f"Error in content-based recommendations: {e}")
            return []
            
    def _get_fallback_recommendations(self, student_id, n_recommendations):
        """Fallback recommendation system using simple matching"""
        try:
            student = self.students_df[self.students_df['student_id'] == student_id].iloc[0]
            student_skills = str(student['skills']).lower().split(',')
            
            recommendations = []
            
            for _, opp in self.opportunities_df.iterrows():
                score = 0.5  # Base score
                
                # Simple skill matching
                opp_skills = str(opp['required_skills']).lower().split(',')
                common_skills = set(student_skills).intersection(set(opp_skills))
                if common_skills:
                    score += 0.3 * len(common_skills) / len(opp_skills)
                
                # Importance bonus
                if opp['importance_level'] == 'high':
                    score += 0.2
                elif opp['importance_level'] == 'medium':
                    score += 0.1
                    
                recommendations.append({
                    'ngo_name': opp['ngo_name'],
                    'description': opp['description'],
                    'required_skills': opp['required_skills'],
                    'importance_level': opp['importance_level'],
                    'work_calendar': opp['work_calendar'],
                    'score': min(1.0, max(0.0, score))
                })
            
            # Sort by score and return top recommendations
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            return recommendations[:n_recommendations]
            
        except Exception as e:
            logger.error(f"Error in fallback recommendations: {e}")
            return []
            
    def register_new_user(self, name, email, skills, interests, university=None):
        """Register a new user"""
        try:
            user_id = self.next_user_id
            self.next_user_id += 1
            
            # Process skills and interests
            skills_list = [s.strip().lower() for s in skills.split(',') if s.strip()]
            interests_list = [i.strip().lower() for i in interests.split(',') if i.strip()]
            
            self.new_users[user_id] = {
                'name': name,
                'email': email,
                'skills': skills_list,
                'interests': interests_list,
                'university': university or 'Not specified',
                'registered_at': datetime.now().isoformat()
            }
            
            logger.info(f"Registered new user: {user_id} - {name}")
            return user_id
            
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return None
            
    def add_opportunity(self, ngo_name, description, required_skills, importance_level, work_calendar):
        """Add a new opportunity"""
        try:
            opportunity_id = self.next_opportunity_id
            self.next_opportunity_id += 1
            
            new_opportunity = {
                'opportunity_id': opportunity_id,
                'ngo_name': ngo_name,
                'description': description,
                'required_skills': required_skills,
                'importance_level': importance_level,
                'work_calendar': work_calendar
            }
            
            # Add to DataFrame
            self.opportunities_df = pd.concat([
                self.opportunities_df,
                pd.DataFrame([new_opportunity])
            ], ignore_index=True)
            
            logger.info(f"Added new opportunity: {opportunity_id} - {ngo_name}")
            return opportunity_id
            
        except Exception as e:
            logger.error(f"Error adding opportunity: {e}")
            return None

# Initialize the matching system
matching_system = VolunteerMatchingSystem()

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Volunteer Matching Platform</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-gray-50 min-h-screen">
    <!-- Header -->
    <nav class="bg-gradient-to-r from-blue-600 to-purple-700 text-white shadow-lg">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center py-4">
                <div class="flex items-center">
                    <i class="fas fa-hands-helping text-2xl mr-3"></i>
                    <h1 class="text-2xl font-bold">Volunteer Matching Platform</h1>
                </div>
                <div id="user-info" class="hidden">
                    <span id="welcome-message" class="mr-4"></span>
                    <button onclick="logout()" class="bg-white text-blue-600 px-4 py-2 rounded-lg hover:bg-blue-50">
                        <i class="fas fa-sign-out-alt mr-1"></i>Logout
                    </button>
                </div>
            </div>
        </div>
    </nav>

    <!-- Login Page -->
    <div id="login-page" class="max-w-4xl mx-auto px-4 py-12">
        <div class="text-center mb-12">
            <h2 class="text-4xl font-bold text-gray-900 mb-4">Welcome to Volunteer Match</h2>
            <p class="text-xl text-gray-600">Connect students with meaningful volunteer opportunities</p>
        </div>

        <div class="grid md:grid-cols-2 gap-8">
            <!-- Student Login/Register -->
            <div class="bg-white rounded-xl shadow-lg p-8">
                <div class="text-center mb-6">
                    <div class="bg-blue-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                        <i class="fas fa-user-graduate text-blue-600 text-2xl"></i>
                    </div>
                    <h3 class="text-2xl font-bold text-gray-900 mb-2">For Students</h3>
                    <p class="text-gray-600">Find volunteer opportunities that match your skills</p>
                </div>

                <!-- Toggle between login and register -->
                <div class="mb-4">
                    <div class="flex bg-gray-100 rounded-lg p-1">
                        <button id="login-tab" onclick="showStudentLogin()" 
                                class="flex-1 py-2 px-4 rounded-md text-sm font-medium bg-white text-blue-600 shadow-sm">
                            Login
                        </button>
                        <button id="register-tab" onclick="showStudentRegister()" 
                                class="flex-1 py-2 px-4 rounded-md text-sm font-medium text-gray-500">
                            Register
                        </button>
                    </div>
                </div>

                <!-- Student Login Form -->
                <div id="student-login-form">
                    <div class="space-y-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Student ID or Email</label>
                            <input type="text" id="student-login-id" 
                                   class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                   placeholder="Enter student ID (0-9) or email">
                        </div>
                        <button onclick="studentLogin()" 
                                class="w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 font-semibold">
                            <i class="fas fa-sign-in-alt mr-2"></i>Login as Student
                        </button>
                    </div>
                </div>

                <!-- Student Registration Form -->
                <div id="student-register-form" class="hidden">
                    <div class="space-y-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Full Name</label>
                            <input type="text" id="register-name" 
                                   class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                   placeholder="Enter your full name">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Email</label>
                            <input type="email" id="register-email" 
                                   class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                   placeholder="Enter your email">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Skills</label>
                            <input type="text" id="register-skills" 
                                   class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                   placeholder="e.g., teaching, programming, design (comma separated)">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Interests</label>
                            <input type="text" id="register-interests" 
                                   class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                   placeholder="e.g., education, environment, health (comma separated)">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">University</label>
                            <input type="text" id="register-university" 
                                   class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                   placeholder="Enter your university name">
                        </div>
                        <button onclick="studentRegister()" 
                                class="w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 font-semibold">
                            <i class="fas fa-user-plus mr-2"></i>Register Account
                        </button>
                    </div>
                </div>
            </div>

            <!-- NGO Login -->
            <div class="bg-white rounded-xl shadow-lg p-8">
                <div class="text-center mb-6">
                    <div class="bg-green-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                        <i class="fas fa-building text-green-600 text-2xl"></i>
                    </div>
                    <h3 class="text-2xl font-bold text-gray-900 mb-2">For NGOs</h3>
                    <p class="text-gray-600">Post volunteer opportunities and find dedicated volunteers</p>
                </div>

                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">NGO Name</label>
                        <input type="text" id="ngo-name" 
                               class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                               placeholder="Enter your organization name">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Contact Email</label>
                        <input type="email" id="ngo-email" 
                               class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                               placeholder="Enter contact email">
                    </div>
                    <button onclick="ngoLogin()" 
                            class="w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 font-semibold">
                        <i class="fas fa-sign-in-alt mr-2"></i>Login as NGO
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- Student Dashboard -->
    <div id="student-dashboard" class="hidden max-w-7xl mx-auto px-4 py-8">
        <div class="mb-8">
            <h2 class="text-3xl font-bold text-gray-900 mb-2">Your Recommendations</h2>
            <p class="text-gray-600">Personalized volunteer opportunities based on your profile</p>
        </div>

        <div id="loading" class="text-center py-12">
            <div class="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p class="text-gray-600">Loading your personalized recommendations...</p>
        </div>

        <div id="recommendations-container" class="hidden">
            <div id="recommendations-list" class="space-y-6">
                <!-- Recommendations will be inserted here -->
            </div>
        </div>

        <div id="no-recommendations" class="hidden text-center py-12">
            <i class="fas fa-search text-gray-400 text-6xl mb-4"></i>
            <h3 class="text-xl font-semibold text-gray-600 mb-2">No Recommendations Found</h3>
            <p class="text-gray-500">We couldn't find any matching opportunities at the moment.</p>
        </div>
    </div>

    <!-- NGO Dashboard -->
    <div id="ngo-dashboard" class="hidden max-w-4xl mx-auto px-4 py-8">
        <div class="mb-8">
            <h2 class="text-3xl font-bold text-gray-900 mb-2">Post New Opportunity</h2>
            <p class="text-gray-600">Create volunteer opportunities for students to discover</p>
        </div>

        <div class="bg-white rounded-xl shadow-lg p-8">
            <div class="space-y-6">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Organization Name</label>
                    <input type="text" id="opportunity-ngo-name" 
                           class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                           placeholder="Enter your organization name">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Opportunity Description</label>
                    <textarea id="opportunity-description" rows="4"
                              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                              placeholder="Describe the volunteer opportunity in detail..."></textarea>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Required Skills</label>
                    <input type="text" id="opportunity-skills" 
                           class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                           placeholder="e.g., teaching, communication, teamwork (comma separated)">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Importance Level</label>
                    <select id="opportunity-importance" 
                            class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500">
                        <option value="low">Low</option>
                        <option value="medium" selected>Medium</option>
                        <option value="high">High</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Work Schedule</label>
                    <input type="text" id="opportunity-calendar" 
                           class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                           placeholder="e.g., Weekends, 2-3 hours per week, Flexible">
                </div>
                <button onclick="postOpportunity()" 
                        class="w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 font-semibold">
                    <i class="fas fa-plus mr-2"></i>Post Opportunity
                </button>
            </div>
        </div>
    </div>

    <!-- Alert Messages -->
    <div id="alert-container" class="fixed top-4 right-4 z-50"></div>

    <script>
        let currentUser = null;
        let currentUserType = null;

        function showAlert(message, type = 'info') {
            const alertContainer = document.getElementById('alert-container');
            const alert = document.createElement('div');
            const bgColor = type === 'success' ? 'bg-green-500' : 
                           type === 'error' ? 'bg-red-500' : 'bg-blue-500';
            
            alert.className = `${bgColor} text-white px-6 py-3 rounded-lg shadow-lg mb-3 opacity-0 transform translate-x-full transition-all duration-300`;
            alert.innerHTML = `
                <div class="flex items-center">
                    <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-triangle' : 'info-circle'} mr-2"></i>
                    ${message}
                </div>
            `;
            
            alertContainer.appendChild(alert);
            
            // Animate in
            setTimeout(() => {
                alert.classList.remove('opacity-0', 'translate-x-full');
            }, 100);
            
            // Remove after 5 seconds
            setTimeout(() => {
                alert.classList.add('opacity-0', 'translate-x-full');
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.parentNode.removeChild(alert);
                    }
                }, 300);
            }, 5000);
        }

        function showStudentLogin() {
            document.getElementById('login-tab').classList.add('bg-white', 'text-blue-600', 'shadow-sm');
            document.getElementById('login-tab').classList.remove('text-gray-500');
            document.getElementById('register-tab').classList.remove('bg-white', 'text-blue-600', 'shadow-sm');
            document.getElementById('register-tab').classList.add('text-gray-500');
            
            document.getElementById('student-login-form').classList.remove('hidden');
            document.getElementById('student-register-form').classList.add('hidden');
        }

        function showStudentRegister() {
            document.getElementById('register-tab').classList.add('bg-white', 'text-blue-600', 'shadow-sm');
            document.getElementById('register-tab').classList.remove('text-gray-500');
            document.getElementById('login-tab').classList.remove('bg-white', 'text-blue-600', 'shadow-sm');
            document.getElementById('login-tab').classList.add('text-gray-500');
            
            document.getElementById('student-register-form').classList.remove('hidden');
            document.getElementById('student-login-form').classList.add('hidden');
        }

        async function studentLogin() {
            const loginId = document.getElementById('student-login-id').value.trim();
            
            if (!loginId) {
                showAlert('Please enter your student ID or email', 'error');
                return;
            }

            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        name: 'Student',
                        email: loginId.includes('@') ? loginId : `student${loginId}@example.com`,
                        user_type: 'student',
                        student_id: loginId.includes('@') ? null : parseInt(loginId)
                    })
                });

                const data = await response.json();
                
                if (data.success) {
                    currentUser = data.user_id;
                    currentUserType = data.user_type;
                    showStudentDashboard();
                    showAlert('Login successful!', 'success');
                } else {
                    showAlert(data.message || 'Login failed', 'error');
                }
            } catch (error) {
                showAlert('Network error. Please try again.', 'error');
            }
        }

        async function studentRegister() {
            const name = document.getElementById('register-name').value.trim();
            const email = document.getElementById('register-email').value.trim();
            const skills = document.getElementById('register-skills').value.trim();
            const interests = document.getElementById('register-interests').value.trim();
            const university = document.getElementById('register-university').value.trim();

            if (!name || !email || !skills || !interests) {
                showAlert('Please fill in all required fields', 'error');
                return;
            }

            try {
                const response = await fetch('/api/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        name: name,
                        email: email,
                        skills: skills,
                        interests: interests,
                        university: university
                    })
                });

                const data = await response.json();
                
                if (data.success) {
                    currentUser = data.user_id;
                    currentUserType = 'student';
                    showStudentDashboard();
                    showAlert('Registration successful! Welcome!', 'success');
                } else {
                    showAlert(data.message || 'Registration failed', 'error');
                }
            } catch (error) {
                showAlert('Network error. Please try again.', 'error');
            }
        }

        async function ngoLogin() {
            const ngoName = document.getElementById('ngo-name').value.trim();
            const email = document.getElementById('ngo-email').value.trim();
            
            if (!ngoName || !email) {
                showAlert('Please fill in all fields', 'error');
                return;
            }

            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        name: ngoName,
                        email: email,
                        user_type: 'ngo'
                    })
                });

                const data = await response.json();
                
                if (data.success) {
                    currentUser = data.user_id;
                    currentUserType = data.user_type;
                    showNgoDashboard();
                    showAlert('NGO login successful!', 'success');
                } else {
                    showAlert(data.message || 'Login failed', 'error');
                }
            } catch (error) {
                showAlert('Network error. Please try again.', 'error');
            }
        }

        function showStudentDashboard() {
            document.getElementById('login-page').classList.add('hidden');
            document.getElementById('student-dashboard').classList.remove('hidden');
            document.getElementById('user-info').classList.remove('hidden');
            document.getElementById('welcome-message').textContent = `Welcome, Student!`;
            
            loadRecommendations();
        }

        function showNgoDashboard() {
            document.getElementById('login-page').classList.add('hidden');
            document.getElementById('ngo-dashboard').classList.remove('hidden');
            document.getElementById('user-info').classList.remove('hidden');
            document.getElementById('welcome-message').textContent = `Welcome, NGO!`;
        }

        async function loadRecommendations() {
            document.getElementById('loading').classList.remove('hidden');
            document.getElementById('recommendations-container').classList.add('hidden');
            document.getElementById('no-recommendations').classList.add('hidden');

            try {
                const response = await fetch(`/api/recommendations/${currentUser}`);
                const recommendations = await response.json();
                
                document.getElementById('loading').classList.add('hidden');
                
                if (recommendations && recommendations.length > 0) {
                    displayRecommendations(recommendations);
                } else {
                    document.getElementById('no-recommendations').classList.remove('hidden');
                }
            } catch (error) {
                document.getElementById('loading').classList.add('hidden');
                document.getElementById('no-recommendations').classList.remove('hidden');
                showAlert('Failed to load recommendations', 'error');
            }
        }

        function displayRecommendations(recommendations) {
            const container = document.getElementById('recommendations-list');
            container.innerHTML = '';
            
            recommendations.forEach((rec, index) => {
                const recElement = document.createElement('div');
                recElement.className = 'bg-white rounded-xl shadow-lg p-6 border-l-4 border-blue-500 hover:shadow-xl transition-shadow';
                
                const scorePercentage = Math.round(rec.score * 100);
                const importanceColor = {
                    'high': 'bg-red-100 text-red-800',
                    'medium': 'bg-yellow-100 text-yellow-800',
                    'low': 'bg-green-100 text-green-800'
                }[rec.importance_level] || 'bg-gray-100 text-gray-800';
                
                recElement.innerHTML = `
                    <div class="flex justify-between items-start mb-4">
                        <div class="flex-1">
                            <h3 class="text-xl font-bold text-gray-800 mb-2">${rec.ngo_name}</h3>
                            <div class="flex items-center mb-2">
                                <div class="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium">
                                    ${scorePercentage}% Match
                                </div>
                                <div class="ml-2">
                                    <span class="px-2 py-1 rounded text-xs font-medium ${importanceColor}">
                                        ${rec.importance_level.toUpperCase()}
                                    </span>
                                </div>
                            </div>
                        </div>
                        <div class="text-right">
                            <div class="text-sm text-gray-500">Recommendation #${index + 1}</div>
                        </div>
                    </div>
                    
                    <p class="text-gray-600 mb-4">${rec.description}</p>
                    
                    <div class="mb-4">
                        <div class="text-sm text-gray-500 mb-2">Required Skills:</div>
                        <div class="text-sm text-gray-800">${rec.required_skills}</div>
                    </div>
                    
                    <div class="flex justify-between items-center">
                        <div class="text-sm text-gray-500">
                            <i class="fas fa-calendar mr-1"></i>
                            ${rec.work_calendar}
                        </div>
                        <button onclick="applyToOpportunity(${index})" 
                                class="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 transition-colors">
                            <i class="fas fa-hand-paper mr-2"></i>Apply Now
                        </button>
                    </div>
                `;
                
                container.appendChild(recElement);
            });
            
            document.getElementById('recommendations-container').classList.remove('hidden');
        }

        function applyToOpportunity(index) {
            showAlert(`Application submitted for opportunity #${index + 1}!`, 'success');
        }

        async function postOpportunity() {
            const ngoName = document.getElementById('opportunity-ngo-name').value.trim();
            const description = document.getElementById('opportunity-description').value.trim();
            const skills = document.getElementById('opportunity-skills').value.trim();
            const importance = document.getElementById('opportunity-importance').value;
            const calendar = document.getElementById('opportunity-calendar').value.trim();

            if (!ngoName || !description || !skills || !calendar) {
                showAlert('Please fill in all fields', 'error');
                return;
            }

            try {
                const response = await fetch('/api/opportunities', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        ngo_name: ngoName,
                        description: description,
                        required_skills: skills,
                        importance_level: importance,
                        work_calendar: calendar
                    })
                });

                const data = await response.json();
                
                if (data.success) {
                    showAlert('Opportunity posted successfully!', 'success');
                    // Clear form
                    document.getElementById('opportunity-ngo-name').value = '';
                    document.getElementById('opportunity-description').value = '';
                    document.getElementById('opportunity-skills').value = '';
                    document.getElementById('opportunity-importance').value = 'medium';
                    document.getElementById('opportunity-calendar').value = '';
                } else {
                    showAlert(data.message || 'Failed to post opportunity', 'error');
                }
            } catch (error) {
                showAlert('Network error. Please try again.', 'error');
            }
        }

        function logout() {
            currentUser = null;
            currentUserType = null;
            
            document.getElementById('student-dashboard').classList.add('hidden');
            document.getElementById('ngo-dashboard').classList.add('hidden');
            document.getElementById('user-info').classList.add('hidden');
            document.getElementById('login-page').classList.remove('hidden');
            
            // Reset forms
            document.getElementById('student-login-id').value = '';
            document.getElementById('ngo-name').value = '';
            document.getElementById('ngo-email').value = '';
            
            showAlert('Logged out successfully', 'success');
        }
    </script>
</body>
</html>
"""

# Flask Routes
@app.route('/')
def index():
    """Serve the main HTML page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/login', methods=['POST'])
def api_login():
    """Handle user login"""
    try:
        data = request.get_json()
        name = data.get('name', '')
        email = data.get('email', '')
        user_type = data.get('user_type', '')
        student_id = data.get('student_id')
        
        if user_type == 'student':
            # Check if it's an existing student (by ID)
            if student_id is not None:
                if student_id in matching_system.students_df['student_id'].values:
                    return jsonify({
                        'success': True,
                        'user_id': student_id,
                        'user_type': 'student',
                        'message': 'Login successful'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Student ID not found. Please register first.'
                    })
            else:
                # Email-based login - check if user exists in new users
                for user_id, profile in matching_system.new_users.items():
                    if profile['email'] == email:
                        return jsonify({
                            'success': True,
                            'user_id': user_id,
                            'user_type': 'student',
                            'message': 'Login successful'
                        })
                
                return jsonify({
                    'success': False,
                    'message': 'Email not found. Please register first.'
                })
                
        elif user_type == 'ngo':
            # Simple NGO login - just accept any valid input
            return jsonify({
                'success': True,
                'user_id': f"ngo_{hash(email) % 1000}",
                'user_type': 'ngo',
                'message': 'NGO login successful'
            })
        
        return jsonify({
            'success': False,
            'message': 'Invalid user type'
        })
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({
            'success': False,
            'message': 'Login failed'
        })

@app.route('/api/register', methods=['POST'])
def api_register():
    """Handle user registration"""
    try:
        data = request.get_json()
        name = data.get('name', '')
        email = data.get('email', '')
        skills = data.get('skills', '')
        interests = data.get('interests', '')
        university = data.get('university', '')
        
        if not all([name, email, skills, interests]):
            return jsonify({
                'success': False,
                'message': 'All fields are required'
            })
        
        # Check if email already exists
        for profile in matching_system.new_users.values():
            if profile['email'] == email:
                return jsonify({
                    'success': False,
                    'message': 'Email already registered'
                })
        
        user_id = matching_system.register_new_user(name, email, skills, interests, university)
        
        if user_id:
            return jsonify({
                'success': True,
                'user_id': user_id,
                'message': 'Registration successful'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Registration failed'
            })
            
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({
            'success': False,
            'message': 'Registration failed'
        })

@app.route('/api/recommendations/<int:student_id>')
def api_recommendations(student_id):
    """Get recommendations for a student"""
    try:
        recommendations = matching_system.get_recommendations(student_id, 5)
        return jsonify(recommendations)
    except Exception as e:
        logger.error(f"Recommendations error: {e}")
        return jsonify([])

@app.route('/api/opportunities', methods=['POST'])
def api_opportunities():
    """Add a new opportunity"""
    try:
        data = request.get_json()
        ngo_name = data.get('ngo_name', '')
        description = data.get('description', '')
        required_skills = data.get('required_skills', '')
        importance_level = data.get('importance_level', 'medium')
        work_calendar = data.get('work_calendar', '')
        
        if not all([ngo_name, description, required_skills, work_calendar]):
            return jsonify({
                'success': False,
                'message': 'All fields are required'
            })
        
        opportunity_id = matching_system.add_opportunity(
            ngo_name, description, required_skills, importance_level, work_calendar
        )
        
        if opportunity_id:
            return jsonify({
                'success': True,
                'opportunity_id': opportunity_id,
                'message': 'Opportunity posted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to post opportunity'
            })
            
    except Exception as e:
        logger.error(f"Add opportunity error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to post opportunity'
        })

def initialize_system():
    """Initialize the matching system"""
    logger.info("Initializing Volunteer Matching System...")
    
    # Load data
    if not matching_system.load_data():
        logger.error("Failed to load data")
        return False
    
    # Build and train model
    if not matching_system.build_lightfm_dataset():
        logger.warning("Using fallback recommendation system")
    
    logger.info("System initialized successfully!")
    return True

if __name__ == '__main__':
    # Initialize the system
    if initialize_system():
        print("🚀 Volunteer Matching Platform is starting...")
        print("🌐 Open your browser to: http://localhost:5000")
        print("🛑 Press Ctrl+C to stop the server")
        
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("❌ Failed to initialize system")
        sys.exit(1)