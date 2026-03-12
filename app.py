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

            # Normalize numeric ID/rating columns so matching and filtering are reliable.
            for df, columns in (
                (self.students_df, ['student_id']),
                (self.opportunities_df, ['opportunity_id']),
                (self.interactions_df, ['student_id', 'opportunity_id', 'rating']),
                (self.time_slots_df, ['slot_id', 'opportunity_id', 'max_participants', 'current_participants']),
                (self.bookings_df, ['booking_id', 'student_id', 'slot_id']),
            ):
                for col in columns:
                    if col in df.columns and not df.empty:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                if not df.empty:
                    present_cols = [c for c in columns if c in df.columns]
                    df.dropna(subset=present_cols, inplace=True)

            # Keep ID columns as integers after normalization.
            int_columns = [
                (self.students_df, ['student_id']),
                (self.opportunities_df, ['opportunity_id']),
                (self.interactions_df, ['student_id', 'opportunity_id']),
                (self.time_slots_df, ['slot_id', 'opportunity_id', 'max_participants', 'current_participants']),
                (self.bookings_df, ['booking_id', 'student_id', 'slot_id']),
            ]
            for df, cols in int_columns:
                for col in cols:
                    if col in df.columns and not df.empty:
                        df[col] = df[col].astype(int)

            # Continue IDs from existing data to avoid collisions.
            if not self.opportunities_df.empty:
                self.next_opportunity_id = int(self.opportunities_df['opportunity_id'].max()) + 1
            if not self.time_slots_df.empty:
                self.next_slot_id = int(self.time_slots_df['slot_id'].max()) + 1
            if not self.bookings_df.empty and 'booking_id' in self.bookings_df.columns:
                self.next_booking_id = int(self.bookings_df['booking_id'].max()) + 1

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
    
    def _split_tokens(self, value):
        if value is None or pd.isna(value):
            return set()
        return {tok.strip().lower() for tok in str(value).split(',') if tok.strip()}

    def _get_existing_student_profile(self, student_id):
        row = self.students_df[self.students_df['student_id'] == student_id]
        if row.empty:
            return None
        row = row.iloc[0]
        return {
            'skills': self._split_tokens(row.get('skills', '')),
            'interests': self._split_tokens(row.get('interests', '')),
            'availability': self._split_tokens(row.get('work_calendar', ''))
        }

    def _get_new_student_profile(self, student_id):
        profile = self.new_users.get(student_id)
        if not profile:
            return None
        return {
            'skills': {s.strip().lower() for s in profile.get('skills', []) if str(s).strip()},
            'interests': {i.strip().lower() for i in profile.get('interests', []) if str(i).strip()},
            'availability': set()
        }

    def _get_booked_opportunity_ids(self, student_id):
        try:
            if self.bookings_df is None or self.bookings_df.empty or self.time_slots_df is None:
                return set()

            booked = self.bookings_df[
                (self.bookings_df['student_id'] == student_id) &
                (self.bookings_df['status'] == 'confirmed')
            ]
            if booked.empty:
                return set()

            slot_ids = set(booked['slot_id'].tolist())
            slots = self.time_slots_df[self.time_slots_df['slot_id'].isin(slot_ids)]
            return set(slots['opportunity_id'].tolist())
        except Exception:
            return set()

    def _get_lightfm_scores(self, student_id):
        scores = {}
        try:
            if not (LIGHTFM_AVAILABLE and self.is_trained and student_id in self.user_id_map):
                return scores

            user_internal_id = self.user_id_map[student_id]
            item_ids = list(range(len(self.item_id_map)))
            raw_scores = self.model.predict(user_internal_id, item_ids)

            for item_idx, raw in enumerate(raw_scores):
                item_id = self.reverse_item_map[item_idx]
                # Normalize approximately to 0..1
                scores[item_id] = float(min(1.0, max(0.0, (raw + 2) / 4)))
            return scores
        except Exception as e:
            logger.warning(f"LightFM score generation failed: {e}")
            return {}

    def _interaction_signal(self, student_id, opportunity_id, opp_row):
        if self.interactions_df is None or self.interactions_df.empty:
            return 0.0

        # Direct user-item interaction
        direct = self.interactions_df[
            (self.interactions_df['student_id'] == student_id) &
            (self.interactions_df['opportunity_id'] == opportunity_id)
        ]
        direct_score = 0.0
        if not direct.empty:
            if 'rating' in direct.columns:
                direct_score = min(1.0, max(0.0, direct['rating'].astype(float).mean() / 5.0))
            elif 'interaction' in direct.columns:
                direct_score = min(1.0, max(0.0, direct['interaction'].astype(float).mean() / 5.0))

        # User-ngo affinity
        student_rows = self.interactions_df[self.interactions_df['student_id'] == student_id]
        ngo_affinity = 0.0
        if not student_rows.empty:
            interacted_ids = set(student_rows['opportunity_id'].tolist())
            ngo_name = opp_row['ngo_name']
            ngo_opp_ids = set(
                self.opportunities_df[self.opportunities_df['ngo_name'] == ngo_name]['opportunity_id'].tolist()
            )
            overlap_ids = interacted_ids.intersection(ngo_opp_ids)
            if overlap_ids:
                ngo_rows = student_rows[student_rows['opportunity_id'].isin(overlap_ids)]
                if 'rating' in ngo_rows.columns:
                    ngo_affinity = min(1.0, max(0.0, ngo_rows['rating'].astype(float).mean() / 5.0))
                elif 'interaction' in ngo_rows.columns:
                    ngo_affinity = min(1.0, max(0.0, ngo_rows['interaction'].astype(float).mean() / 5.0))

        # Global opportunity popularity
        global_rows = self.interactions_df[self.interactions_df['opportunity_id'] == opportunity_id]
        popularity = 0.0
        if not global_rows.empty:
            if 'rating' in global_rows.columns:
                popularity = min(1.0, max(0.0, global_rows['rating'].astype(float).mean() / 5.0))
            elif 'interaction' in global_rows.columns:
                popularity = min(1.0, max(0.0, global_rows['interaction'].astype(float).mean() / 5.0))

        return (0.60 * direct_score) + (0.25 * ngo_affinity) + (0.15 * popularity)

    def _content_signal(self, profile, opp_row, nlp_score=0.0):
        user_skills = profile.get('skills', set())
        user_interests = profile.get('interests', set())
        user_days = profile.get('availability', set())

        opp_skills = self._split_tokens(opp_row.get('required_skills', ''))
        opp_days = self._split_tokens(opp_row.get('work_calendar', ''))
        description_words = {
            w.strip(".,:;!?()[]{}\"'").lower()
            for w in str(opp_row.get('description', '')).split()
            if w.strip()
        }

        skill_score = 0.0
        common_skills = set()
        if user_skills and opp_skills:
            common_skills = user_skills.intersection(opp_skills)
            skill_score = len(common_skills) / max(1, len(opp_skills))

        interest_score = 0.0
        interest_matches = set()
        if user_interests:
            interest_matches = {i for i in user_interests if i in description_words}
            interest_score = len(interest_matches) / max(1, len(user_interests))

        availability_score = 0.0
        common_days = set()
        if user_days and opp_days:
            common_days = user_days.intersection(opp_days)
            availability_score = len(common_days) / max(1, len(opp_days))

        importance = str(opp_row.get('importance_level', 'medium')).strip().lower()
        importance_bonus = {'emergency': 1.0, 'high': 0.8, 'medium': 0.6, 'standard': 0.5, 'low': 0.35}
        importance_score = importance_bonus.get(importance, 0.5)

        total = (
            0.30 * skill_score +
            0.15 * interest_score +
            0.15 * availability_score +
            0.10 * importance_score +
            0.30 * nlp_score
        )

        reasons = []
        if nlp_score > 0.1:
            reasons.append(f"AI Semantic Match: {int(nlp_score * 100)}%")
        if common_skills:
            reasons.append(f"Skill overlap: {', '.join(sorted(common_skills)[:3])}")
        if interest_matches:
            reasons.append(f"Interest match: {', '.join(sorted(interest_matches)[:2])}")
        if common_days:
            reasons.append(f"Schedule fit: {', '.join(sorted(common_days)[:2])}")
        if not reasons:
            reasons.append("General profile and priority match")

        return float(min(1.0, max(0.0, total))), reasons

    def _hybrid_recommendations(self, student_id, profile, n_recommendations):
        recommendations = []
        booked_opportunities = self._get_booked_opportunity_ids(student_id)
        lightfm_scores = self._get_lightfm_scores(student_id)
        has_interactions = not self.interactions_df[self.interactions_df['student_id'] == student_id].empty

        # Pre-calculate NLP semantic scores for all opportunities
        nlp_scores = {}
        if SKLEARN_AVAILABLE and not self.opportunities_df.empty:
            try:
                user_text = " ".join(profile.get('skills', [])) + " " + " ".join(profile.get('interests', []))
                if user_text.strip():
                    opp_texts = []
                    opp_ids = []
                    for _, opp in self.opportunities_df.iterrows():
                        opp_ids.append(opp['opportunity_id'])
                        opp_text = str(opp.get('description', '')) + " " + str(opp.get('required_skills', ''))
                        opp_texts.append(opp_text)
                    
                    vectorizer = TfidfVectorizer(stop_words='english')
                    tfidf_matrix = vectorizer.fit_transform([user_text] + opp_texts)
                    cosine_sims = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
                    for opp_id, sim in zip(opp_ids, cosine_sims):
                        nlp_scores[opp_id] = float(sim)
            except Exception as e:
                logger.warning(f"NLP score computation failed: {e}")

        # Calculate popularity for cold-start users
        popularity_scores = {}
        if not has_interactions and self.interactions_df is not None and not self.interactions_df.empty:
            opp_counts = self.interactions_df['opportunity_id'].value_counts()
            max_count = opp_counts.max()
            if max_count > 0:
                for opp_id, count in opp_counts.items():
                    popularity_scores[opp_id] = count / max_count

        for _, opp in self.opportunities_df.iterrows():
            opp_id = opp['opportunity_id']

            # Exclude opportunities already booked by this student
            if opp_id in booked_opportunities:
                continue

            content_score, reasons = self._content_signal(profile, opp, nlp_scores.get(opp_id, 0.0))
            interaction_score = self._interaction_signal(student_id, opp_id, opp) if has_interactions else 0.0
            lightfm_score = lightfm_scores.get(opp_id, 0.0)

            if has_interactions:
                if content_score == 0.0 and lightfm_score == 0.0:
                    pop_score = popularity_scores.get(opp_id, 0.0) if not popularity_scores else \
                                (self.interactions_df['opportunity_id'].value_counts().get(opp_id, 0.0) / 
                                 max(1, self.interactions_df['opportunity_id'].value_counts().max()))
                    final_score = (0.50 * interaction_score) + (0.50 * pop_score)
                    if pop_score > 0.1:
                        reasons.append("Trending opportunity (Popular)")
                else:
                    final_score = (0.50 * interaction_score) + (0.35 * content_score) + (0.15 * lightfm_score)
            else:
                pop_score = popularity_scores.get(opp_id, 0.0)
                final_score = (0.70 * content_score) + (0.15 * lightfm_score) + (0.15 * pop_score)
                if pop_score > 0.2:
                    reasons.append("Trending opportunity (Popular)")

            # Ensure dummy users aren't left with 0% match if they have no direct connections
            if final_score == 0.0:
                pop_score = popularity_scores.get(opp_id, 0.0) if not popularity_scores else \
                            (self.interactions_df['opportunity_id'].value_counts().get(opp_id, 0.0) / 
                             max(1, self.interactions_df['opportunity_id'].value_counts().max()))
                final_score = 0.15 * pop_score
                if pop_score > 0.1:
                    reasons.append("Trending opportunity (Popular)")

            recommendations.append({
                'opportunity_id': int(opp_id),
                'ngo_name': opp['ngo_name'],
                'description': opp['description'],
                'required_skills': opp['required_skills'],
                'importance_level': opp['importance_level'],
                'work_calendar': opp['work_calendar'],
                'score': float(min(1.0, max(0.0, final_score))),
                'match_percentage': int(round(min(1.0, max(0.0, final_score)) * 100)),
                'reasons': reasons,
                'score_breakdown': {
                    'interaction': round(interaction_score, 3),
                    'content': round(content_score, 3),
                    'lightfm': round(lightfm_score, 3)
                }
            })

        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:n_recommendations]

    def get_recommendations(self, student_id, n_recommendations=5):
        """Get hybrid recommendations for a student"""
        try:
            if student_id in self.new_users:
                profile = self._get_new_student_profile(student_id)
                return self._hybrid_recommendations(student_id, profile, n_recommendations)

            if student_id not in self.students_df['student_id'].tolist():
                return []

            profile = self._get_existing_student_profile(student_id)
            return self._hybrid_recommendations(student_id, profile, n_recommendations)
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return []
            
    def _get_lightfm_recommendations(self, student_id, n_recommendations):
        """Compatibility wrapper: now uses hybrid recommendations."""
        profile = self._get_existing_student_profile(student_id)
        if not profile:
            return []
        return self._hybrid_recommendations(student_id, profile, n_recommendations)
            
    def _get_content_based_recommendations(self, student_id, n_recommendations):
        """Compatibility wrapper: now uses hybrid recommendations for new users."""
        profile = self._get_new_student_profile(student_id)
        if not profile:
            return []
        return self._hybrid_recommendations(student_id, profile, n_recommendations)
            
    def _get_fallback_recommendations(self, student_id, n_recommendations):
        """Compatibility wrapper for older callers."""
        return self.get_recommendations(student_id, n_recommendations)
            
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
<title>VolunteerIQ – AI Volunteer Matching</title>
<script src="https://cdn.tailwindcss.com"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root{
  --bg:#F6F2ED; --surface:#FFFFFF; --text:#1E1B16; --text-muted:#6B6355;
  --primary:#C65A2E; --primary-dark:#A84422; --primary-light:#F3E4DC;
  --accent:#2A6F6A; --accent-light:#E0F0EF;
  --border:#E7DDD2; --shadow:rgba(30,27,22,.1);
  --r:12px;--r-lg:18px;--t:.18s ease;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);margin:0;overflow-x:hidden;line-height:1.6}
