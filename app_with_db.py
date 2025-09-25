#!/usr/bin/env python3
"""
LightFM Volunteer Matching System with PostgreSQL
Complete application with user registration, authentication, and AI recommendations
"""

import os
import uuid
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# Flask and extensions
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, IntegerField, DecimalField, BooleanField, PasswordField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional as OptionalValidator
from werkzeug.security import generate_password_hash, check_password_hash

# Data processing and ML
import pandas as pd
import numpy as np
from lightfm import LightFM
from lightfm.data import Dataset
from sklearn.preprocessing import LabelEncoder
import pickle

# Utilities
from dotenv import load_dotenv
import bcrypt
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import text
from marshmallow import Schema, fields

# Load environment variables
load_dotenv()

# =============================================
# Flask Application Configuration
# =============================================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://lightfm_user:secure_password_123@localhost:5432/lightfm_volunteer_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_ENABLED'] = True

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================
# Database Models
# =============================================

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'student' or 'ngo'
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    student = db.relationship('Student', backref='user', uselist=False, cascade='all, delete-orphan')
    ngo = db.relationship('NGO', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def set_password(self, password: str):
        """Hash and set password"""
        salt_rounds = int(os.getenv('PASSWORD_SALT_ROUNDS', 12))
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=salt_rounds)).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        """Check password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def get_id(self):
        """Required for Flask-Login"""
        return str(self.id)

class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    university = db.Column(db.String(255))
    major = db.Column(db.String(255))
    year_of_study = db.Column(db.Integer)
    gpa = db.Column(db.Numeric(3,2))
    
    # Profile information
    bio = db.Column(db.Text)
    profile_picture_url = db.Column(db.String(500))
    
    # JSON fields for flexible data
    skills = db.Column(JSONB, default=[])
    interests = db.Column(JSONB, default=[])
    languages = db.Column(JSONB, default=[])
    availability = db.Column(JSONB, default={})
    
    # Preferences
    willingness_level = db.Column(db.String(50), default='medium')
    preferred_location = db.Column(db.String(255))
    max_distance_km = db.Column(db.Integer, default=50)
    transportation_available = db.Column(db.Boolean, default=False)
    volunteer_experience_years = db.Column(db.Integer, default=0)
    previous_volunteer_work = db.Column(db.Text)
    preferred_contact_method = db.Column(db.String(50), default='email')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    applications = db.relationship('Application', backref='student', cascade='all, delete-orphan')
    interactions = db.relationship('Interaction', backref='student', cascade='all, delete-orphan')
    saved_opportunities = db.relationship('SavedOpportunity', backref='student', cascade='all, delete-orphan')

class NGO(db.Model):
    __tablename__ = 'ngos'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    organization_name = db.Column(db.String(255), nullable=False)
    registration_number = db.Column(db.String(100))
    tax_id = db.Column(db.String(100))
    founded_year = db.Column(db.Integer)
    organization_size = db.Column(db.String(50))
    
    # Contact information
    contact_person_name = db.Column(db.String(255), nullable=False)
    contact_person_title = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    website_url = db.Column(db.String(500))
    
    # Location
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(100), default='USA')
    
    # Organization profile
    mission_statement = db.Column(db.Text)
    description = db.Column(db.Text)
    logo_url = db.Column(db.String(500))
    
    # JSON fields
    focus_areas = db.Column(JSONB, default=[])
    target_demographics = db.Column(JSONB, default=[])
    
    # Verification and trust
    is_verified = db.Column(db.Boolean, default=False)
    verification_date = db.Column(db.DateTime)
    trust_score = db.Column(db.Numeric(3,2), default=5.00)
    total_volunteers_hosted = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    opportunities = db.relationship('Opportunity', backref='ngo', cascade='all, delete-orphan')

class Opportunity(db.Model):
    __tablename__ = 'opportunities'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ngo_id = db.Column(UUID(as_uuid=True), db.ForeignKey('ngos.id'), nullable=False)
    
    # Opportunity details
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text)
    responsibilities = db.Column(db.Text)
    benefits = db.Column(db.Text)
    
    # Skills and qualifications
    required_skills = db.Column(JSONB, default=[])
    preferred_skills = db.Column(JSONB, default=[])
    minimum_age = db.Column(db.Integer, default=16)
    background_check_required = db.Column(db.Boolean, default=False)
    
    # Time and commitment
    time_commitment = db.Column(db.String(100))
    schedule_flexibility = db.Column(db.String(50), default='flexible')
    available_days = db.Column(JSONB, default=[])
    available_hours = db.Column(JSONB, default={})
    
    # Location
    is_remote = db.Column(db.Boolean, default=False)
    location_address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    
    # Management
    status = db.Column(db.String(50), default='active')
    urgency_level = db.Column(db.String(50), default='medium')
    max_volunteers = db.Column(db.Integer, default=1)
    current_volunteers = db.Column(db.Integer, default=0)
    
    # Dates
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    application_deadline = db.Column(db.Date)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    applications = db.relationship('Application', backref='opportunity', cascade='all, delete-orphan')
    interactions = db.relationship('Interaction', backref='opportunity', cascade='all, delete-orphan')

class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey('students.id'), nullable=False)
    opportunity_id = db.Column(UUID(as_uuid=True), db.ForeignKey('opportunities.id'), nullable=False)
    
    # Application details
    cover_letter = db.Column(db.Text)
    additional_info = db.Column(db.Text)
    motivation = db.Column(db.Text)
    
    # Status
    status = db.Column(db.String(50), default='pending')
    ngo_notes = db.Column(db.Text)
    student_notes = db.Column(db.Text)
    
    # Dates
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    decision_date = db.Column(db.DateTime)

class Interaction(db.Model):
    __tablename__ = 'interactions'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey('students.id'), nullable=False)
    opportunity_id = db.Column(UUID(as_uuid=True), db.ForeignKey('opportunities.id'), nullable=False)
    
    interaction_type = db.Column(db.String(50), nullable=False)  # 'view', 'save', 'apply', etc.
    rating = db.Column(db.Integer)
    feedback = db.Column(db.Text)
    duration_minutes = db.Column(db.Integer)
    device_type = db.Column(db.String(50))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SavedOpportunity(db.Model):
    __tablename__ = 'saved_opportunities'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey('students.id'), nullable=False)
    opportunity_id = db.Column(UUID(as_uuid=True), db.ForeignKey('opportunities.id'), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Recommendation(db.Model):
    __tablename__ = 'recommendations'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey('students.id'), nullable=False)
    opportunity_id = db.Column(UUID(as_uuid=True), db.ForeignKey('opportunities.id'), nullable=False)
    
    prediction_score = db.Column(db.Numeric(10, 6), nullable=False)
    confidence_level = db.Column(db.Numeric(5, 4))
    rank_position = db.Column(db.Integer)
    algorithm_version = db.Column(db.String(50))
    features_used = db.Column(JSONB)
    
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    
    was_clicked = db.Column(db.Boolean, default=False)
    was_applied = db.Column(db.Boolean, default=False)
    user_rating = db.Column(db.Integer)

# =============================================
# Flask-Login Configuration
# =============================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# =============================================
# Forms for User Input
# =============================================

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    user_type = SelectField('User Type', choices=[('student', 'Student'), ('ngo', 'NGO')], validators=[DataRequired()])

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

class StudentProfileForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=100)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Phone', validators=[OptionalValidator(), Length(max=20)])
    university = StringField('University', validators=[OptionalValidator(), Length(max=255)])
    major = StringField('Major', validators=[OptionalValidator(), Length(max=255)])
    year_of_study = IntegerField('Year of Study', validators=[OptionalValidator(), NumberRange(min=1, max=8)])
    bio = TextAreaField('Bio')
    skills = TextAreaField('Skills (comma-separated)')
    interests = TextAreaField('Interests (comma-separated)')
    willingness_level = SelectField('Willingness Level', 
                                  choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('very_high', 'Very High')])

class NGOProfileForm(FlaskForm):
    organization_name = StringField('Organization Name', validators=[DataRequired(), Length(max=255)])
    contact_person_name = StringField('Contact Person Name', validators=[DataRequired(), Length(max=255)])
    contact_person_title = StringField('Contact Person Title', validators=[OptionalValidator(), Length(max=100)])
    phone = StringField('Phone', validators=[OptionalValidator(), Length(max=20)])
    address = TextAreaField('Address')
    city = StringField('City', validators=[OptionalValidator(), Length(max=100)])
    state = StringField('State', validators=[OptionalValidator(), Length(max=100)])
    mission_statement = TextAreaField('Mission Statement')
    description = TextAreaField('Description')
    focus_areas = TextAreaField('Focus Areas (comma-separated)')

# =============================================
# LightFM Recommendation Engine
# =============================================

class LightFMRecommendationEngine:
    """Enhanced LightFM recommendation system with PostgreSQL integration"""
    
    def __init__(self):
        self.model = None
        self.dataset = None
        self.user_features = None
        self.item_features = None
        self.user_mappings = {}
        self.item_mappings = {}
        self.is_trained = False
        
    def prepare_data(self) -> bool:
        """Prepare data from PostgreSQL for LightFM training"""
        try:
            logger.info("🔄 Preparing data from PostgreSQL...")
            
            # Get all students with their features
            students_query = """
                SELECT s.id, s.user_id, s.skills, s.interests, s.willingness_level,
                       s.university, s.major, s.volunteer_experience_years
                FROM students s
                JOIN users u ON s.user_id = u.id
                WHERE u.is_active = true
            """
            students_df = pd.read_sql(students_query, db.engine)
            
            # Get all opportunities with their features  
            opportunities_query = """
                SELECT o.id, o.ngo_id, o.title, o.required_skills, o.urgency_level,
                       o.status, o.city, o.state, n.focus_areas, n.organization_name
                FROM opportunities o
                JOIN ngos n ON o.ngo_id = n.id
                WHERE o.status = 'active'
            """
            opportunities_df = pd.read_sql(opportunities_query, db.engine)
            
            # Get interactions
            interactions_query = """
                SELECT i.student_id, i.opportunity_id, i.interaction_type, i.rating,
                       i.created_at
                FROM interactions i
                WHERE i.rating IS NOT NULL
            """
            interactions_df = pd.read_sql(interactions_query, db.engine)
            
            if students_df.empty or opportunities_df.empty:
                logger.warning("⚠️ No data found in database")
                return False
            
            # Create LightFM dataset
            self.dataset = Dataset()
            
            # Prepare user and item features
            all_user_features = set()
            all_item_features = set()
            
            # Extract user features
            for _, student in students_df.iterrows():
                skills = student['skills'] if student['skills'] else []
                interests = student['interests'] if student['interests'] else []
                
                if isinstance(skills, str):
                    skills = json.loads(skills) if skills.strip() else []
                if isinstance(interests, str):
                    interests = json.loads(interests) if interests.strip() else []
                
                user_features = [f"skill_{skill.lower().replace(' ', '_')}" for skill in skills]
                user_features += [f"interest_{interest.lower().replace(' ', '_')}" for interest in interests]
                user_features += [f"willingness_{student['willingness_level']}"]
                
                if student['university']:
                    user_features.append(f"university_{student['university'].lower().replace(' ', '_')}")
                if student['major']:
                    user_features.append(f"major_{student['major'].lower().replace(' ', '_')}")
                
                all_user_features.update(user_features)
            
            # Extract item features
            for _, opp in opportunities_df.iterrows():
                required_skills = opp['required_skills'] if opp['required_skills'] else []
                focus_areas = opp['focus_areas'] if opp['focus_areas'] else []
                
                if isinstance(required_skills, str):
                    required_skills = json.loads(required_skills) if required_skills.strip() else []
                if isinstance(focus_areas, str):
                    focus_areas = json.loads(focus_areas) if focus_areas.strip() else []
                
                item_features = [f"required_{skill.lower().replace(' ', '_')}" for skill in required_skills]
                item_features += [f"focus_{area.lower().replace(' ', '_')}" for area in focus_areas]
                item_features += [f"urgency_{opp['urgency_level']}"]
                
                if opp['city']:
                    item_features.append(f"city_{opp['city'].lower().replace(' ', '_')}")
                if opp['state']:
                    item_features.append(f"state_{opp['state'].lower()}")
                
                all_item_features.update(item_features)
            
            # Convert UUIDs to strings for LightFM
            user_ids = [str(uid) for uid in students_df['id'].tolist()]
            item_ids = [str(oid) for oid in opportunities_df['id'].tolist()]
            
            # Fit the dataset
            self.dataset.fit(
                users=user_ids,
                items=item_ids,
                user_features=list(all_user_features),
                item_features=list(all_item_features)
            )
            
            logger.info(f"✅ Dataset prepared: {len(user_ids)} users, {len(item_ids)} items")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error preparing data: {str(e)}")
            return False
    
    def train_model(self) -> bool:
        """Train the LightFM model"""
        try:
            if not self.dataset:
                logger.error("❌ Dataset not prepared")
                return False
            
            logger.info("🚀 Training LightFM model...")
            
            # Initialize model
            components = int(os.getenv('LIGHTFM_COMPONENTS', 50))
            learning_rate = float(os.getenv('LIGHTFM_LEARNING_RATE', 0.05))
            loss = os.getenv('LIGHTFM_LOSS', 'warp')
            
            self.model = LightFM(
                loss=loss,
                no_components=components,
                learning_rate=learning_rate,
                random_state=42
            )
            
            # Get interactions matrix
            interactions_query = """
                SELECT i.student_id, i.opportunity_id, 
                       CASE 
                           WHEN i.rating IS NOT NULL THEN i.rating
                           WHEN i.interaction_type = 'apply' THEN 5
                           WHEN i.interaction_type = 'save' THEN 4
                           WHEN i.interaction_type = 'view' THEN 3
                           ELSE 1
                       END as implicit_rating
                FROM interactions i
            """
            interactions_df = pd.read_sql(interactions_query, db.engine)
            
            if interactions_df.empty:
                # Create synthetic interactions for cold start
                logger.info("🔄 Creating synthetic interactions for cold start...")
                interactions_df = self._create_synthetic_interactions()
            
            # Convert to string IDs
            interactions_df['student_id'] = interactions_df['student_id'].astype(str)
            interactions_df['opportunity_id'] = interactions_df['opportunity_id'].astype(str)
            
            # Build interactions matrix
            interactions, weights = self.dataset.build_interactions(
                [(row['student_id'], row['opportunity_id'], row['implicit_rating']) 
                 for _, row in interactions_df.iterrows()]
            )
            
            # Train model
            epochs = int(os.getenv('LIGHTFM_EPOCHS', 10))
            self.model.fit(interactions, sample_weight=weights, epochs=epochs, verbose=True)
            
            self.is_trained = True
            logger.info("✅ LightFM model trained successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error training model: {str(e)}")
            return False
    
    def _create_synthetic_interactions(self) -> pd.DataFrame:
        """Create synthetic interactions for cold start problem"""
        # Get random samples of students and opportunities
        students = db.session.query(Student.id).limit(50).all()
        opportunities = db.session.query(Opportunity.id).limit(50).all()
        
        synthetic_data = []
        np.random.seed(42)
        
        for student in students:
            # Create 3-5 random interactions per student
            n_interactions = np.random.randint(3, 6)
            selected_opps = np.random.choice(len(opportunities), n_interactions, replace=False)
            
            for opp_idx in selected_opps:
                synthetic_data.append({
                    'student_id': str(student[0]),
                    'opportunity_id': str(opportunities[opp_idx][0]),
                    'implicit_rating': np.random.randint(3, 6)  # 3-5 rating
                })
        
        return pd.DataFrame(synthetic_data)
    
    def get_recommendations(self, student_id: str, num_recommendations: int = 5) -> List[Dict]:
        """Get recommendations for a specific student"""
        try:
            if not self.is_trained:
                logger.warning("⚠️ Model not trained yet")
                return []
            
            # Get student internal ID
            user_id, user_features = self.dataset.build_user_features([(student_id, [])])
            
            # Get all items
            all_opportunities = db.session.query(Opportunity).filter_by(status='active').all()
            item_ids = [str(opp.id) for opp in all_opportunities]
            
            # Get predictions
            item_internal_ids = np.array([self.dataset.mapping()[2][item_id] for item_id in item_ids 
                                        if item_id in self.dataset.mapping()[2]])
            
            if len(item_internal_ids) == 0:
                return []
            
            user_internal_id = self.dataset.mapping()[0].get(student_id)
            if user_internal_id is None:
                return []
            
            scores = self.model.predict(user_internal_id, item_internal_ids)
            
            # Get top recommendations
            top_indices = np.argsort(-scores)[:num_recommendations]
            
            recommendations = []
            for idx in top_indices:
                item_internal_id = item_internal_ids[idx]
                # Find the actual opportunity ID
                for item_id, internal_id in self.dataset.mapping()[2].items():
                    if internal_id == item_internal_id:
                        opportunity = db.session.query(Opportunity).filter_by(id=item_id).first()
                        if opportunity:
                            recommendations.append({
                                'opportunity_id': str(opportunity.id),
                                'ngo_name': opportunity.ngo.organization_name,
                                'title': opportunity.title,
                                'description': opportunity.description,
                                'required_skills': opportunity.required_skills,
                                'urgency_level': opportunity.urgency_level,
                                'city': opportunity.city,
                                'prediction_score': float(scores[idx]),
                                'match_percentage': min(100, max(0, int((scores[idx] + 2) * 25)))
                            })
                        break
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Error getting recommendations: {str(e)}")
            return []

# Initialize recommendation engine
recommendation_engine = LightFMRecommendationEngine()

# =============================================
# Routes
# =============================================

@app.route('/')
def index():
    """Landing page"""
    return render_template('index_db.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter(
            (User.email == form.email.data) | (User.username == form.username.data)
        ).first()
        
        if existing_user:
            flash('User with this email or username already exists', 'error')
            return render_template('register.html', form=form)
        
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data,
            user_type=form.user_type.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        # Redirect to profile setup
        login_user(user)
        if user.user_type == 'student':
            return redirect(url_for('student_profile'))
        else:
            return redirect(url_for('ngo_profile'))
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Redirect based on user type
            if user.user_type == 'student':
                return redirect(url_for('student_dashboard'))
            else:
                return redirect(url_for('ngo_dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    return redirect(url_for('index'))

@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
def student_profile():
    """Student profile setup/edit"""
    if current_user.user_type != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    form = StudentProfileForm()
    student = current_user.student
    
    if form.validate_on_submit():
        if not student:
            student = Student(user_id=current_user.id)
            db.session.add(student)
        
        # Update student profile
        student.first_name = form.first_name.data
        student.last_name = form.last_name.data
        student.phone = form.phone.data
        student.university = form.university.data
        student.major = form.major.data
        student.year_of_study = form.year_of_study.data
        student.bio = form.bio.data
        student.willingness_level = form.willingness_level.data
        
        # Process skills and interests
        if form.skills.data:
            student.skills = [s.strip() for s in form.skills.data.split(',') if s.strip()]
        if form.interests.data:
            student.interests = [i.strip() for i in form.interests.data.split(',') if i.strip()]
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student_dashboard'))
    
    # Pre-populate form if student exists
    if student:
        form.first_name.data = student.first_name
        form.last_name.data = student.last_name
        form.phone.data = student.phone
        form.university.data = student.university
        form.major.data = student.major
        form.year_of_study.data = student.year_of_study
        form.bio.data = student.bio
        form.willingness_level.data = student.willingness_level
        form.skills.data = ', '.join(student.skills or [])
        form.interests.data = ', '.join(student.interests or [])
    
    return render_template('student_profile.html', form=form, student=student)

@app.route('/ngo/profile', methods=['GET', 'POST'])
@login_required
def ngo_profile():
    """NGO profile setup/edit"""
    if current_user.user_type != 'ngo':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    form = NGOProfileForm()
    ngo = current_user.ngo
    
    if form.validate_on_submit():
        if not ngo:
            ngo = NGO(user_id=current_user.id)
            db.session.add(ngo)
        
        # Update NGO profile
        ngo.organization_name = form.organization_name.data
        ngo.contact_person_name = form.contact_person_name.data
        ngo.contact_person_title = form.contact_person_title.data
        ngo.phone = form.phone.data
        ngo.address = form.address.data
        ngo.city = form.city.data
        ngo.state = form.state.data
        ngo.mission_statement = form.mission_statement.data
        ngo.description = form.description.data
        
        # Process focus areas
        if form.focus_areas.data:
            ngo.focus_areas = [f.strip() for f in form.focus_areas.data.split(',') if f.strip()]
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('ngo_dashboard'))
    
    # Pre-populate form if NGO exists
    if ngo:
        form.organization_name.data = ngo.organization_name
        form.contact_person_name.data = ngo.contact_person_name
        form.contact_person_title.data = ngo.contact_person_title
        form.phone.data = ngo.phone
        form.address.data = ngo.address
        form.city.data = ngo.city
        form.state.data = ngo.state
        form.mission_statement.data = ngo.mission_statement
        form.description.data = ngo.description
        form.focus_areas.data = ', '.join(ngo.focus_areas or [])
    
    return render_template('ngo_profile.html', form=form, ngo=ngo)

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    """Student dashboard"""
    if current_user.user_type != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    student = current_user.student
    if not student:
        flash('Please complete your profile first', 'warning')
        return redirect(url_for('student_profile'))
    
    return render_template('student_dashboard_db.html', student=student)

@app.route('/ngo/dashboard')
@login_required
def ngo_dashboard():
    """NGO dashboard"""
    if current_user.user_type != 'ngo':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    ngo = current_user.ngo
    if not ngo:
        flash('Please complete your profile first', 'warning')
        return redirect(url_for('ngo_profile'))
    
    opportunities = Opportunity.query.filter_by(ngo_id=ngo.id).all()
    return render_template('ngo_dashboard.html', ngo=ngo, opportunities=opportunities)

@app.route('/init_model')
def init_model():
    """Initialize the LightFM model"""
    try:
        if recommendation_engine.prepare_data() and recommendation_engine.train_model():
            return jsonify({
                'success': True,
                'message': 'LightFM model initialized successfully',
                'status': 'Model ready for recommendations'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to initialize model'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Model initialization failed: {str(e)}'
        }), 500

@app.route('/api/recommendations')
@login_required
def get_recommendations():
    """Get recommendations for current student"""
    if current_user.user_type != 'student':
        return jsonify({'error': 'Access denied'}), 403
    
    student = current_user.student
    if not student:
        return jsonify({'error': 'Student profile not found'}), 404
    
    recommendations = recommendation_engine.get_recommendations(str(student.id))
    
    return jsonify({
        'recommendations': recommendations,
        'profile': {
            'first_name': student.first_name,
            'last_name': student.last_name,
            'skills': student.skills or [],
            'interests': student.interests or [],
            'willingness_level': student.willingness_level,
            'university': student.university
        }
    })

# =============================================
# Application Initialization
# =============================================

def create_tables():
    """Create database tables"""
    with app.app_context():
        try:
            db.create_all()
            logger.info("✅ Database tables created successfully")
        except Exception as e:
            logger.error(f"❌ Error creating tables: {str(e)}")

if __name__ == '__main__':
    print("🚀 Starting LightFM Volunteer Matching System with PostgreSQL")
    print("=" * 60)
    print("📊 Features:")
    print("  ✅ PostgreSQL database integration")
    print("  ✅ User registration and authentication")  
    print("  ✅ Student and NGO profile management")
    print("  ✅ Real LightFM model training with database data")
    print("  ✅ Dynamic recommendation generation")
    print()
    print("🌐 Access at: http://localhost:5000")
    print("=" * 60)
    
    # Create database tables
    create_tables()
    
    # Initialize recommendation engine
    recommendation_engine.prepare_data()
    recommendation_engine.train_model()
    
    app.run(host='0.0.0.0', port=5000, debug=True)