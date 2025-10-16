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

# Alternative recommendation system using scikit-learn
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    print("Warning: scikit-learn not available. Using basic fallback.")
    SKLEARN_AVAILABLE = False

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
        self.time_slots_df = None
        self.bookings_df = None
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
        self.next_slot_id = 1000  # Start new slot IDs from 1000
        self.next_booking_id = 1000  # Start new booking IDs from 1000
        
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

            # Load time slots data
            if os.path.exists('time_slots.csv'):
                self.time_slots_df = pd.read_csv('time_slots.csv')
                logger.info(f"Loaded {len(self.time_slots_df)} time slots")
            else:
                # Create sample time slots data
                self.time_slots_df = pd.DataFrame({
                    'slot_id': range(20),
                    'opportunity_id': range(20),
                    'date': [f'2024-01-{i+1:02d}' for i in range(20)],
                    'start_time': [f'{9+i%3:02d}:00' for i in range(20)],
                    'end_time': [f'{12+i%3:02d}:00' for i in range(20)],
                    'max_participants': [5] * 20,
                    'current_participants': [0] * 20,
                    'status': ['available'] * 20
                })

            # Load bookings data
            if os.path.exists('bookings.csv'):
                self.bookings_df = pd.read_csv('bookings.csv')
                logger.info(f"Loaded {len(self.bookings_df)} bookings")
            else:
                # Create empty bookings DataFrame
                self.bookings_df = pd.DataFrame(columns=[
                    'booking_id', 'student_id', 'slot_id', 'booking_date', 'status', 'notes'
                ])

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

    def get_available_slots(self, opportunity_id):
        """Get available time slots for a specific opportunity"""
        try:
            if self.time_slots_df is None:
                return []

            # Filter slots for the opportunity that are available
            available_slots = self.time_slots_df[
                (self.time_slots_df['opportunity_id'] == opportunity_id) &
                (self.time_slots_df['status'] == 'available') &
                (self.time_slots_df['current_participants'] < self.time_slots_df['max_participants'])
            ]

            # Convert to list of dictionaries
            slots = []
            for _, slot in available_slots.iterrows():
                slots.append({
                    'slot_id': int(slot['slot_id']),
                    'opportunity_id': int(slot['opportunity_id']),
                    'date': slot['date'],
                    'start_time': slot['start_time'],
                    'end_time': slot['end_time'],
                    'max_participants': int(slot['max_participants']),
                    'current_participants': int(slot['current_participants']),
                    'available_spots': int(slot['max_participants'] - slot['current_participants'])
                })

            return slots

        except Exception as e:
            logger.error(f"Error getting available slots: {e}")
            return []

    def book_slot(self, student_id, slot_id, notes=""):
        """Book a time slot for a student"""
        try:
            # Check if slot exists and is available
            slot = self.time_slots_df[self.time_slots_df['slot_id'] == slot_id]
            if slot.empty:
                return {'success': False, 'message': 'Time slot not found'}

            slot = slot.iloc[0]

            # Check if slot is available
            if slot['status'] != 'available':
                return {'success': False, 'message': 'Time slot is not available'}

            # Check if slot has capacity
            if slot['current_participants'] >= slot['max_participants']:
                return {'success': False, 'message': 'Time slot is fully booked'}

            # Check if student already has a booking for this slot
            existing_booking = self.bookings_df[
                (self.bookings_df['student_id'] == student_id) &
                (self.bookings_df['slot_id'] == slot_id) &
                (self.bookings_df['status'] == 'confirmed')
            ]
            if not existing_booking.empty:
                return {'success': False, 'message': 'You have already booked this time slot'}

            # Check if student has conflicting bookings (same time on same day)
            slot_date = slot['date']
            slot_start = slot['start_time']
            slot_end = slot['end_time']

            student_bookings = self.bookings_df[
                (self.bookings_df['student_id'] == student_id) &
                (self.bookings_df['status'] == 'confirmed')
            ]

            for _, booking in student_bookings.iterrows():
                booked_slot = self.time_slots_df[self.time_slots_df['slot_id'] == booking['slot_id']].iloc[0]
                if (booked_slot['date'] == slot_date and
                    ((slot_start < booked_slot['end_time'] and slot_end > booked_slot['start_time']))):
                    return {'success': False, 'message': 'You have a conflicting booking at this time'}

            # Create booking
            booking_id = self.next_booking_id
            self.next_booking_id += 1

            new_booking = {
                'booking_id': booking_id,
                'student_id': student_id,
                'slot_id': slot_id,
                'booking_date': datetime.now().strftime('%Y-%m-%d'),
                'status': 'confirmed',
                'notes': notes
            }

            # Add booking to DataFrame
            self.bookings_df = pd.concat([
                self.bookings_df,
                pd.DataFrame([new_booking])
            ], ignore_index=True)

            # Update slot participants count
            self.time_slots_df.loc[self.time_slots_df['slot_id'] == slot_id, 'current_participants'] += 1

            # Update slot status if full
            if slot['current_participants'] + 1 >= slot['max_participants']:
                self.time_slots_df.loc[self.time_slots_df['slot_id'] == slot_id, 'status'] = 'full'

            logger.info(f"Booking created: {booking_id} for student {student_id} slot {slot_id}")
            return {'success': True, 'booking_id': booking_id, 'message': 'Booking confirmed successfully'}

        except Exception as e:
            logger.error(f"Error booking slot: {e}")
            return {'success': False, 'message': 'Failed to create booking'}

    def get_student_bookings(self, student_id):
        """Get all bookings for a student"""
        try:
            if self.bookings_df is None:
                return []

            # Get student's confirmed bookings
            student_bookings = self.bookings_df[
                (self.bookings_df['student_id'] == student_id) &
                (self.bookings_df['status'] == 'confirmed')
            ]

            bookings = []
            for _, booking in student_bookings.iterrows():
                slot = self.time_slots_df[self.time_slots_df['slot_id'] == booking['slot_id']].iloc[0]
                opportunity = self.opportunities_df[self.opportunities_df['opportunity_id'] == slot['opportunity_id']].iloc[0]

                bookings.append({
                    'booking_id': int(booking['booking_id']),
                    'slot_id': int(booking['slot_id']),
                    'opportunity_id': int(slot['opportunity_id']),
                    'ngo_name': opportunity['ngo_name'],
                    'description': opportunity['description'],
                    'date': slot['date'],
                    'start_time': slot['start_time'],
                    'end_time': slot['end_time'],
                    'booking_date': booking['booking_date'],
                    'notes': booking['notes']
                })

            # Sort by date and time
            bookings.sort(key=lambda x: (x['date'], x['start_time']))
            return bookings

        except Exception as e:
            logger.error(f"Error getting student bookings: {e}")
            return []

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
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        @keyframes pulse-glow {
            0%, 100% { box-shadow: 0 0 20px rgba(59, 130, 246, 0.5); }
            50% { box-shadow: 0 0 30px rgba(59, 130, 246, 0.8); }
        }
        @keyframes slideInUp {
            from { transform: translateY(30px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        @keyframes fadeInScale {
            from { transform: scale(0.9); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }
        .animate-float { animation: float 3s ease-in-out infinite; }
        .animate-pulse-glow { animation: pulse-glow 2s ease-in-out infinite; }
        .animate-slide-in-up { animation: slideInUp 0.6s ease-out; }
        .animate-fade-in-scale { animation: fadeInScale 0.5s ease-out; }
        .gradient-bg {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .glass-effect {
            backdrop-filter: blur(10px);
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .skill-match-bar {
            background: linear-gradient(90deg, #10b981 0%, #34d399 100%);
            border-radius: 4px;
            transition: width 1s ease-in-out;
        }
    </style>
</head>
<body class="bg-gradient-to-br from-indigo-50 via-white to-cyan-50 min-h-screen overflow-x-hidden">
    <!-- Animated Background Elements -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none">
        <div class="absolute -top-40 -right-40 w-80 h-80 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-float"></div>
        <div class="absolute -bottom-40 -left-40 w-80 h-80 bg-yellow-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-float" style="animation-delay: 2s;"></div>
        <div class="absolute top-40 left-1/2 w-80 h-80 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-float" style="animation-delay: 4s;"></div>
    </div>

    <!-- Header -->
    <nav class="relative z-10 bg-white/80 backdrop-blur-lg border-b border-white/20 shadow-lg">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center py-4">
                <div class="flex items-center">
                    <div class="bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl p-2 mr-3 animate-pulse-glow">
                        <i class="fas fa-hands-helping text-white text-xl"></i>
                    </div>
                    <div>
                        <h1 class="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">VolunteerMatch</h1>
                        <p class="text-xs text-gray-500 -mt-1">AI-Powered Connections</p>
                    </div>
                </div>
                <div id="user-info" class="hidden flex items-center">
                    <div class="flex items-center mr-4">
                        <div class="w-8 h-8 bg-gradient-to-r from-green-400 to-blue-500 rounded-full flex items-center justify-center mr-2">
                            <i class="fas fa-user text-white text-xs"></i>
                        </div>
                        <span id="welcome-message" class="text-sm font-medium text-gray-700"></span>
                    </div>
                    <button onclick="logout()" class="bg-gradient-to-r from-red-500 to-pink-500 text-white px-4 py-2 rounded-lg hover:from-red-600 hover:to-pink-600 transition-all duration-300 transform hover:scale-105 shadow-lg">
                        <i class="fas fa-sign-out-alt mr-1"></i>Logout
                    </button>
                </div>
            </div>
        </div>
    </nav>

    <!-- Login Page -->
    <div id="login-page" class="relative z-10 max-w-6xl mx-auto px-4 py-16">
        <!-- Hero Section -->
        <div class="text-center mb-16 animate-slide-in-up">
            <div class="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full mb-6 animate-pulse-glow">
                <i class="fas fa-heart text-white text-3xl"></i>
            </div>
            <h2 class="text-5xl font-bold text-gray-900 mb-4 bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-600 bg-clip-text text-transparent">
                Make a Difference Today
            </h2>
            <p class="text-xl text-gray-600 max-w-2xl mx-auto leading-relaxed">
                Join thousands of students and NGOs creating positive change through our AI-powered volunteer matching platform
            </p>
            <div class="flex justify-center mt-8 space-x-8 text-sm text-gray-500">
                <div class="flex items-center">
                    <i class="fas fa-users text-blue-500 mr-2"></i>
                    <span>10,000+ Volunteers</span>
                </div>
                <div class="flex items-center">
                    <i class="fas fa-building text-green-500 mr-2"></i>
                    <span>500+ NGOs</span>
                </div>
                <div class="flex items-center">
                    <i class="fas fa-star text-yellow-500 mr-2"></i>
                    <span>98% Match Rate</span>
                </div>
            </div>
        </div>

        <div class="grid lg:grid-cols-2 gap-12 items-start">
            <!-- Student Login/Register -->
            <div class="bg-white/70 backdrop-blur-lg rounded-2xl shadow-2xl p-8 border border-white/20 animate-fade-in-scale hover:shadow-3xl transition-all duration-500 transform hover:-translate-y-2">
                <div class="text-center mb-8">
                    <div class="relative inline-block">
                        <div class="w-20 h-20 bg-gradient-to-r from-blue-400 to-blue-600 rounded-2xl flex items-center justify-center mb-4 animate-float shadow-lg">
                            <i class="fas fa-user-graduate text-white text-3xl"></i>
                        </div>
                        <div class="absolute -top-2 -right-2 w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                            <i class="fas fa-check text-white text-xs"></i>
                        </div>
                    </div>
                    <h3 class="text-3xl font-bold text-gray-900 mb-3">Student Portal</h3>
                    <p class="text-gray-600 text-lg">Discover opportunities that match your passion and skills</p>
                </div>

                <!-- Toggle between login and register -->
                <div class="mb-6">
                    <div class="relative bg-gray-100 rounded-xl p-1 shadow-inner">
                        <div class="absolute inset-1 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg transition-all duration-300" id="tab-indicator"></div>
                        <button id="login-tab" onclick="showStudentLogin()"
                                class="relative z-10 flex-1 py-3 px-6 rounded-lg text-sm font-semibold transition-all duration-300">
                            <i class="fas fa-sign-in-alt mr-2"></i>Login
                        </button>
                        <button id="register-tab" onclick="showStudentRegister()"
                                class="relative z-10 flex-1 py-3 px-6 rounded-lg text-sm font-semibold transition-all duration-300">
                            <i class="fas fa-user-plus mr-2"></i>Register
                        </button>
                    </div>
                </div>

                <!-- Student Login Form -->
                <div id="student-login-form" class="animate-slide-in-up">
                    <div class="space-y-5">
                        <div class="relative">
                            <label class="block text-sm font-semibold text-gray-700 mb-2">Student ID or Email</label>
                            <div class="relative">
                                <input type="text" id="student-login-id"
                                       class="w-full pl-12 pr-4 py-4 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/20 transition-all duration-300"
                                       placeholder="Enter student ID (0-9) or email">
                                <div class="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400">
                                    <i class="fas fa-id-card"></i>
                                </div>
                            </div>
                        </div>
                        <button onclick="studentLogin()"
                                class="w-full bg-gradient-to-r from-blue-500 to-blue-600 text-white py-4 px-6 rounded-xl hover:from-blue-600 hover:to-blue-700 font-semibold text-lg shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105">
                            <i class="fas fa-rocket mr-2"></i>Start Your Journey
                        </button>
                    </div>
                </div>

                <!-- Student Registration Form -->
                <div id="student-register-form" class="hidden animate-slide-in-up">
                    <div class="space-y-5">
                        <div class="relative">
                            <label class="block text-sm font-semibold text-gray-700 mb-2">Full Name</label>
                            <div class="relative">
                                <input type="text" id="register-name"
                                       class="w-full pl-12 pr-4 py-4 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/20 transition-all duration-300"
                                       placeholder="Enter your full name">
                                <div class="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400">
                                    <i class="fas fa-user"></i>
                                </div>
                            </div>
                        </div>
                        <div class="relative">
                            <label class="block text-sm font-semibold text-gray-700 mb-2">Email</label>
                            <div class="relative">
                                <input type="email" id="register-email"
                                       class="w-full pl-12 pr-4 py-4 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/20 transition-all duration-300"
                                       placeholder="Enter your email">
                                <div class="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400">
                                    <i class="fas fa-envelope"></i>
                                </div>
                            </div>
                        </div>
                        <div class="relative">
                            <label class="block text-sm font-semibold text-gray-700 mb-2">Skills</label>
                            <div class="relative">
                                <input type="text" id="register-skills"
                                       class="w-full pl-12 pr-4 py-4 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/20 transition-all duration-300"
                                       placeholder="e.g., teaching, programming, design">
                                <div class="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400">
                                    <i class="fas fa-tools"></i>
                                </div>
                            </div>
                            <p class="text-xs text-gray-500 mt-1">Separate skills with commas</p>
                        </div>
                        <div class="relative">
                            <label class="block text-sm font-semibold text-gray-700 mb-2">Interests</label>
                            <div class="relative">
                                <input type="text" id="register-interests"
                                       class="w-full pl-12 pr-4 py-4 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/20 transition-all duration-300"
                                       placeholder="e.g., education, environment, health">
                                <div class="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400">
                                    <i class="fas fa-heart"></i>
                                </div>
                            </div>
                            <p class="text-xs text-gray-500 mt-1">Separate interests with commas</p>
                        </div>
                        <div class="relative">
                            <label class="block text-sm font-semibold text-gray-700 mb-2">University</label>
                            <div class="relative">
                                <input type="text" id="register-university"
                                       class="w-full pl-12 pr-4 py-4 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/20 transition-all duration-300"
                                       placeholder="Enter your university name">
                                <div class="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400">
                                    <i class="fas fa-university"></i>
                                </div>
                            </div>
                        </div>
                        <button onclick="studentRegister()"
                                class="w-full bg-gradient-to-r from-green-500 to-green-600 text-white py-4 px-6 rounded-xl hover:from-green-600 hover:to-green-700 font-semibold text-lg shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105">
                            <i class="fas fa-user-plus mr-2"></i>Create Your Account
                        </button>
                    </div>
                </div>
            </div>

            <!-- NGO Login -->
            <div class="bg-white/70 backdrop-blur-lg rounded-2xl shadow-2xl p-8 border border-white/20 animate-fade-in-scale hover:shadow-3xl transition-all duration-500 transform hover:-translate-y-2" style="animation-delay: 0.2s;">
                <div class="text-center mb-8">
                    <div class="relative inline-block">
                        <div class="w-20 h-20 bg-gradient-to-r from-green-400 to-green-600 rounded-2xl flex items-center justify-center mb-4 animate-float shadow-lg">
                            <i class="fas fa-building text-white text-3xl"></i>
                        </div>
                        <div class="absolute -top-2 -right-2 w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                            <i class="fas fa-star text-white text-xs"></i>
                        </div>
                    </div>
                    <h3 class="text-3xl font-bold text-gray-900 mb-3">NGO Portal</h3>
                    <p class="text-gray-600 text-lg">Connect with passionate volunteers for your mission</p>
                </div>

                <div class="space-y-5 animate-slide-in-up">
                    <div class="relative">
                        <label class="block text-sm font-semibold text-gray-700 mb-2">Organization Name</label>
                        <div class="relative">
                            <input type="text" id="ngo-name"
                                   class="w-full pl-12 pr-4 py-4 border-2 border-gray-200 rounded-xl focus:border-green-500 focus:ring-4 focus:ring-green-500/20 transition-all duration-300"
                                   placeholder="Enter your organization name">
                            <div class="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400">
                                <i class="fas fa-building"></i>
                            </div>
                        </div>
                    </div>
                    <div class="relative">
                        <label class="block text-sm font-semibold text-gray-700 mb-2">Contact Email</label>
                        <div class="relative">
                            <input type="email" id="ngo-email"
                                   class="w-full pl-12 pr-4 py-4 border-2 border-gray-200 rounded-xl focus:border-green-500 focus:ring-4 focus:ring-green-500/20 transition-all duration-300"
                                   placeholder="Enter contact email">
                            <div class="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400">
                                <i class="fas fa-envelope"></i>
                            </div>
                        </div>
                    </div>
                    <button onclick="ngoLogin()"
                            class="w-full bg-gradient-to-r from-green-500 to-green-600 text-white py-4 px-6 rounded-xl hover:from-green-600 hover:to-green-700 font-semibold text-lg shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105">
                        <i class="fas fa-sign-in-alt mr-2"></i>Access NGO Dashboard
                    </button>
                </div>

                <!-- Feature Highlights -->
                <div class="mt-8 pt-6 border-t border-gray-200">
                    <h4 class="text-sm font-semibold text-gray-700 mb-4 text-center">Why Choose Our Platform?</h4>
                    <div class="grid grid-cols-2 gap-4 text-center">
                        <div class="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-3">
                            <i class="fas fa-brain text-blue-500 text-lg mb-1"></i>
                            <p class="text-xs text-gray-600">AI Matching</p>
                        </div>
                        <div class="bg-gradient-to-r from-green-50 to-blue-50 rounded-lg p-3">
                            <i class="fas fa-calendar-check text-green-500 text-lg mb-1"></i>
                            <p class="text-xs text-gray-600">Easy Booking</p>
                        </div>
                        <div class="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-3">
                            <i class="fas fa-chart-line text-purple-500 text-lg mb-1"></i>
                            <p class="text-xs text-gray-600">Impact Tracking</p>
                        </div>
                        <div class="bg-gradient-to-r from-yellow-50 to-orange-50 rounded-lg p-3">
                            <i class="fas fa-users text-yellow-500 text-lg mb-1"></i>
                            <p class="text-xs text-gray-600">Community</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Student Dashboard -->
    <div id="student-dashboard" class="hidden max-w-7xl mx-auto px-4 py-8">
        <!-- Dashboard Navigation -->
        <div class="mb-8">
            <div class="flex justify-between items-center mb-4">
                <div>
                    <h2 class="text-3xl font-bold text-gray-900 mb-2">Student Dashboard</h2>
                    <p class="text-gray-600">Find opportunities and manage your bookings</p>
                </div>
                <div class="flex space-x-4">
                    <button onclick="showRecommendations()" id="recommendations-tab"
                            class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700">
                        <i class="fas fa-search mr-2"></i>Find Opportunities
                    </button>
                    <button onclick="showMyBookings()" id="bookings-tab"
                            class="bg-gray-600 text-white px-6 py-2 rounded-lg hover:bg-gray-700">
                        <i class="fas fa-calendar-check mr-2"></i>My Bookings
                    </button>
                </div>
            </div>
        </div>

        <!-- Recommendations Section -->
        <div id="recommendations-section">
            <div class="mb-6">
                <h3 class="text-2xl font-bold text-gray-900 mb-2">Your Recommendations</h3>
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

        <!-- My Bookings Section -->
        <div id="bookings-section" class="hidden">
            <div class="mb-6">
                <h3 class="text-2xl font-bold text-gray-900 mb-2">My Bookings</h3>
                <p class="text-gray-600">Your confirmed volunteer commitments</p>
            </div>

            <div id="bookings-loading" class="text-center py-12">
                <div class="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p class="text-gray-600">Loading your bookings...</p>
            </div>

            <div id="bookings-container" class="hidden">
                <div id="bookings-list" class="space-y-4">
                    <!-- Bookings will be inserted here -->
                </div>
            </div>

            <div id="no-bookings" class="hidden text-center py-12">
                <i class="fas fa-calendar-times text-gray-400 text-6xl mb-4"></i>
                <h3 class="text-xl font-semibold text-gray-600 mb-2">No Bookings Yet</h3>
                <p class="text-gray-500">You haven't booked any time slots yet. Browse recommendations to get started!</p>
            </div>
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

    <!-- Booking Calendar Modal -->
    <div id="booking-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden z-50 flex items-center justify-center">
        <div class="bg-white rounded-xl shadow-2xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div class="p-6 border-b border-gray-200">
                <div class="flex justify-between items-center">
                    <h3 class="text-2xl font-bold text-gray-900">Book Time Slot</h3>
                    <button onclick="closeBookingModal()" class="text-gray-400 hover:text-gray-600">
                        <i class="fas fa-times text-xl"></i>
                    </button>
                </div>
                <div id="modal-opportunity-info" class="mt-4 text-gray-600"></div>
            </div>

            <div class="p-6">
                <div id="calendar-loading" class="text-center py-8">
                    <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p class="text-gray-600">Loading available time slots...</p>
                </div>

                <div id="calendar-content" class="hidden">
                    <div id="slots-container" class="grid gap-4">
                        <!-- Time slots will be inserted here -->
                    </div>

                    <div id="no-slots" class="hidden text-center py-8">
                        <i class="fas fa-calendar-times text-gray-400 text-4xl mb-4"></i>
                        <h4 class="text-lg font-semibold text-gray-600 mb-2">No Available Slots</h4>
                        <p class="text-gray-500">There are no available time slots for this opportunity at the moment.</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

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
                        <button onclick="showBookingCalendar(${index}, ${rec.opportunity_id || index})"
                                class="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 transition-colors">
                            <i class="fas fa-calendar-plus mr-2"></i>Book Time Slot
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

        function showRecommendations() {
            document.getElementById('recommendations-tab').classList.add('bg-blue-600');
            document.getElementById('recommendations-tab').classList.remove('bg-gray-600');
            document.getElementById('bookings-tab').classList.add('bg-gray-600');
            document.getElementById('bookings-tab').classList.remove('bg-blue-600');

            document.getElementById('recommendations-section').classList.remove('hidden');
            document.getElementById('bookings-section').classList.add('hidden');
        }

        function showMyBookings() {
            document.getElementById('bookings-tab').classList.add('bg-blue-600');
            document.getElementById('bookings-tab').classList.remove('bg-gray-600');
            document.getElementById('recommendations-tab').classList.add('bg-gray-600');
            document.getElementById('recommendations-tab').classList.remove('bg-blue-600');

            document.getElementById('bookings-section').classList.remove('hidden');
            document.getElementById('recommendations-section').classList.add('hidden');

            loadMyBookings();
        }

        async function loadMyBookings() {
            document.getElementById('bookings-loading').classList.remove('hidden');
            document.getElementById('bookings-container').classList.add('hidden');
            document.getElementById('no-bookings').classList.add('hidden');

            try {
                const response = await fetch(`/api/my-bookings/${currentUser}`);
                const bookings = await response.json();

                document.getElementById('bookings-loading').classList.add('hidden');

                if (bookings && bookings.length > 0) {
                    displayBookings(bookings);
                } else {
                    document.getElementById('no-bookings').classList.remove('hidden');
                }
            } catch (error) {
                document.getElementById('bookings-loading').classList.add('hidden');
                document.getElementById('no-bookings').classList.remove('hidden');
                showAlert('Failed to load bookings', 'error');
            }
        }

        function displayBookings(bookings) {
            const container = document.getElementById('bookings-list');
            container.innerHTML = '';

            bookings.forEach((booking) => {
                const bookingElement = document.createElement('div');
                bookingElement.className = 'bg-white rounded-xl shadow-lg p-6 border-l-4 border-green-500';

                const bookingDate = new Date(booking.booking_date);
                const slotDate = new Date(booking.date);
                const today = new Date();
                const isUpcoming = slotDate >= today;

                bookingElement.innerHTML = `
                    <div class="flex justify-between items-start mb-4">
                        <div class="flex-1">
                            <h3 class="text-xl font-bold text-gray-800 mb-2">${booking.ngo_name}</h3>
                            <div class="flex items-center mb-2">
                                <div class="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium">
                                    <i class="fas fa-check-circle mr-1"></i>Confirmed
                                </div>
                                ${isUpcoming ? '<div class="ml-2 bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium">Upcoming</div>' : '<div class="ml-2 bg-gray-100 text-gray-800 px-3 py-1 rounded-full text-sm font-medium">Past</div>'}
                            </div>
                        </div>
                        <div class="text-right">
                            <div class="text-sm text-gray-500">Booked on ${bookingDate.toLocaleDateString()}</div>
                        </div>
                    </div>

                    <p class="text-gray-600 mb-4">${booking.description}</p>

                    <div class="grid md:grid-cols-2 gap-4 mb-4">
                        <div>
                            <div class="text-sm text-gray-500 mb-1">Date & Time</div>
                            <div class="text-sm text-gray-800">
                                <i class="fas fa-calendar mr-1"></i>${slotDate.toLocaleDateString()} at ${booking.start_time} - ${booking.end_time}
                            </div>
                        </div>
                        <div>
                            <div class="text-sm text-gray-500 mb-1">Booking ID</div>
                            <div class="text-sm text-gray-800">#${booking.booking_id}</div>
                        </div>
                    </div>

                    ${booking.notes ? `
                    <div class="mb-4">
                        <div class="text-sm text-gray-500 mb-1">Your Notes</div>
                        <div class="text-sm text-gray-800 italic">${booking.notes}</div>
                    </div>
                    ` : ''}

                    <div class="flex justify-end">
                        <button onclick="cancelBooking(${booking.booking_id})"
                                class="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors text-sm">
                            <i class="fas fa-times mr-1"></i>Cancel Booking
                        </button>
                    </div>
                `;

                container.appendChild(bookingElement);
            });

            document.getElementById('bookings-container').classList.remove('hidden');
        }

        function cancelBooking(bookingId) {
            // For now, just show a message - full cancellation logic would need backend support
            showAlert('Booking cancellation feature coming soon!', 'info');
        }

        async function showBookingCalendar(index, opportunityId) {
            // Get opportunity details from the recommendations
            const recElement = document.getElementById('recommendations-list').children[index];
            const ngoName = recElement.querySelector('h3').textContent;
            const description = recElement.querySelector('p').textContent;

            document.getElementById('modal-opportunity-info').innerHTML = `
                <strong>${ngoName}</strong><br>
                ${description}
            `;

            document.getElementById('booking-modal').classList.remove('hidden');
            document.getElementById('calendar-loading').classList.remove('hidden');
            document.getElementById('calendar-content').classList.add('hidden');

            try {
                const response = await fetch(`/api/slots/${opportunityId}`);
                const slots = await response.json();

                document.getElementById('calendar-loading').classList.add('hidden');

                if (slots && slots.length > 0) {
                    displaySlots(slots, opportunityId);
                } else {
                    document.getElementById('no-slots').classList.remove('hidden');
                }
            } catch (error) {
                document.getElementById('calendar-loading').classList.add('hidden');
                document.getElementById('no-slots').classList.remove('hidden');
                showAlert('Failed to load time slots', 'error');
            }
        }

        function displaySlots(slots, opportunityId) {
            const container = document.getElementById('slots-container');
            container.innerHTML = '';

            slots.forEach((slot) => {
                const slotElement = document.createElement('div');
                const slotDate = new Date(slot.date);
                const isAvailable = slot.available_spots > 0;
                const availabilityClass = isAvailable ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-gray-50 opacity-50';
                const buttonClass = isAvailable ? 'bg-green-600 hover:bg-green-700' : 'bg-gray-400 cursor-not-allowed';

                slotElement.className = `border-2 rounded-lg p-4 ${availabilityClass}`;

                slotElement.innerHTML = `
                    <div class="flex justify-between items-start mb-3">
                        <div>
                            <div class="text-lg font-semibold text-gray-800">
                                ${slotDate.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
                            </div>
                            <div class="text-sm text-gray-600">
                                ${slot.start_time} - ${slot.end_time}
                            </div>
                        </div>
                        <div class="text-right">
                            <div class="text-sm text-gray-500">
                                ${slot.available_spots} spot${slot.available_spots !== 1 ? 's' : ''} left
                            </div>
                            <div class="text-xs text-gray-400">
                                Max: ${slot.max_participants}
                            </div>
                        </div>
                    </div>

                    <div class="flex justify-between items-center">
                        <div class="text-sm text-gray-600">
                            <i class="fas fa-users mr-1"></i>
                            ${slot.current_participants}/${slot.max_participants} participants
                        </div>
                        <button onclick="bookSlot(${slot.slot_id}, ${opportunityId})"
                                ${!isAvailable ? 'disabled' : ''}
                                class="px-4 py-2 rounded-lg text-white text-sm font-medium transition-colors ${buttonClass}">
                            <i class="fas fa-calendar-plus mr-1"></i>${isAvailable ? 'Book Now' : 'Full'}
                        </button>
                    </div>
                `;

                container.appendChild(slotElement);
            });

            document.getElementById('calendar-content').classList.remove('hidden');
        }

        async function bookSlot(slotId, opportunityId) {
            try {
                const response = await fetch('/api/book', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        student_id: currentUser,
                        slot_id: slotId,
                        notes: 'Booked via calendar widget'
                    })
                });

                const data = await response.json();

                if (data.success) {
                    showAlert('Booking confirmed successfully!', 'success');
                    closeBookingModal();
                    // Refresh recommendations to show updated availability
                    loadRecommendations();
                } else {
                    showAlert(data.message || 'Booking failed', 'error');
                }
            } catch (error) {
                showAlert('Network error. Please try again.', 'error');
            }
        }

        function closeBookingModal() {
            document.getElementById('booking-modal').classList.add('hidden');
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

@app.route('/api/slots/<int:opportunity_id>')
def api_get_slots(opportunity_id):
    """Get available time slots for an opportunity"""
    try:
        slots = matching_system.get_available_slots(opportunity_id)
        return jsonify(slots)
    except Exception as e:
        logger.error(f"Get slots error: {e}")
        return jsonify([])

@app.route('/api/book', methods=['POST'])
def api_book_slot():
    """Book a time slot"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        slot_id = data.get('slot_id')
        notes = data.get('notes', '')

        if student_id is None or slot_id is None:
            return jsonify({
                'success': False,
                'message': 'Student ID and slot ID are required'
            })

        result = matching_system.book_slot(student_id, slot_id, notes)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Book slot error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to process booking'
        })

@app.route('/api/my-bookings/<int:student_id>')
def api_get_student_bookings(student_id):
    """Get bookings for a student"""
    try:
        bookings = matching_system.get_student_bookings(student_id)
        return jsonify(bookings)
    except Exception as e:
        logger.error(f"Get student bookings error: {e}")
        return jsonify([])

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