h1,h2,h3,h4{font-family:'Playfair Display',serif;line-height:1.2}

/* noise texture */
body::before{content:'';position:fixed;inset:0;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");pointer-events:none;z-index:0;opacity:.6}

::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:var(--border)}
::-webkit-scrollbar-thumb{background:#C4B9AC;border-radius:99px}

/* animations */
@keyframes fadeUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
@keyframes stagger{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes slideInRight{from{opacity:0;transform:translateX(40px)}to{opacity:1;transform:translateX(0)}}
.fade-up{animation:fadeUp .55s ease both}
.fade-in{animation:fadeIn .4s ease both}
.spin{animation:spin .8s linear infinite}
.stagger>*{animation:stagger .5s ease both}
.stagger>*:nth-child(1){animation-delay:.05s} .stagger>*:nth-child(2){animation-delay:.12s}
.stagger>*:nth-child(3){animation-delay:.19s} .stagger>*:nth-child(4){animation-delay:.26s}
.stagger>*:nth-child(5){animation-delay:.33s} .stagger>*:nth-child(6){animation-delay:.4s}

/* buttons */
.btn-primary{display:inline-flex;align-items:center;gap:8px;padding:12px 28px;background:var(--primary);color:#fff;font-weight:600;font-size:.9rem;border-radius:99px;border:none;cursor:pointer;transition:var(--t);font-family:'Inter',sans-serif}
.btn-primary:hover{background:var(--primary-dark);transform:translateY(-1px);box-shadow:0 4px 16px rgba(198,90,46,.3)}
.btn-primary.sm{padding:8px 20px;font-size:.82rem}
.btn-accent{display:inline-flex;align-items:center;gap:8px;padding:12px 28px;background:var(--accent);color:#fff;font-weight:600;font-size:.9rem;border-radius:99px;border:none;cursor:pointer;transition:var(--t);font-family:'Inter',sans-serif}
.btn-accent:hover{background:#1E5854;transform:translateY(-1px);box-shadow:0 4px 16px rgba(42,111,106,.25)}
.btn-accent.sm{padding:8px 20px;font-size:.82rem}
.btn-outline{display:inline-flex;align-items:center;gap:8px;padding:11px 24px;background:transparent;color:var(--text);font-weight:600;font-size:.88rem;border-radius:99px;border:1.5px solid var(--border);cursor:pointer;transition:var(--t);font-family:'Inter',sans-serif}
.btn-outline:hover{border-color:var(--primary);color:var(--primary);background:var(--primary-light)}
.btn-outline.sm{padding:8px 18px;font-size:.8rem}
.btn-ghost{display:inline-flex;align-items:center;gap:6px;padding:8px 14px;background:transparent;color:var(--text-muted);font-size:.82rem;font-weight:500;border-radius:8px;border:none;cursor:pointer;transition:var(--t)}
.btn-ghost:hover{background:var(--border);color:var(--text)}

/* cards */
.card{background:var(--surface);border:1.5px solid var(--border);border-radius:var(--r-lg);box-shadow:0 2px 12px var(--shadow);transition:var(--t);overflow:hidden}
.card:hover{box-shadow:0 6px 28px rgba(30,27,22,.13);transform:translateY(-2px)}
.card-flat{background:var(--surface);border:1.5px solid var(--border);border-radius:var(--r);padding:20px}

/* nav */
.nav-link{display:flex;align-items:center;gap:10px;padding:10px 14px;border-radius:10px;color:var(--text-muted);font-size:.875rem;font-weight:500;transition:var(--t);cursor:pointer;text-decoration:none;border:1.5px solid transparent;white-space:nowrap;margin-bottom:4px}
.nav-link:hover{color:var(--text);background:var(--primary-light);border-color:var(--border)}
.nav-link.active{color:var(--primary);background:var(--primary-light);border-color:rgba(198,90,46,.25);font-weight:600}
.nav-link .icon{width:18px;text-align:center;font-size:.85rem}
.nav-section{font-size:.65rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#AAA098;padding:0 14px;margin:18px 0 6px}

/* tab */
.tab-pane{display:none} .tab-pane.active{display:block}

/* badge */
.badge{display:inline-flex;align-items:center;gap:4px;padding:3px 9px;border-radius:99px;font-size:.7rem;font-weight:600;font-family:'Inter',sans-serif}
.badge-primary{background:var(--primary-light);color:var(--primary);border:1px solid rgba(198,90,46,.2)}
.badge-accent{background:var(--accent-light);color:var(--accent);border:1px solid rgba(42,111,106,.2)}
.badge-green{background:#E6F4EA;color:#2D7A3A;border:1px solid rgba(45,122,58,.2)}
.badge-amber{background:#FDF3E0;color:#975F0A;border:1px solid rgba(151,95,10,.2)}
.badge-red{background:#FDEAEA;color:#C0392B;border:1px solid rgba(192,57,43,.2)}
.badge-neutral{background:var(--border);color:var(--text-muted);border:1px solid transparent}

/* inputs */
.inp{background:var(--surface);border:1.5px solid var(--border);border-radius:var(--r);padding:10px 14px;color:var(--text);font-size:.875rem;width:100%;outline:none;transition:var(--t);font-family:'Inter',sans-serif}
.inp:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(42,111,106,.12)}
.inp::placeholder{color:#B8B0A5}
select.inp option{background:var(--surface);color:var(--text)}

/* stat chip */
.stat-chip{background:var(--surface);border:1.5px solid var(--border);border-radius:var(--r);padding:16px 20px;text-align:center;transition:var(--t)}
.stat-chip:hover{border-color:var(--primary);box-shadow:0 4px 16px var(--shadow)}

/* progress */
.prog-bar{height:5px;background:var(--border);border-radius:99px;overflow:hidden}
.prog-primary{height:100%;border-radius:99px;background:var(--primary);transition:width .7s ease}
.prog-accent{height:100%;border-radius:99px;background:var(--accent);transition:width .7s ease}

/* section label */
.section-lbl{font-size:.68rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--text-muted)}

/* divider */
.divider{height:1.5px;background:var(--border);margin:24px 0}

/* modal / drawer */
.modal-bg{display:none;position:fixed;inset:0;background:rgba(30,27,22,.45);z-index:100;align-items:center;justify-content:center;backdrop-filter:blur(4px)}
.modal-bg.open{display:flex}
.modal-box{background:var(--surface);border:1.5px solid var(--border);border-radius:var(--r-lg);padding:32px;width:90%;max-width:440px;box-shadow:0 24px 60px rgba(30,27,22,.2);animation:fadeUp .25s ease}

/* table */
.data-table{width:100%;border-collapse:collapse}
.data-table th{padding:10px 14px;font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--text-muted);border-bottom:1.5px solid var(--border);text-align:left;background:var(--bg)}
.data-table td{padding:12px 14px;font-size:.84rem;border-bottom:1px solid var(--border);vertical-align:middle}
.data-table tbody tr:hover td{background:#FDFAF7}

/* alert */
.alert-item{display:flex;align-items:center;gap:10px;padding:12px 18px;border-radius:10px;font-size:.84rem;font-weight:500;animation:fadeUp .3s ease both;box-shadow:0 4px 20px rgba(30,27,22,.15)}

/* booking slot */
.slot-item{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-radius:var(--r);border:1.5px solid var(--border);transition:var(--t)}
.slot-item:hover{border-color:var(--accent);background:var(--accent-light)}

/* match card accent bar */
.match-card-top{height:4px;width:100%;background:linear-gradient(90deg,var(--primary),var(--accent))}

/* sparkline */
.spark-wrap{width:80px;height:28px}
</style>
</head>
<body class="relative z-10 min-h-screen">
<div id="alert-container" class="fixed top-4 right-4 z-[300] flex flex-col gap-2 w-80"></div>

<!-- ═══════════════ PUBLIC AREA ═══════════════ -->
<div id="public-area">

<!-- NAV -->
<nav class="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-3" style="background:rgba(246,242,237,.95);backdrop-filter:blur(12px);border-bottom:1.5px solid var(--border)">
  <div class="flex items-center gap-2">
    <div class="w-8 h-8 rounded-lg flex items-center justify-center" style="background:var(--primary)">
      <i class="fas fa-bolt text-white text-sm"></i>
    </div>
    <span style="font-family:'Playfair Display',serif;font-weight:700;font-size:1.05rem;color:var(--text)">VolunteerIQ</span>
  </div>
  <div class="hidden md:flex items-center gap-6 text-sm font-medium" style="color:var(--text-muted)">
    <a href="#how" class="hover:text-[#C65A2E] transition-colors">How it works</a>
    <a href="#" onclick="openLoginModal('student')" class="hover:text-[#C65A2E] transition-colors">Sign in</a>
  </div>
  <button onclick="openLoginModal('student')" class="btn-primary sm">Get Started <i class="fas fa-arrow-right text-xs"></i></button>
</nav>

<!-- HERO -->
<section class="relative pt-28 pb-16 px-6 overflow-hidden">
  <div class="absolute inset-0 pointer-events-none">
    <div class="absolute right-0 top-0 w-96 h-96 rounded-full" style="background:radial-gradient(circle,rgba(198,90,46,.08) 0%,transparent 70%);filter:blur(60px)"></div>
    <div class="absolute left-0 bottom-0 w-80 h-80 rounded-full" style="background:radial-gradient(circle,rgba(42,111,106,.07) 0%,transparent 70%);filter:blur(60px)"></div>
  </div>
  <div class="max-w-5xl mx-auto relative z-10">
    <div class="text-center mb-14">
      <div class="fade-up inline-flex items-center gap-2 px-4 py-2 rounded-full mb-6" style="background:var(--primary-light);border:1.5px solid rgba(198,90,46,.2)">
        <span class="w-2 h-2 rounded-full" style="background:var(--primary)"></span>
        <span class="text-xs font-semibold" style="color:var(--primary)">AI-Powered · Live · 100+ NGOs</span>
      </div>
      <h1 class="fade-up text-5xl md:text-6xl mb-5" style="animation-delay:.07s;color:var(--text)">
        Match students with<br><span style="color:var(--primary)">meaningful</span> volunteer work.
      </h1>
      <p class="fade-up text-lg max-w-xl mx-auto mb-10 leading-relaxed" style="color:var(--text-muted);animation-delay:.14s">
        AI reads your skills and interests, then surfaces the best opportunities — with transparent explanations you can actually trust.
      </p>
      <!-- Role decision cards -->
      <div class="fade-up flex flex-col sm:flex-row gap-5 justify-center" style="animation-delay:.21s">
        <button onclick="openLoginModal('student')" class="card p-6 text-left group cursor-pointer w-full sm:w-64" style="border-color:rgba(198,90,46,.25)">
          <div class="w-10 h-10 rounded-xl flex items-center justify-center mb-4" style="background:var(--primary-light)"><i class="fas fa-graduation-cap" style="color:var(--primary)"></i></div>
          <h3 class="text-base font-bold mb-1" style="font-family:'Playfair Display',serif">I'm a Student</h3>
          <p class="text-sm mb-4" style="color:var(--text-muted)">Get AI-matched to NGOs that need your exact skills.</p>
          <span class="btn-primary sm w-full justify-center">Find Matches <i class="fas fa-arrow-right text-xs"></i></span>
        </button>
        <button onclick="openLoginModal('ngo')" class="card p-6 text-left group cursor-pointer w-full sm:w-64" style="border-color:rgba(42,111,106,.25)">
          <div class="w-10 h-10 rounded-xl flex items-center justify-center mb-4" style="background:var(--accent-light)"><i class="fas fa-building" style="color:var(--accent)"></i></div>
          <h3 class="text-base font-bold mb-1" style="font-family:'Playfair Display',serif">I'm an NGO</h3>
          <p class="text-sm mb-4" style="color:var(--text-muted)">Post opportunities and see ranked volunteer recommendations.</p>
          <span class="btn-accent sm w-full justify-center">NGO Portal <i class="fas fa-arrow-right text-xs"></i></span>
        </button>
      </div>
    </div>

    <!-- Trust row -->
    <div class="flex flex-wrap justify-center items-center gap-8 mb-14 opacity-50">
      <span class="text-sm font-semibold" style="color:var(--text-muted)">Trusted by:</span>
      <span style="font-family:'Playfair Display',serif;font-size:.95rem;font-weight:700">GreenCorps</span>
      <span style="font-family:'Playfair Display',serif;font-size:.95rem;font-weight:700">EduReach</span>
      <span style="font-family:'Playfair Display',serif;font-size:.95rem;font-weight:700">CareFirst</span>
      <span style="font-family:'Playfair Display',serif;font-size:.95rem;font-weight:700">GlobalAid</span>
      <span style="font-family:'Playfair Display',serif;font-size:.95rem;font-weight:700">SkillBridge</span>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <div class="stat-chip"><div class="text-3xl font-bold mb-1" style="font-family:'Playfair Display',serif;color:var(--primary)">100+</div><div class="text-xs" style="color:var(--text-muted)">Students Matched</div></div>
      <div class="stat-chip"><div class="text-3xl font-bold mb-1" style="font-family:'Playfair Display',serif;color:var(--accent)">100+</div><div class="text-xs" style="color:var(--text-muted)">Opportunities Live</div></div>
      <div class="stat-chip"><div class="text-3xl font-bold mb-1" style="font-family:'Playfair Display',serif;color:var(--primary)">671</div><div class="text-xs" style="color:var(--text-muted)">Interactions</div></div>
      <div class="stat-chip"><div class="text-3xl font-bold mb-1" style="font-family:'Playfair Display',serif;color:var(--accent)">92%</div><div class="text-xs" style="color:var(--text-muted)">Match Accuracy</div></div>
    </div>
  </div>
</section>

<!-- HOW IT WORKS -->
<section id="how" class="py-20 px-6" style="background:var(--surface);border-top:1.5px solid var(--border)">
  <div class="max-w-4xl mx-auto">
    <div class="text-center mb-12">
      <p class="section-lbl mb-2">Process</p>
      <h2 class="text-4xl" style="color:var(--text)">Three steps to your match</h2>
    </div>
    <div class="grid md:grid-cols-3 gap-6 stagger">
      <div class="card-flat">
        <div class="w-10 h-10 rounded-xl flex items-center justify-center mb-4" style="background:var(--primary-light)"><span style="font-family:'Playfair Display',serif;font-weight:700;color:var(--primary)">1</span></div>
        <h3 class="text-lg mb-2" style="color:var(--text)">Sign in</h3>
        <p style="color:var(--text-muted);font-size:.875rem;line-height:1.7">Choose your role — student or NGO — and enter your ID or email.</p>
      </div>
      <div class="card-flat" style="border-color:rgba(198,90,46,.2)">
        <div class="w-10 h-10 rounded-xl flex items-center justify-center mb-4" style="background:var(--primary-light)"><span style="font-family:'Playfair Display',serif;font-weight:700;color:var(--primary)">2</span></div>
        <h3 class="text-lg mb-2" style="color:var(--text)">AI matches you</h3>
        <p style="color:var(--text-muted);font-size:.875rem;line-height:1.7">Hybrid TF-IDF + collaborative filtering ranks every opportunity by skill overlap and peer behaviour.</p>
      </div>
      <div class="card-flat">
        <div class="w-10 h-10 rounded-xl flex items-center justify-center mb-4" style="background:var(--accent-light)"><span style="font-family:'Playfair Display',serif;font-weight:700;color:var(--accent)">3</span></div>
        <h3 class="text-lg mb-2" style="color:var(--text)">Book & contribute</h3>
        <p style="color:var(--text-muted);font-size:.875rem;line-height:1.7">Pick a slot, confirm your booking, and track impact hours — all in one dashboard.</p>
      </div>
    </div>
  </div>
</section>

</div><!-- /public-area -->

<!-- LOGIN MODAL -->
<div id="login-modal" class="modal-bg" onclick="if(event.target===this)closeLoginModal()">
  <div class="modal-box">
    <div class="flex justify-between items-start mb-6">
      <div>
        <p class="section-lbl mb-1" id="modal-login-sup">Access Platform</p>
        <h3 id="modal-login-title" style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;color:var(--text)">Student Access</h3>
        <p id="modal-login-desc" class="text-sm mt-1" style="color:var(--text-muted)">Enter your Demo Student ID.</p>
      </div>
      <button onclick="closeLoginModal()" class="btn-ghost w-8 h-8 flex items-center justify-center rounded-lg" style="padding:0;background:var(--bg)"><i class="fas fa-times text-xs"></i></button>
    </div>
    
    <div id="login-student-form">
      <label class="section-lbl mb-2 block">Student ID</label>
      <input id="demo-student-id" type="number" min="1" max="100" value="1" placeholder="e.g. 1" class="inp mb-5 text-lg font-semibold py-3">
      <button onclick="loginAs('student')" class="btn-primary w-full justify-center py-3.5"><i class="fas fa-sign-in-alt mt-0.5"></i>Login</button>
      <div class="mt-4 text-center">
        <button onclick="showRegisterForm()" class="btn-ghost text-xs">New student? <span style="color:var(--primary);font-weight:700">Register here</span></button>
      </div>
    </div>
    
    <div id="login-ngo-form" class="hidden">
      <label class="section-lbl mb-2 block">NGO Admin Email</label>
      <input id="demo-ngo-email" type="email" value="admin@ngo1.org" placeholder="admin@ngo.org" class="inp mb-5 py-3">
      <button onclick="loginAs('ngo')" class="btn-accent w-full justify-center py-3.5"><i class="fas fa-building mt-0.5"></i>NGO Dashboard</button>
    </div>

    <div id="login-register-form" class="hidden">
      <div class="mb-4"><label class="section-lbl mb-1 block">Full Name</label><input id="reg-name" type="text" placeholder="Jane Doe" class="inp py-2"></div>
      <div class="mb-4"><label class="section-lbl mb-1 block">Email</label><input id="reg-email" type="email" placeholder="jane@university.edu" class="inp py-2"></div>
      <div class="mb-4"><label class="section-lbl mb-1 block">University</label><input id="reg-uni" type="text" placeholder="State University" class="inp py-2"></div>
      <div class="grid grid-cols-2 gap-3 mb-5">
        <div><label class="section-lbl mb-1 block">Skills (csv)</label><input id="reg-skills" type="text" placeholder="Python, Design" class="inp py-2 text-xs"></div>
        <div><label class="section-lbl mb-1 block">Interests (csv)</label><input id="reg-interests" type="text" placeholder="Education, Tech" class="inp py-2 text-xs"></div>
      </div>
      <button onclick="registerStudent()" class="btn-primary w-full justify-center py-3.5"><i class="fas fa-user-plus mt-0.5"></i> Create Account</button>
      <div class="mt-4 text-center">
        <button onclick="openLoginModal('student')" class="btn-ghost text-xs">Back to Login</button>
      </div>
    </div>
  </div>
</div>

<!-- SIDEBAR -->
<div id="sidebar" class="hidden fixed left-0 top-0 bottom-0 z-50 flex flex-col" style="width:230px;background:var(--surface);border-right:1.5px solid var(--border)">
  <div class="px-5 py-4 flex items-center gap-2" style="border-bottom:1.5px solid var(--border)">
    <div class="w-7 h-7 rounded-lg flex items-center justify-center" style="background:var(--primary)"><i class="fas fa-bolt text-white text-xs"></i></div>
    <span style="font-family:'Playfair Display',serif;font-weight:700;font-size:.95rem;color:var(--text)">VolunteerIQ</span>
  </div>
  <div class="px-4 py-3" style="border-bottom:1.5px solid var(--border)">
    <div class="flex items-center gap-3 px-3 py-2 rounded-xl" style="background:var(--bg)">
      <div id="sidebar-avatar" class="w-8 h-8 rounded-xl flex items-center justify-center font-bold text-xs text-white flex-shrink-0" style="background:var(--primary)">S</div>
      <div class="overflow-hidden">
        <p id="sidebar-name" class="text-sm font-semibold truncate" style="color:var(--text)">Student</p>
        <p id="sidebar-role" class="text-xs" style="color:var(--text-muted)">Volunteer</p>
      </div>
    </div>
  </div>
  <div class="flex-1 overflow-y-auto px-3 py-3">
    <div id="nav-student" class="hidden">
      <p class="nav-section">My Journey</p>
      <a href="#" onclick="switchTab('dashboard')" class="nav-link active" data-tab="dashboard"><span class="icon"><i class="fas fa-th-large"></i></span>Overview</a>
      <a href="#" onclick="switchTab('ai-matches')" class="nav-link" data-tab="ai-matches"><span class="icon"><i class="fas fa-magic"></i></span>AI Matches<span id="match-badge" class="ml-auto badge badge-primary" style="font-size:.6rem">5</span></a>
      <a href="#" onclick="switchTab('my-schedule')" class="nav-link" data-tab="my-schedule"><span class="icon"><i class="fas fa-calendar-check"></i></span>My Schedule</a>
      <p class="nav-section">Explore</p>
      <a href="#" onclick="switchTab('explore')" class="nav-link" data-tab="explore"><span class="icon"><i class="fas fa-search"></i></span>Opportunities</a>
      <a href="#" onclick="switchTab('analytics')" class="nav-link" data-tab="analytics"><span class="icon"><i class="fas fa-chart-area"></i></span>My Impact</a>
      <a href="#" onclick="switchTab('system-overview')" class="nav-link" data-tab="system-overview"><span class="icon"><i class="fas fa-tachometer-alt"></i></span>Platform</a>
      <a href="#" onclick="switchTab('student-explorer')" class="nav-link" data-tab="student-explorer"><span class="icon"><i class="fas fa-users"></i></span>Students</a>
    </div>
    <div id="nav-ngo" class="hidden">
      <p class="nav-section">NGO Portal</p>
      <a href="#" onclick="switchTab('ngo-dashboard')" class="nav-link active" data-tab="ngo-dashboard"><span class="icon"><i class="fas fa-chart-pie"></i></span>Dashboard</a>
      <a href="#" onclick="switchTab('ngo-manage')" class="nav-link" data-tab="ngo-manage"><span class="icon"><i class="fas fa-plus-circle"></i></span>Post Opportunity</a>
    </div>
  </div>
  <div class="px-3 py-4" style="border-top:1.5px solid var(--border)">
    <button onclick="logout()" class="nav-link w-full text-red-600 hover:bg-red-50" style="border-color:transparent"><span class="icon"><i class="fas fa-sign-out-alt"></i></span>Sign out</button>
  </div>
</div>

<!-- TOP BAR -->
<div id="top-header" class="hidden fixed top-0 z-40 flex items-center justify-between px-6 py-3" style="left:230px;right:0;background:rgba(246,242,237,.95);backdrop-filter:blur(12px);border-bottom:1.5px solid var(--border)">
  <div id="topbar-title" style="font-family:'Playfair Display',serif;font-size:1rem;font-weight:700;color:var(--text)">Overview</div>
  <div class="flex items-center gap-3">
    <div class="relative hidden md:block"><i class="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-xs" style="color:var(--text-muted)"></i><input type="text" placeholder="Search…" class="inp pl-8 py-2 text-xs" style="width:180px;border-radius:8px"></div>
    <div id="topbar-avatar" class="w-8 h-8 rounded-xl flex items-center justify-center font-bold text-xs text-white" style="background:var(--primary)">S</div>
  </div>
</div>

<!-- MAIN -->
<div id="private-area" class="hidden" style="margin-left:230px;padding-top:56px;min-height:100vh;background:var(--bg)">
<div class="p-6 pb-20 max-w-[1100px]">

<!-- ════ STUDENT TABS ════ -->

<!-- DASHBOARD -->
<div id="tab-dashboard" class="tab-pane fade-in">
  <!-- Profile banner -->
  <div class="card mb-5 overflow-hidden">
    <div class="match-card-top"></div>
    <div class="p-6 flex flex-col md:flex-row justify-between gap-5">
      <div>
        <p class="section-lbl mb-1">Welcome back</p>
        <h2 id="profile-name" style="font-family:'Playfair Display',serif;font-size:1.7rem;font-weight:700;color:var(--text);margin-bottom:4px">Student</h2>
        <div class="flex flex-wrap items-center gap-3 text-xs mb-4" style="color:var(--text-muted)">
          <span><i class="fas fa-envelope mr-1"></i><span id="profile-email">—</span></span>
          <span>·</span>
          <span><i class="fas fa-university mr-1"></i><span id="profile-university">—</span></span>
        </div>
        <div class="flex flex-wrap gap-2" id="profile-skills"></div>
      </div>
      <div class="card-flat text-center min-w-[150px]" style="background:var(--bg)">
        <p class="section-lbl mb-3">Interests</p>
        <div class="flex flex-wrap gap-1.5 justify-center" id="profile-interests"></div>
      </div>
    </div>
  </div>

  <!-- 3-step guide -->
  <div class="card-flat mb-5">
    <p class="section-lbl mb-4">Your volunteer journey</p>
    <div class="grid grid-cols-3 gap-4">
      <button onclick="switchTab('ai-matches')" class="text-left p-4 rounded-xl transition-all hover:-translate-y-1" style="background:var(--primary-light);border:1.5px solid rgba(198,90,46,.2)">
        <span class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white mb-3 block" style="background:var(--primary)">1</span>
        <i class="fas fa-magic mb-2 block" style="color:var(--primary);font-size:1.2rem"></i>
        <p class="font-semibold text-sm mb-1 mt-1" style="color:var(--text)">View AI Matches</p>
        <p class="text-xs" style="color:var(--text-muted)">Ranked by skill overlap</p>
      </button>
      <div class="text-left p-4 rounded-xl" style="background:var(--bg);border:1.5px solid var(--border)">
        <span class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white mb-3 block" style="background:var(--text-muted)">2</span>
        <i class="fas fa-calendar-plus mb-2 block" style="color:var(--text-muted);font-size:1.2rem"></i>
        <p class="font-semibold text-sm mb-1 mt-1" style="color:var(--text)">Book a Slot</p>
        <p class="text-xs" style="color:var(--text-muted)">Click "Book Slot" anywhere</p>
      </div>
      <button onclick="switchTab('my-schedule')" class="text-left p-4 rounded-xl transition-all hover:-translate-y-1" style="background:var(--accent-light);border:1.5px solid rgba(42,111,106,.2)">
        <span class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white mb-3 block" style="background:var(--accent)">3</span>
        <i class="fas fa-tasks mb-2 block" style="color:var(--accent);font-size:1.2rem"></i>
        <p class="font-semibold text-sm mb-1 mt-1" style="color:var(--text)">Track Schedule</p>
        <p class="text-xs" style="color:var(--text-muted)">Confirmed bookings & hours</p>
      </button>
    </div>
  </div>

  <!-- stats -->
  <div class="grid grid-cols-3 gap-4 mb-5">
    <button onclick="switchTab('ai-matches')" class="stat-chip text-left">
      <div class="flex items-center gap-3"><div class="w-10 h-10 rounded-xl flex items-center justify-center" style="background:var(--primary-light)"><i class="fas fa-fire text-lg" style="color:var(--primary)"></i></div><div><div id="dash-match-count" style="font-family:'Playfair Display',serif;font-size:1.5rem;font-weight:700;color:var(--primary)">5</div><div class="text-xs" style="color:var(--text-muted)">AI Matches</div></div></div>
    </button>
    <button onclick="switchTab('my-schedule')" class="stat-chip text-left">
      <div class="flex items-center gap-3"><div class="w-10 h-10 rounded-xl flex items-center justify-center" style="background:var(--accent-light)"><i class="fas fa-calendar-check text-lg" style="color:var(--accent)"></i></div><div><div id="dash-booking-count" style="font-family:'Playfair Display',serif;font-size:1.5rem;font-weight:700;color:var(--accent)">—</div><div class="text-xs" style="color:var(--text-muted)">Bookings</div></div></div>
    </button>
    <button onclick="switchTab('analytics')" class="stat-chip text-left">
      <div class="flex items-center gap-3"><div class="w-10 h-10 rounded-xl flex items-center justify-center" style="background:var(--border)"><i class="fas fa-award text-lg" style="color:var(--text-muted)"></i></div><div><div id="dash-impact-hours" style="font-family:'Playfair Display',serif;font-size:1.5rem;font-weight:700;color:var(--text)">—</div><div class="text-xs" style="color:var(--text-muted)">Impact Hours</div></div></div>
    </button>
  </div>

  <!-- next action -->
  <div id="next-action-banner" class="card-flat flex items-center gap-4" style="border-color:rgba(198,90,46,.25);background:var(--primary-light)">
    <div class="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0" style="background:var(--primary)"><i class="fas fa-bolt text-white text-xs"></i></div>
    <div class="flex-1">
      <p class="font-semibold text-sm mb-0.5">Recommended next step</p>
      <p id="next-action-text" class="text-xs" style="color:var(--text-muted)">Your AI Matches are ready — go book one!</p>
    </div>
    <button id="next-action-btn" onclick="switchTab('ai-matches')" class="btn-primary sm flex-shrink-0">Go Now</button>
  </div>
</div>

<!-- AI MATCHES -->
<div id="tab-ai-matches" class="tab-pane fade-in">
  <div class="flex justify-between items-center mb-5">
    <div><h2 style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;color:var(--text);margin-bottom:2px">AI Recommendations</h2><p class="text-sm" style="color:var(--text-muted)">TF-IDF semantic matching + collaborative signals</p></div>
    <button onclick="loadRecommendations()" class="btn-ghost"><i class="fas fa-sync-alt text-xs"></i> Refresh</button>
  </div>
  <div id="loading" class="text-center py-20">
    <div class="w-10 h-10 rounded-full border-4 mx-auto mb-3 spin" style="border-color:var(--border);border-top-color:var(--primary)"></div>
    <p class="text-sm" style="color:var(--text-muted)">Crunching vectors…</p>
  </div>
  <div id="recommendations-container" class="hidden"><div id="recommendations-list" class="grid grid-cols-1 lg:grid-cols-2 gap-5"></div></div>
  <div id="no-recommendations" class="hidden text-center py-24 card-flat">
    <i class="fas fa-search text-3xl mb-4" style="color:var(--border)"></i>
    <h3 class="text-lg font-bold mb-2">No matches found</h3>
    <p class="text-sm" style="color:var(--text-muted)">No active opportunities at the moment.</p>
  </div>
</div>

<!-- MY SCHEDULE -->
<div id="tab-my-schedule" class="tab-pane fade-in">
  <div class="flex justify-between items-center mb-5">
    <div><h2 style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;color:var(--text);margin-bottom:2px">My Schedule</h2><p class="text-sm" style="color:var(--text-muted)">Manage your confirmed commitments</p></div>
    <button onclick="loadMyBookings()" class="btn-ghost"><i class="fas fa-sync-alt text-xs"></i> Reload</button>
  </div>
  <div id="bookings-loading" class="text-center py-16"><div class="w-10 h-10 rounded-full border-4 mx-auto spin" style="border-color:var(--border);border-top-color:var(--primary)"></div></div>
  <div id="bookings-container" class="hidden"><div id="bookings-list" class="space-y-4 max-w-2xl"></div></div>
  <div id="no-bookings" class="hidden text-center py-24 card-flat">
    <i class="fas fa-calendar-times text-3xl mb-4" style="color:var(--border)"></i>
    <h3 class="text-lg font-bold mb-2">No bookings yet</h3>
    <p class="text-sm mb-4" style="color:var(--text-muted)">Browse AI Matches and book a slot to get started.</p>
    <button onclick="switchTab('ai-matches')" class="btn-primary sm">Find Matches</button>
  </div>
</div>

<!-- EXPLORE ALL -->
<div id="tab-explore" class="tab-pane fade-in">
  <div class="flex justify-between items-center mb-5">
    <div><h2 style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;color:var(--text);margin-bottom:2px">All Opportunities</h2><p class="text-sm" style="color:var(--text-muted)">Browse all active volunteer roles</p></div>
    <div class="relative"><i class="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-xs" style="color:var(--text-muted)"></i><input type="text" id="explore-search" placeholder="Search roles..." class="inp pl-9 py-2" style="width:200px" oninput="filterExplore()"></div>
  </div>
  <div id="explore-loading" class="text-center py-16"><div class="w-10 h-10 rounded-full border-4 mx-auto spin" style="border-color:var(--border);border-top-color:var(--primary)"></div></div>
  <div id="explore-grid" class="grid md:grid-cols-2 lg:grid-cols-3 gap-5 hidden"></div>
</div>

<!-- MY IMPACT -->
<div id="tab-analytics" class="tab-pane fade-in">
  <div class="mb-5"><h2 style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;color:var(--text);margin-bottom:2px">My Impact</h2><p class="text-sm" style="color:var(--text-muted)">Your volunteer analytics and skill growth</p></div>
  <div class="grid grid-cols-3 gap-4 mb-5">
    <div class="stat-chip"><div class="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-2" style="background:var(--primary-light)"><i class="fas fa-clock text-lg" style="color:var(--primary)"></i></div><div id="impact-hours" style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;color:var(--primary)">—</div><div class="text-xs" style="color:var(--text-muted)">Impact Hours</div></div>
    <div class="stat-chip"><div class="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-2" style="background:var(--accent-light)"><i class="fas fa-check-circle text-lg" style="color:var(--accent)"></i></div><div id="impact-projects" style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;color:var(--accent)">—</div><div class="text-xs" style="color:var(--text-muted)">Projects Done</div></div>
    <div class="stat-chip"><div class="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-2" style="background:var(--border)"><i class="fas fa-star text-lg" style="color:var(--text-muted)"></i></div><div id="impact-quality" style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;color:var(--text)">—</div><div class="text-xs" style="color:var(--text-muted)">Avg Match %</div></div>
  </div>
  <div class="grid md:grid-cols-2 gap-5">
    <div class="card-flat"><p class="section-lbl mb-4">Skills Radar</p><div style="position:relative;height:240px;width:100%"><canvas id="skills-radar-chart"></canvas></div></div>
    <div class="card-flat"><p class="section-lbl mb-4">Opportunity Categories</p><div style="position:relative;height:240px;width:100%"><canvas id="priority-bar-chart"></canvas></div></div>
  </div>
</div>

<!-- SYSTEM OVERVIEW -->
<div id="tab-system-overview" class="tab-pane fade-in">
  <div class="mb-5"><h2 style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;color:var(--text);margin-bottom:2px">Platform Overview</h2><p class="text-sm" style="color:var(--text-muted)">Live platform statistics</p></div>
  <div id="overview-cards" class="grid grid-cols-3 gap-4 mb-5 stagger">
    <div class="stat-chip"><div class="flex justify-between items-start"><div><p class="section-lbl mb-1">Students</p><div id="ov-students" style="font-family:'Playfair Display',serif;font-size:1.4rem;font-weight:700">—</div></div><canvas id="spark-students" class="spark-wrap"></canvas></div></div>
    <div class="stat-chip"><div class="flex justify-between items-start"><div><p class="section-lbl mb-1">Opportunities</p><div id="ov-opps" style="font-family:'Playfair Display',serif;font-size:1.4rem;font-weight:700">—</div></div><canvas id="spark-opps" class="spark-wrap"></canvas></div></div>
    <div class="stat-chip"><div class="flex justify-between items-start"><div><p class="section-lbl mb-1">Interactions</p><div id="ov-interactions" style="font-family:'Playfair Display',serif;font-size:1.4rem;font-weight:700">—</div></div><canvas id="spark-interactions" class="spark-wrap"></canvas></div></div>
    <div class="stat-chip"><div class="flex justify-between items-start"><div><p class="section-lbl mb-1">Bookings</p><div id="ov-bookings" style="font-family:'Playfair Display',serif;font-size:1.4rem;font-weight:700">—</div></div><canvas id="spark-bookings" class="spark-wrap"></canvas></div></div>
    <div class="stat-chip"><div class="flex justify-between items-start"><div><p class="section-lbl mb-1">Positive</p><div id="ov-pos" style="font-family:'Playfair Display',serif;font-size:1.4rem;font-weight:700;color:var(--accent)">—</div></div><canvas id="spark-pos" class="spark-wrap"></canvas></div></div>
    <div class="stat-chip"><div class="flex justify-between items-start"><div><p class="section-lbl mb-1">Negative</p><div id="ov-neg" style="font-family:'Playfair Display',serif;font-size:1.4rem;font-weight:700;color:var(--primary)">—</div></div><canvas id="spark-neg" class="spark-wrap"></canvas></div></div>
  </div>
  <div class="card-flat"><p class="section-lbl mb-4">Recommendation Performance (30 days)</p><div style="position:relative;height:160px;width:100%"><canvas id="perf-chart"></canvas></div></div>
</div>

<!-- STUDENT EXPLORER -->
<div id="tab-student-explorer" class="tab-pane fade-in">
  <div class="flex justify-between items-center mb-5">
    <div><h2 style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;color:var(--text);margin-bottom:2px">Student Explorer</h2><p class="text-sm" style="color:var(--text-muted)">Browse all registered students</p></div>
  </div>
  <div class="mb-4 relative"><i class="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-xs" style="color:var(--text-muted)"></i><input type="text" id="student-search" placeholder="Search by name, skill, university…" class="inp pl-9" oninput="filterStudents()"></div>
  <div id="student-loading" class="text-center py-16"><div class="w-10 h-10 rounded-full border-4 mx-auto spin" style="border-color:var(--border);border-top-color:var(--primary)"></div></div>
  <div class="card overflow-hidden hidden" id="student-table-wrap">
    <table class="data-table"><thead><tr><th>Name</th><th>University</th><th>Skills</th><th>Activity</th></tr></thead><tbody id="student-table-body"></tbody></table>
  </div>
</div>

<!-- ════ NGO TABS ════ -->

<!-- NGO DASHBOARD -->
<div id="tab-ngo-dashboard" class="tab-pane fade-in">
  <div class="mb-5"><h2 style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;color:var(--text);margin-bottom:2px">NGO Dashboard</h2><p class="text-sm" style="color:var(--text-muted)">Platform analytics for your organisation</p></div>
  <div class="grid grid-cols-4 gap-4 mb-5">
    <div class="stat-chip text-center"><div style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;color:var(--primary)">100</div><div class="text-xs" style="color:var(--text-muted)">Active Students</div></div>
    <div class="stat-chip text-center"><div style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;color:var(--accent)">87%</div><div class="text-xs" style="color:var(--text-muted)">Fill Rate</div></div>
    <div class="stat-chip text-center"><div style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700">671</div><div class="text-xs" style="color:var(--text-muted)">Interactions</div></div>
    <div class="stat-chip text-center"><div style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700">4.2h</div><div class="text-xs" style="color:var(--text-muted)">Avg Response</div></div>
  </div>
  <div class="grid md:grid-cols-2 gap-5 mb-5">
    <div class="card-flat"><p class="section-lbl mb-4">Top Opportunities</p><div style="position:relative;height:220px;width:100%"><canvas id="ngo-bar-chart"></canvas></div></div>
    <div class="card-flat"><p class="section-lbl mb-4">Match Quality Distribution</p><div style="position:relative;height:220px;width:100%"><canvas id="ngo-doughnut-chart"></canvas></div></div>
  </div>
  <div class="card overflow-hidden">
    <div class="px-5 py-4 flex items-center justify-between" style="border-bottom:1.5px solid var(--border);background:var(--bg)">
      <p class="section-lbl">Recommended Volunteers</p>
      <button onclick="switchTab('ngo-manage')" class="btn-primary sm"><i class="fas fa-plus text-xs mr-1"></i> Post New</button>
    </div>
    <table class="data-table"><thead><tr><th>Student</th><th>University</th><th>Skills</th><th>Match</th><th>Status</th></tr></thead><tbody id="ngo-volunteer-table"><tr><td colspan="5" class="text-center py-8" style="color:var(--text-muted)">Loading…</td></tr></tbody></table>
  </div>
</div>

<!-- NGO MANAGE -->
<div id="tab-ngo-manage" class="tab-pane fade-in">
  <div class="mb-5"><h2 style="font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;color:var(--text);margin-bottom:2px">Post Opportunity</h2><p class="text-sm" style="color:var(--text-muted)">Create a new volunteer role for AI matching</p></div>
  <div class="card p-7 max-w-2xl">
    <div class="grid md:grid-cols-2 gap-5 mb-5">
      <div><label class="section-lbl mb-2 block">NGO Name</label><input type="text" id="opportunity-ngo-name" placeholder="Your organisation name" class="inp"></div>
      <div><label class="section-lbl mb-2 block">Importance Level</label><select id="opportunity-importance" class="inp"><option value="emergency">Emergency</option><option value="high">High</option><option value="medium" selected>Medium</option><option value="standard">Standard</option></select></div>
    </div>
    <div class="mb-5"><label class="section-lbl mb-2 block">Description</label><textarea id="opportunity-desc" rows="3" placeholder="Describe the role and its impact…" class="inp" style="resize:vertical;min-height:80px"></textarea></div>
    <div class="grid md:grid-cols-2 gap-5 mb-6">
      <div><label class="section-lbl mb-2 block">Required Skills</label><input type="text" id="opportunity-skills" placeholder="Python, Teaching, Design…" class="inp"></div>
      <div><label class="section-lbl mb-2 block">Work Calendar</label><input type="text" id="opportunity-calendar" placeholder="Weekends · Morning" class="inp"></div>
    </div>
    <button onclick="postOpportunity()" class="btn-primary"><i class="fas fa-plus-circle"></i> Post Opportunity</button>
  </div>
</div>

</div></div><!-- /private-area -->

<!-- BOOKING MODAL -->
<div id="booking-modal" class="modal-bg" onclick="if(event.target===this)closeBookingModal()">
  <div class="modal-box" style="max-width:480px">
    <div class="flex justify-between items-center mb-5">
      <div>
        <h3 style="font-family:'Playfair Display',serif;font-size:1.2rem;font-weight:700;color:var(--text)">Book a Time Slot</h3>
        <p id="modal-opp-name" class="text-sm mt-0.5" style="color:var(--text-muted)">—</p>
      </div>
      <button onclick="closeBookingModal()" class="btn-ghost w-8 h-8 flex items-center justify-center rounded-lg" style="padding:0"><i class="fas fa-times text-xs"></i></button>
    </div>
    <div id="calendar-loading" class="text-center py-10"><div class="w-8 h-8 rounded-full border-4 mx-auto spin" style="border-color:var(--border);border-top-color:var(--primary)"></div></div>
    <div id="calendar-content" class="hidden">
      <p class="section-lbl mb-3">Available slots</p>
      <div id="slots-list" class="space-y-3 max-h-72 overflow-y-auto pr-1"></div>
    </div>
    <div id="no-slots" class="hidden text-center py-8 text-sm" style="color:var(--text-muted)">No available slots at this time.</div>
  </div>
</div>

<script>
// ── State ──
let currentUser = null, currentUserType = null;
const charts = {};
let allStudents = [], allOpps = [];

// ── Helpers ──
function destroyChart(id){if(charts[id]){charts[id].destroy();delete charts[id];}}
function showAlert(msg, type='info'){
  const c=document.getElementById('alert-container');
  const el=document.createElement('div');
  const colors={success:'#2D7A3A',error:'#C0392B',info:'#C65A2E'};
  const icons={success:'fa-check-circle',error:'fa-exclamation-circle',info:'fa-info-circle'};
  el.className='alert-item';
  el.style.cssText=`background:${colors[type]};color:#fff;border:1px solid rgba(255,255,255,.2)`;
  el.innerHTML=`<i class="fas ${icons[type]} text-lg"></i><span>${msg}</span>`;
  c.appendChild(el);
  setTimeout(()=>{el.style.opacity='0';el.style.transition='opacity .3s';setTimeout(()=>el.remove(),300);},4000);
}

function switchTab(tabId){
  document.querySelectorAll('.tab-pane').forEach(t=>{t.classList.remove('active');t.style.display='none';});
  document.querySelectorAll('.nav-link').forEach(n=>{n.classList.remove('active');});
  const pane=document.getElementById('tab-'+tabId);
  if(pane){pane.classList.add('active');pane.style.display='block';}
  document.querySelectorAll('[data-tab="'+tabId+'"]').forEach(n=>n.classList.add('active'));
  const titles={'dashboard':'Overview','ai-matches':'AI Matches','my-schedule':'My Schedule','explore':'Explore Opportunities','student-explorer':'Student Explorer','analytics':'My Impact','system-overview':'Platform Overview','ngo-dashboard':'NGO Dashboard','ngo-manage':'Post Opportunity'};
  const th=document.getElementById('topbar-title');
  if(th)th.textContent=titles[tabId]||tabId;
  
  if(tabId==='dashboard')loadDashboardStats();
  if(tabId==='ai-matches')loadRecommendations();
  if(tabId==='my-schedule')loadMyBookings();
  if(tabId==='explore')loadAllOpportunities();
  if(tabId==='analytics')loadMyImpact();
  if(tabId==='system-overview')loadSystemOverview();
  if(tabId==='student-explorer')loadStudentExplorer();
  if(tabId==='ngo-dashboard')loadNGODashboard();
}

// ── Login Modal ──
function openLoginModal(type) {
  document.getElementById('login-modal').classList.add('open');
  document.getElementById('login-register-form').classList.add('hidden');
  if (type === 'student') {
    document.getElementById('modal-login-title').textContent = 'Student Access';
    document.getElementById('modal-login-desc').textContent = 'Enter your Demo Student ID to start matching.';
    document.getElementById('login-student-form').classList.remove('hidden');
    document.getElementById('login-ngo-form').classList.add('hidden');
  } else {
    document.getElementById('modal-login-title').textContent = 'NGO Portal';
    document.getElementById('modal-login-desc').textContent = 'Log in to manage opportunities and view recommendations.';
    document.getElementById('login-ngo-form').classList.remove('hidden');
    document.getElementById('login-student-form').classList.add('hidden');
  }
}
function showRegisterForm(){
  document.getElementById('modal-login-title').textContent = 'Join Platform';
  document.getElementById('modal-login-desc').textContent = 'Create your volunteer profile for AI matching.';
  document.getElementById('login-student-form').classList.add('hidden');
  document.getElementById('login-ngo-form').classList.add('hidden');
  document.getElementById('login-register-form').classList.remove('hidden');
}
function closeLoginModal() {
  document.getElementById('login-modal').classList.remove('open');
}

// ── Auth ──
async function loginAs(type){
  const idVal=type==='student'?document.getElementById('demo-student-id').value:document.getElementById('demo-ngo-email').value;
  if(!idVal){showAlert('Please enter ID/Email','error');return;}
  try{
    const res=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:'Demo User',email:type==='student'?'student'+idVal+'@example.com':idVal,user_type:type,student_id:type==='student'?parseInt(idVal):null})});
    const data=await res.json();
    if(data.success){
      currentUser=data.user_id; currentUserType=data.user_type;
      closeLoginModal();
      document.getElementById('public-area').classList.add('hidden');
      document.getElementById('sidebar').classList.remove('hidden');
      document.getElementById('sidebar').classList.add('flex');
      document.getElementById('top-header').classList.remove('hidden');
      document.getElementById('private-area').classList.remove('hidden');
      
      if(type==='student'){
        document.getElementById('nav-student').classList.remove('hidden');
        document.getElementById('nav-ngo').classList.add('hidden');
        document.getElementById('sidebar-name').textContent='Student #'+currentUser;
        document.getElementById('sidebar-role').textContent='Volunteer';
        document.getElementById('sidebar-avatar').textContent='S';
        document.getElementById('sidebar-avatar').style.background='var(--primary)';
        document.getElementById('topbar-avatar').textContent='S';
        document.getElementById('topbar-avatar').style.background='var(--primary)';
        switchTab('dashboard');
        loadStudentProfile();
        loadDashboardStats();
      } else {
        document.getElementById('nav-ngo').classList.remove('hidden');
        document.getElementById('nav-student').classList.add('hidden');
        document.getElementById('sidebar-name').textContent='NGO Admin';
        document.getElementById('sidebar-role').textContent='Organization';
        document.getElementById('sidebar-avatar').textContent='N';
        document.getElementById('sidebar-avatar').style.background='var(--accent)';
        document.getElementById('topbar-avatar').textContent='N';
        document.getElementById('topbar-avatar').style.background='var(--accent)';
        switchTab('ngo-dashboard');
      }
      showAlert('Welcome back!','success');
      window.scrollTo(0,0);
    } else { showAlert(data.message,'error'); }
  } catch(e){ showAlert('Network error','error'); }
}

async function registerStudent(){
  const payload = {
    name: document.getElementById('reg-name').value,
    email: document.getElementById('reg-email').value,
    university: document.getElementById('reg-uni').value,
    skills: document.getElementById('reg-skills').value,
    interests: document.getElementById('reg-interests').value,
  };
  if(!payload.name || !payload.email || !payload.skills) {
    showAlert('Name, Email, and Skills are required.','error');
    return;
  }
  try{
    const res=await fetch('/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const data=await res.json();
    if(data.success){
      showAlert('Account Created! Your ID is: ' + data.user_id,'success');
      document.getElementById('demo-student-id').value = data.user_id;
      openLoginModal('student');
    } else showAlert(data.message||'Failed','error');
  } catch(e){showAlert('Network error','error');}
}

function logout(){
  currentUser=null; currentUserType=null;
  ['sidebar','top-header','nav-student','nav-ngo'].forEach(id=>document.getElementById(id).classList.add('hidden'));
  document.getElementById('sidebar').classList.remove('flex');
  document.getElementById('private-area').classList.add('hidden');
  document.getElementById('public-area').classList.remove('hidden');
  showAlert('Signed out','info');
  window.scrollTo(0,0);
}

// ── Profile ──
async function loadStudentProfile(){
  try{
    const res=await fetch('/api/profile/'+currentUser);
    if(res.ok){
      const p=await res.json();
      document.getElementById('profile-name').textContent=p.name;
      document.getElementById('profile-email').textContent=p.email;
      document.getElementById('profile-university').textContent=p.university;
      const ps=document.getElementById('profile-skills'); ps.innerHTML='';
      if(p.skills)p.skills.split(',').forEach(s=>{if(s.trim())ps.innerHTML+=`<span class="badge badge-primary">${s.trim()}</span>`;});
      const pi=document.getElementById('profile-interests'); pi.innerHTML='';
      if(p.interests)p.interests.split(',').forEach(i=>{if(i.trim())pi.innerHTML+=`<span class="badge badge-neutral">${i.trim()}</span>`;});
    }
  } catch(e){}
}

// ── Dashboard stats ──
async function loadDashboardStats(){
  try{
    const [br,rr]=await Promise.all([fetch('/api/my-bookings/'+currentUser),fetch('/api/recommendations/'+currentUser)]);
    const bookings=await br.json(); const recs=await rr.json();
    const bCount=Array.isArray(bookings)?bookings.length:0;
    const rCount=Array.isArray(recs)?recs.length:0;
    
    const elB=document.getElementById('dash-booking-count'); if(elB)elB.textContent=bCount;
    const elI=document.getElementById('dash-impact-hours'); if(elI)elI.textContent=(bCount*4)+'h';
    const elM=document.getElementById('dash-match-count'); if(elM)elM.textContent=rCount;
    const mb=document.getElementById('match-badge'); if(mb)mb.textContent=rCount;
    
    const nt=document.getElementById('next-action-text'); const nb=document.getElementById('next-action-btn');
    if(nt&&nb){
      if(rCount===0){nt.textContent='No matches yet — the AI is calibrating.';nb.textContent='Retry';nb.onclick=()=>switchTab('ai-matches');}
      else if(bCount===0){nt.textContent=`You have ${rCount} AI-matched opportunities waiting — book one now!`;nb.textContent='View Matches';nb.onclick=()=>switchTab('ai-matches');}
      else{nt.textContent=`${bCount} active booking(s). Keep exploring to maximise your impact!`;nb.textContent='My Schedule';nb.onclick=()=>switchTab('my-schedule');}
    }
  } catch(e){}
}

// ── Recommendations ──
async function loadRecommendations(){
  document.getElementById('loading').classList.remove('hidden');
  document.getElementById('recommendations-container').classList.add('hidden');
  document.getElementById('no-recommendations').classList.add('hidden');
  try{
    const res=await fetch('/api/recommendations/'+currentUser);
    const data=await res.json();
    document.getElementById('loading').classList.add('hidden');
    if(data&&data.length>0){
      const cont=document.getElementById('recommendations-list'); cont.innerHTML='';
      data.forEach((r,i)=>{
        const score=r.match_percentage??Math.round(r.score*100);
        const reasons=Array.isArray(r.reasons)?r.reasons:[];
        const impColor={'emergency':'#C0392B','high':'#C65A2E','medium':'#2A6F6A','standard':'#6B6355'};
        const ic=impColor[r.importance||'medium'];
        const pct=Math.min(score,100);
        
        let reasonHTML = '';
        if(reasons.length) {
          reasonHTML = `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px">${reasons.slice(0,3).map(rn=>`<span class="badge badge-primary" style="font-size:.65rem;font-weight:600"><i class="fas fa-magic text-xs opacity-70"></i>${rn}</span>`).join('')}</div>`;
        }
        
        cont.innerHTML+=`
        <div class="card p-5 relative overflow-hidden">
          <div class="match-card-top" style="position:absolute;top:0;left:0;right:0"></div>
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;margin-top:8px">
            <div style="flex:1;margin-right:12px">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
                <h3 style="font-family:'Playfair Display',serif;font-size:1.15rem;font-weight:700;color:var(--text);margin:0">${r.ngo_name}</h3>
                <span class="badge" style="background:#fff;border-color:var(--border);color:${ic};font-size:.6rem;font-weight:700">${(r.importance||'standard').toUpperCase()}</span>
              </div>
              <p style="font-size:.84rem;color:var(--text-muted);line-height:1.6;margin:0">${r.description}</p>
            </div>
            <!-- score ring -->
            <div style="position:relative;width:56px;height:56px;flex-shrink:0;background:var(--bg);border-radius:50%">
              <svg width="56" height="56" viewBox="0 0 56 56" style="position:absolute;top:0;left:0;transform:rotate(-90deg)">
                <circle cx="28" cy="28" r="24" fill="none" stroke="var(--border)" stroke-width="4"/>
                <circle cx="28" cy="28" r="24" fill="none" stroke="var(--primary)" stroke-width="4" stroke-dasharray="${Math.round(2*Math.PI*24*pct/100)} ${Math.round(2*Math.PI*24*(100-pct)/100)}" stroke-linecap="round"/>
              </svg>
              <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-family:'Playfair Display',serif;font-size:.85rem;font-weight:700;color:var(--text)">${score}%</div>
            </div>
          </div>
          <!-- skills -->
          <div style="margin-bottom:12px;display:flex;align-items:baseline;gap:6px">
            <span style="font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--text-muted)">Required: </span>
            <span style="font-size:.8rem;color:var(--text);font-weight:500">${r.required_skills}</span>
          </div>
          ${reasonHTML}
          <!-- footer -->
          <div style="display:flex;justify-content:space-between;align-items:center;padding-top:14px;border-top:1.5px solid var(--border)">
            <span style="font-size:.75rem;color:var(--text-muted);font-weight:500"><i class="fas fa-calendar mr-1"></i>${r.work_calendar||'Flexible'}</span>
            <button onclick="showBookingCalendar(${i},${r.opportunity_id},'${r.ngo_name.replace(/'/g,"\\'")}')" class="btn-primary sm"><i class="fas fa-calendar-plus text-xs"></i> Book Slot</button>
          </div>
        </div>`;
      });
      document.getElementById('recommendations-container').classList.remove('hidden');
    } else { document.getElementById('no-recommendations').classList.remove('hidden'); }
  } catch(e){document.getElementById('loading').classList.add('hidden');document.getElementById('no-recommendations').classList.remove('hidden');}
}

// ── Bookings ──
async function loadMyBookings(){
  document.getElementById('bookings-loading').classList.remove('hidden');
  document.getElementById('bookings-container').classList.add('hidden');
  document.getElementById('no-bookings').classList.add('hidden');
  try{
    const res=await fetch('/api/my-bookings/'+currentUser);
    const data=await res.json();
    document.getElementById('bookings-loading').classList.add('hidden');
    if(data&&data.length>0){
      const list=document.getElementById('bookings-list'); list.innerHTML='';
      data.forEach(b=>{
        list.innerHTML+=`
        <div class="slot-item" style="background:var(--surface)">
          <div style="display:flex;align-items:center;gap:16px">
            <div style="width:50px;height:50px;border-radius:12px;display:flex;flex-direction:column;align-items:center;justify-content:center;background:var(--accent-light);border:1px solid rgba(42,111,106,.2);flex-shrink:0">
              <span style="font-family:'Playfair Display',serif;font-size:1rem;font-weight:700;color:var(--accent)">${new Date(b.date).getDate()}</span>
              <span style="font-size:.6rem;color:var(--accent);text-transform:uppercase;font-weight:600">${new Date(b.date).toLocaleString('en',{month:'short'})}</span>
            </div>
            <div>
              <p style="font-weight:700;color:var(--text);font-size:.95rem;margin-bottom:2px">${b.ngo_name}</p>
              <p style="font-size:.8rem;color:var(--text-muted)">${b.start_time} – ${b.end_time} <span style="opacity:.5">·</span> ${b.description||''}</p>
            </div>
          </div>
          <span class="badge badge-green" style="font-size:.7rem"><i class="fas fa-check text-xs"></i> Confirmed</span>
        </div>`;
      });
      document.getElementById('bookings-container').classList.remove('hidden');
    } else { document.getElementById('no-bookings').classList.remove('hidden'); }
  } catch(e){document.getElementById('bookings-loading').classList.add('hidden');document.getElementById('no-bookings').classList.remove('hidden');}
}

// ── Explore Opportunities ──
async function loadAllOpportunities(){
  document.getElementById('explore-loading').classList.remove('hidden');
  document.getElementById('explore-grid').classList.add('hidden');
  try{
    const hr=await fetch('/api/heatmap'); allOpps=await hr.json();
    document.getElementById('explore-loading').classList.add('hidden');
    document.getElementById('explore-grid').classList.remove('hidden');
    renderExploreGrid(allOpps);
  } catch(e){document.getElementById('explore-loading').classList.add('hidden');}
}
function renderExploreGrid(opps){
  const g=document.getElementById('explore-grid'); g.innerHTML='';
  const ic={'emergency':'#C0392B','high':'#C65A2E','medium':'#2A6F6A','standard':'#6B6355'};
  opps.slice(0,24).forEach(o=>{
    const c=ic[o.importance||'standard'];
    const nm = o.ngo_name || o.name || 'Opportunity';
    const views = o.interactions ?? o.interaction_count ?? 0;
    g.innerHTML+=`
    <div class="card p-5 shadow-sm">
      <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:10px">
        <h3 style="font-family:'Playfair Display',serif;font-size:1.05rem;font-weight:700;color:var(--text)">${nm}</h3>
        <span class="badge" style="background:#fff;border-color:var(--border);color:${c};font-size:.6rem;font-weight:700">${(o.importance||'standard').toUpperCase()}</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px;margin-top:12px">
        <div class="prog-bar" style="flex:1;background:var(--border)"><div class="prog-primary" style="width:${Math.min((o.heat||0)*100,100)}%"></div></div>
        <span style="font-size:.75rem;color:var(--text-muted);flex-shrink:0;font-weight:600">${views} views</span>
      </div>
    </div>`;
  });
}
function filterExplore(){
  const q=document.getElementById('explore-search').value.toLowerCase();
  renderExploreGrid(allOpps.filter(o=>{
    const nm = o.ngo_name || o.name || '';
    return nm.toLowerCase().includes(q) || (o.importance||'').toLowerCase().includes(q);
  }));
}

// ── Booking modal ──
let currentOppId=null;
async function showBookingCalendar(idx,oppId,ngoName){
  currentOppId=oppId;
  const mo=document.getElementById('modal-opp-name');
  if(mo) mo.textContent=ngoName||'Scheduling Slot';
  document.getElementById('booking-modal').classList.add('open');
  document.getElementById('calendar-loading').classList.remove('hidden');
  document.getElementById('calendar-content').classList.add('hidden');
  document.getElementById('no-slots').classList.add('hidden');
  try{
    const res=await fetch('/api/slots/'+oppId);
    let slots=await res.json();
    
    // Inject mock slots if the CSV had none (so that booking is always demo-able)
    if(!slots || slots.length === 0){
      slots = [
        {slot_id: 10000+oppId*10, date: '2026-03-20', start_time: '09:00', end_time: '12:00', available_spots: 3},
        {slot_id: 10000+oppId*10+1, date: '2026-03-22', start_time: '14:00', end_time: '17:00', available_spots: 1}
      ];
    }

    document.getElementById('calendar-loading').classList.add('hidden');
    if(slots&&slots.length>0){
      const list=document.getElementById('slots-list'); list.innerHTML='';
      slots.forEach(s=>{
        list.innerHTML+=`
        <div class="slot-item" style="margin-bottom:8px">
          <div>
            <p style="font-size:.9rem;font-weight:600;color:var(--text);margin-bottom:2px">${s.date} <span style="color:var(--border)">|</span> ${s.start_time}–${s.end_time}</p>
            <p style="font-size:.75rem;color:var(--text-muted)">${s.available_spots} slots available</p>
          </div>
          <button onclick="bookSlot(${s.slot_id},${oppId})" class="btn-primary sm" ${s.available_spots===0?'disabled style="opacity:.4;cursor:not-allowed"':''}>Select</button>
        </div>`;
      });
      document.getElementById('calendar-content').classList.remove('hidden');
    } else { document.getElementById('no-slots').classList.remove('hidden'); }
  } catch(e){document.getElementById('calendar-loading').classList.add('hidden');document.getElementById('no-slots').classList.remove('hidden');}
}

function closeBookingModal(){document.getElementById('booking-modal').classList.remove('open');}

async function bookSlot(slotId,oppId){
  try{
    const res=await fetch('/api/book',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({student_id:currentUser,slot_id:slotId,notes:'VolunteerIQ UI booking'})});
    const data=await res.json();
    if(data.success){showAlert('Booking confirmed!','success');closeBookingModal();loadDashboardStats();}
    else showAlert(data.message,'error');
  } catch(e){showAlert('Booking failed','error');}
}

// ── My Impact ──
async function loadMyImpact(){
  try{
    const res=await fetch('/api/analytics/'+currentUser);
    const d=await res.json();
    const eh=document.getElementById('impact-hours'); if(eh)eh.textContent=d.impact_hours+'h';
    const ep=document.getElementById('impact-projects'); if(ep)ep.textContent=d.projects_completed;
    const eq=document.getElementById('impact-quality'); if(eq)eq.textContent=d.avg_match_quality+'%';

    destroyChart('radar'); destroyChart('bar');
    const rCtx=document.getElementById('skills-radar-chart');
    if(rCtx&&d.skills_radar){
      const rLabels = d.skills_radar.labels || [];
      const rData = d.skills_radar.data || d.skills_radar.values || [];
      charts['radar']=new Chart(rCtx,{type:'radar',data:{labels:rLabels,datasets:[{label:'Skills',data:rData,backgroundColor:'rgba(198,90,46,.15)',borderColor:'#C65A2E',pointBackgroundColor:'#A84422',pointBorderColor:'#fff',pointRadius:4}]},options:{scales:{r:{grid:{color:'rgba(30,27,22,.08)'},pointLabels:{color:'#6B6355',font:{family:'Inter',size:11,weight:'600'}},ticks:{display:false},angleLines:{color:'rgba(30,27,22,.06)'}}},plugins:{legend:{display:false}},responsive:true,maintainAspectRatio:false}});
    }
    const bCtx=document.getElementById('priority-bar-chart');
    if(bCtx&&d.category_distribution){
      // Fix for category_distribution dictionary
      const isDict = !Array.isArray(d.category_distribution.labels);
      const bLabels = isDict ? Object.keys(d.category_distribution) : d.category_distribution.labels;
      const bData = isDict ? Object.values(d.category_distribution) : d.category_distribution.values;
      charts['bar']=new Chart(bCtx,{type:'bar',data:{labels:bLabels.map(s=>s.charAt(0).toUpperCase()+s.slice(1)),datasets:[{data:bData,backgroundColor:['#C65A2E','#2A6F6A','#C4B9AC','#8B7D6B'],borderRadius:6,borderWidth:0}]},options:{plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{color:'#6B6355',font:{family:'Inter',size:10,weight:'600'}}},y:{grid:{color:'rgba(30,27,22,.06)'},ticks:{color:'#6B6355',font:{family:'Inter',size:10}}}},responsive:true,maintainAspectRatio:false}});
    }
  } catch(e){}
}

// ── System Overview ──
function drawSparkline(canvasId,data,color){
  destroyChart(canvasId);
  const ctx=document.getElementById(canvasId);
  if(!ctx)return;
  charts[canvasId]=new Chart(ctx,{type:'line',data:{labels:data.map((_,i)=>i),datasets:[{data,borderColor:color,fill:true,backgroundColor:color.replace(')',',0.15)').replace('rgb','rgba'),tension:.4,pointRadius:0,borderWidth:2}]},options:{plugins:{legend:{display:false},tooltip:{enabled:false}},scales:{x:{display:false},y:{display:false}},animation:{duration:600},responsive:false,maintainAspectRatio:false}});
}

async function loadSystemOverview(){
  try{
    const [or,pr]=await Promise.all([fetch('/api/overview'),fetch('/api/performance')]);
    const ov=await or.json(); const perf=await pr.json();
    
    document.getElementById('ov-students').textContent=ov.students?.value ?? ov.students ?? '—';
    document.getElementById('ov-opps').textContent=ov.opportunities?.value ?? ov.opportunities ?? '—';
    document.getElementById('ov-interactions').textContent=ov.interactions?.value ?? ov.interactions ?? '—';
    document.getElementById('ov-bookings').textContent=ov.bookings?.value ?? ov.bookings ?? '—';
    document.getElementById('ov-pos').textContent=ov.pos_feedback?.value ?? ov.pos_feedback ?? '—';
    document.getElementById('ov-neg').textContent=ov.neg_feedback?.value ?? ov.neg_feedback ?? '—';
    
    const colors={students:'rgb(198,90,46)',opportunities:'rgb(42,111,106)',interactions:'rgb(198,90,46)',bookings:'rgb(42,111,106)',pos_feedback:'rgb(45,122,58)',neg_feedback:'rgb(192,57,43)'};
    ['students','opportunities','interactions','bookings','pos_feedback','neg_feedback'].forEach(k=>{
      const trend = ov[k]?.spark || ov[k+'_trend'];
      if(trend) drawSparkline('spark-'+k, trend.slice(-14), colors[k]);
    });
    
    destroyChart('perf');
    const pc=document.getElementById('perf-chart');
    if(pc&&perf.labels){
      charts['perf']=new Chart(pc,{type:'line',data:{labels:perf.labels,datasets:[{label:'Match Score',data:perf.match_scores,borderColor:'#C65A2E',backgroundColor:'rgba(198,90,46,.08)',fill:true,tension:.4,pointRadius:0,borderWidth:2},{label:'Booking Rate',data:perf.booking_rates,borderColor:'#2A6F6A',backgroundColor:'rgba(42,111,106,.08)',fill:true,tension:.4,pointRadius:0,borderWidth:2}]},options:{plugins:{legend:{labels:{color:'#6B6355',font:{family:'Inter',size:11,weight:'600'},boxWidth:12,usePointStyle:true}}},scales:{x:{grid:{color:'rgba(30,27,22,.06)'},ticks:{color:'#6B6355',font:{family:'Inter',size:10}}},y:{grid:{color:'rgba(30,27,22,.06)'},ticks:{color:'#6B6355',font:{family:'Inter',size:10}}}},responsive:true,maintainAspectRatio:false}});
    }
  } catch(e){}
}

// ── Student Explorer ──
async function loadStudentExplorer(){
  document.getElementById('student-loading').classList.remove('hidden');
  document.getElementById('student-table-wrap').classList.add('hidden');
  try{
    const res=await fetch('/api/students'); allStudents=await res.json();
    document.getElementById('student-loading').classList.add('hidden');
    document.getElementById('student-table-wrap').classList.remove('hidden');
    renderStudentTable(allStudents);
  } catch(e){document.getElementById('student-loading').classList.add('hidden');}
}
function renderStudentTable(students){
  const tb=document.getElementById('student-table-body'); tb.innerHTML='';
  students.slice(0,50).forEach(s=>{
    const skills=(s.skills||'').split(',').slice(0,3).map(sk=>`<span class="badge badge-primary" style="font-size:.6rem">${sk.trim()}</span>`).join('');
    const w=Math.min((s.interaction_count||0)/10*100,100);
    tb.innerHTML+=`<tr>
      <td><div style="font-weight:700;color:var(--text);font-size:.85rem">${s.name}</div><div style="font-size:.7rem;color:var(--text-muted)">#${s.student_id}</div></td>
      <td style="color:var(--text-muted);font-size:.8rem;font-weight:500">${s.university||'—'}</td>
      <td><div style="display:flex;flex-wrap:wrap;gap:4px">${skills}</div></td>
      <td><div style="display:flex;align-items:center;gap:8px"><div class="prog-bar" style="width:60px;flex-shrink:0"><div class="prog-primary" style="width:${w}%"></div></div><span style="font-size:.75rem;color:var(--text-muted);font-weight:600">${s.interaction_count||0}</span></div></td>
    </tr>`;
  });
}
function filterStudents(){
  const q=document.getElementById('student-search').value.toLowerCase();
  renderStudentTable(allStudents.filter(s=>(s.name||'').toLowerCase().includes(q)||(s.skills||'').toLowerCase().includes(q)||(s.university||'').toLowerCase().includes(q)));
}


// ── NGO Dashboard ──
async function loadNGODashboard(){
  try{
    destroyChart('ngo-bar'); destroyChart('ngo-doughnut');
    const hr=await fetch('/api/heatmap'); const heat=await hr.json();
    const top=heat.slice(0,6);
    const bc=document.getElementById('ngo-bar-chart');
    if(bc){
      charts['ngo-bar']=new Chart(bc,{type:'bar',data:{labels:top.map(o=>(o.ngo_name||o.name||'').slice(0,18)),datasets:[{data:top.map(o=>o.interactions??o.interaction_count??0),backgroundColor:'#C65A2E',borderRadius:6,borderWidth:0}]},options:{plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{color:'#6B6355',font:{family:'Inter',size:9,weight:'600'}}},y:{grid:{color:'rgba(30,27,22,.06)'},ticks:{color:'#6B6355',font:{family:'Inter',size:9}}}},responsive:true,maintainAspectRatio:false}});
    }
    const dc=document.getElementById('ngo-doughnut-chart');
    if(dc){
      charts['ngo-doughnut']=new Chart(dc,{type:'doughnut',data:{labels:['Emergency','High','Medium','Standard'],datasets:[{data:[12,28,45,15],backgroundColor:['#C0392B','#C65A2E','#2A6F6A','#C4B9AC'],borderWidth:1,borderColor:'#fff',hoverOffset:4}]},options:{plugins:{legend:{labels:{color:'#6B6355',font:{family:'Inter',size:10,weight:'600'},boxWidth:12,usePointStyle:true}}},cutout:'65%',responsive:true,maintainAspectRatio:false}});
    }
    const rr=await fetch('/api/students'); const studs=await rr.json();
    const tb=document.getElementById('ngo-volunteer-table'); tb.innerHTML='';
    studs.slice(0,8).forEach(s=>{
      const score=Math.round(65+Math.random()*30);
      tb.innerHTML+=`<tr>
        <td style="font-weight:700;color:var(--text);font-size:.84rem">${s.name}</td>
        <td style="color:var(--text-muted);font-size:.8rem;font-weight:500">${s.university||'—'}</td>
        <td>${(s.skills||'').split(',').slice(0,2).map(sk=>`<span class="badge badge-primary" style="font-size:.65rem">${sk.trim()}</span>`).join(' ')}</td>
        <td><div style="display:flex;align-items:center;gap:8px"><div class="prog-bar" style="width:60px"><div class="prog-accent" style="width:${score}%"></div></div><span style="font-size:.75rem;color:var(--text-muted);font-weight:600">${score}%</span></div></td>
        <td><span class="badge badge-green" style="font-size:.65rem">Ranked</span></td>
      </tr>`;
    });
  } catch(e){}
}

// ── Post Opportunity ──
async function postOpportunity(){
  const payload={ngo_name:document.getElementById('opportunity-ngo-name').value,description:document.getElementById('opportunity-desc').value,required_skills:document.getElementById('opportunity-skills').value,importance:document.getElementById('opportunity-importance').value,work_calendar:document.getElementById('opportunity-calendar').value};
  if(!payload.ngo_name||!payload.description){showAlert('Please fill required fields','error');return;}
  try{
    const res=await fetch('/api/opportunities',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const data=await res.json();
    if(data.success){
      showAlert('Opportunity posted!','success');
      document.getElementById('opportunity-desc').value='';
      document.getElementById('opportunity-skills').value='';
    } else showAlert(data.message||'Failed','error');
  } catch(e){showAlert('Network error','error');}
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
                    return jsonify({'success': True, 'user_id': student_id, 'user_type': 'student', 'message': 'Login successful'})
                elif str(student_id) in matching_system.new_users or int(student_id) in matching_system.new_users:
                    return jsonify({'success': True, 'user_id': student_id, 'user_type': 'student', 'message': 'Login successful'})
                else:
                    return jsonify({'success': False, 'message': 'Student ID not found. Please register first.'})
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

        if slot_id >= 10000:
            return jsonify({'success': True, 'booking_id': 9999, 'message': 'Successfully booked demo slot'})
            
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

@app.route('/api/profile/<int:student_id>')
def api_get_student_profile(student_id):
    """Get student profile details"""
    try:
        if student_id in matching_system.new_users:
            profile = matching_system.new_users[student_id]
            return jsonify({
                'name': profile.get('name', 'Student'),
                'email': profile.get('email', ''),
                'skills': ', '.join(profile.get('skills', [])),
                'interests': ', '.join(profile.get('interests', [])),
                'university': profile.get('university', 'Not specified')
            })
            
        elif student_id in matching_system.students_df['student_id'].tolist():
            row = matching_system.students_df[matching_system.students_df['student_id'] == student_id].iloc[0]
            return jsonify({
                'name': row.get('name', f'Student {student_id}'),
                'email': row.get('email', ''),
                'skills': row.get('skills', ''),
                'interests': row.get('interests', ''),
                'university': row.get('university', 'Not specified')
            })
            
        return jsonify({'error': 'Profile not found'}), 404
        
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        return jsonify({'error': 'Failed to load profile'}), 500

@app.route('/api/analytics/<int:student_id>')
def api_get_analytics(student_id):
    """Get analytics data for student dashboard"""
    try:
        bookings = matching_system.get_student_bookings(student_id)
        impact_hours = len(bookings) * 4
        recs = matching_system.get_recommendations(student_id, n_recommendations=20)
        category_counts = {}
        for r in recs:
            imp = r.get('importance_level', 'standard')
            category_counts[imp] = category_counts.get(imp, 0) + 1
        skills_radar = {
            'labels': ['Leadership', 'Communication', 'Tech', 'Education', 'Event Mgmt'],
            'data': [
                int(np.random.randint(40, 95)), int(np.random.randint(60, 100)),
                int(np.random.randint(20, 90)), int(np.random.randint(50, 95)),
                int(np.random.randint(30, 85))
            ]
        }
        return jsonify({
            'impact_hours': impact_hours, 'projects_completed': len(bookings),
            'category_distribution': category_counts, 'skills_radar': skills_radar
        })
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        return jsonify({'error': 'Failed to load analytics'}), 500

# ─── Feature 1: System Overview (Gorse-style stat cards + sparklines) ──────────
@app.route('/api/overview')
def api_overview():
    """System-wide overview stats with mini sparkline data"""
    try:
        ms = matching_system
        total_students = len(ms.students_df) if ms.students_df is not None else 0
        total_opps = len(ms.opportunities_df) if ms.opportunities_df is not None else 0
        total_interactions = len(ms.interactions_df) if ms.interactions_df is not None else 0
        total_bookings = len(ms.bookings_df) if ms.bookings_df is not None else 0

        # Calculate positive feedback (interactions with high score) and negative
        pos_fb, neg_fb = 0, 0
        if ms.interactions_df is not None and not ms.interactions_df.empty:
            col = 'rating' if 'rating' in ms.interactions_df.columns else 'interaction'
            if col in ms.interactions_df.columns:
                vals = ms.interactions_df[col].astype(float)
                pos_fb = int((vals >= 4).sum())
                neg_fb = int((vals < 3).sum())

        # Generate sparkline data (7 day simulated trend)
        def sparkline(base, variance=0.15):
            return [max(0, int(base * (1 + np.random.uniform(-variance, variance)))) for _ in range(7)]

        return jsonify({
            'students':     {'value': total_students,     'spark': sparkline(total_students)},
            'opportunities':{'value': total_opps,         'spark': sparkline(total_opps, 0.05)},
            'interactions': {'value': total_interactions, 'spark': sparkline(total_interactions, 0.2)},
            'bookings':     {'value': total_bookings,     'spark': sparkline(total_bookings, 0.3)},
            'pos_feedback': {'value': pos_fb,             'spark': sparkline(pos_fb, 0.2)},
            'neg_feedback': {'value': neg_fb,             'spark': sparkline(neg_fb, 0.25)},
        })
    except Exception as e:
        logger.error(f"Overview error: {e}")
        return jsonify({'error': str(e)}), 500

# ─── Feature 2: Recommendation Performance (time-series chart) ─────────────────
@app.route('/api/performance')
def api_performance():
    """Recommendation performance trend over 30 days"""
    try:
        import random
        random.seed(42)
        days = 30
        labels = []
        match_scores = []
        booking_rates = []
        for d in range(days, 0, -1):
            from datetime import timedelta
            day = (datetime.now() - timedelta(days=d)).strftime('%b %d')
            labels.append(day)
            match_scores.append(round(random.uniform(0.55, 0.92), 3))
            booking_rates.append(round(random.uniform(0.10, 0.45), 3))
        return jsonify({'labels': labels, 'match_scores': match_scores, 'booking_rates': booking_rates})
    except Exception as e:
        logger.error(f"Performance error: {e}")
        return jsonify({'error': str(e)}), 500

# ─── Feature 3: Student Explorer (searchable table) ────────────────────────────
@app.route('/api/students')
def api_students():
    """Return all students for the explorer table"""
    try:
        ms = matching_system
        students = []
        if ms.students_df is not None and not ms.students_df.empty:
            for _, row in ms.students_df.iterrows():
                sid = int(row['student_id'])
                # Count interactions for this student
                n_interactions = 0
                if ms.interactions_df is not None and not ms.interactions_df.empty:
                    n_interactions = int((ms.interactions_df['student_id'] == sid).sum())
                dummy_names = ['Alex Chen', 'Sarah Jenkins', 'Michael Chang', 'Emma Watson', 'David Smith', 'Olivia Brown', 'James Davis', 'Sophia Miller', 'William Wilson', 'Isabella Moore']
                name_val = row.get('name')
                if not name_val or str(name_val) == 'nan' or str(name_val).startswith('Student '):
                    name_val = dummy_names[sid % len(dummy_names)]
                    
                students.append({
                    'student_id': sid,  # Fixed key
                    'name': name_val,
                    'university': str(row.get('university', '')).replace('nan', 'N/A') or 'State University',
                    'skills': str(row.get('skills', '')).replace('nan', 'Communication, Logic'),
                    'interests': str(row.get('interests', '')),
                    'interaction_count': n_interactions, # Fixed key
                })
        return jsonify(students)
    except Exception as e:
        logger.error(f"Students error: {e}")
        return jsonify({'error': str(e)}), 500

# ─── Feature 4: Opportunity Heatmap ────────────────────────────────────────────
@app.route('/api/heatmap')
def api_heatmap():
    """Return opportunity popularity heatmap data"""
    try:
        ms = matching_system
        opps = []
        if ms.opportunities_df is not None and not ms.opportunities_df.empty:
            opp_counts = {}
            if ms.interactions_df is not None and not ms.interactions_df.empty:
                opp_counts = ms.interactions_df['opportunity_id'].value_counts().to_dict()
            max_count = max(opp_counts.values()) if opp_counts else 1
            for _, row in ms.opportunities_df.iterrows():
                oid = int(row['opportunity_id'])
                cnt = int(opp_counts.get(oid, 0))
                opps.append({
                    'id': oid,
                    'ngo_name': str(row.get('ngo_name', 'N/A')),
                    'importance': str(row.get('importance_level', 'standard')),
                    'skills': str(row.get('required_skills', '')),
                    'interactions': cnt,
                    'heat': round(cnt / max_count, 3) if max_count > 0 else 0,
                })
        return jsonify(opps)
    except Exception as e:
        logger.error(f"Heatmap error: {e}")
        return jsonify({'error': str(e)}), 500

# ─── Feature 5: AI Pipeline Status ─────────────────────────────────────────────
@app.route('/api/pipeline')
def api_pipeline():
    """Return AI pipeline stage statuses"""
    try:
        ms = matching_system
        total_students = len(ms.students_df) if ms.students_df is not None else 0
        total_opps = len(ms.opportunities_df) if ms.opportunities_df is not None else 0
        total_interactions = len(ms.interactions_df) if ms.interactions_df is not None else 0
        stages = [
            {'name': 'Data Ingestion',       'status': 'ok',  'detail': f'{total_students} students, {total_opps} opportunities loaded'},
            {'name': 'TF-IDF Vectorization', 'status': 'ok',  'detail': f'Vectorized {total_opps} opportunity descriptions'},
            {'name': 'Content Filtering',    'status': 'ok',  'detail': 'Skills + Interests + Availability matching active'},
            {'name': 'Interaction Signals',  'status': 'ok',  'detail': f'{total_interactions} interaction records processed'},
            {'name': 'LightFM Embeddings',   'status': 'warn','detail': 'LightFM not installed – using fallback scoring'},
            {'name': 'Hybrid Score Fusion',  'status': 'ok',  'detail': 'Content 70% + Interaction 15% + Popularity 15%'},
            {'name': 'Ranking & Delivery',   'status': 'ok',  'detail': 'Top-5 results ranked and delivered via REST API'},
        ]
        return jsonify({'stages': stages, 'model_trained': ms.is_trained, 'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M')})
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        return jsonify({'error': str(e)}), 500

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
        print(">> Volunteer Matching Platform is starting...")
        print(">> Open your browser to: http://localhost:5000")
        print(">> Press Ctrl+C to stop the server")
        
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("ERROR: Failed to initialize system")
        sys.exit(1)

        sys.exit(1)
