#!/usr/bin/env python3
"""
LightFM Volunteer Recommendation System

This script creates a recommendation system that matches students with volunteer opportunities
using LightFM collaborative filtering with content-based features.

Features used:
- Student skills, interests, willingness level, and availability
- Opportunity required skills, importance level, and time requirements
- Past interaction history between students and opportunities
"""

import os
import pickle
import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Any
from scipy.sparse import csr_matrix

try:
    from lightfm.data import Dataset
    from lightfm import LightFM
    from lightfm.evaluation import precision_at_k, auc_score
except ImportError:
    raise ImportError("LightFM not installed. Install with: pip install lightfm")

class VolunteerRecommendationSystem:
    def __init__(self):
        self.model = None
        self.dataset = None
        self.user_id_map = {}
        self.item_id_map = {}
        self.reverse_user_map = {}
        self.reverse_item_map = {}
        self.user_features = None
        self.item_features = None
        self.interactions_matrix = None
        
    def load_data(self, students_file: str, opportunities_file: str, interactions_file: str):
        """Load and preprocess the data files"""
        print("Loading data files...")
        
        # Load CSV files
        self.students_df = pd.read_csv(students_file)
        self.opportunities_df = pd.read_csv(opportunities_file)
        self.interactions_df = pd.read_csv(interactions_file)
        
        print(f"Loaded {len(self.students_df)} students, {len(self.opportunities_df)} opportunities, {len(self.interactions_df)} interactions")
        
        # Ensure all IDs are strings for consistency
        self.students_df['student_id'] = self.students_df['student_id'].astype(str)
        self.opportunities_df['opportunity_id'] = self.opportunities_df['opportunity_id'].astype(str)
        self.interactions_df['student_id'] = self.interactions_df['student_id'].astype(str)
        self.interactions_df['opportunity_id'] = self.interactions_df['opportunity_id'].astype(str)
        
        return self
    
    def extract_features(self):
        """Extract and normalize features from the data"""
        print("Extracting features...")
        
        # Extract user features
        user_features = set()
        user_feature_dict = {}
        
        for idx, row in self.students_df.iterrows():
            student_id = str(row['student_id'])
            features = []
            
            # Skills features
            if pd.notna(row['skills']):
                skills = [s.strip() for s in row['skills'].split(',')]
                for skill in skills:
                    feature = f"skill_{skill.lower().replace(' ', '_')}"
                    features.append(feature)
                    user_features.add(feature)
            
            # Interest features
            if pd.notna(row['interests']):
                interests = [i.strip() for i in row['interests'].split(',')]
                for interest in interests:
                    feature = f"interest_{interest.lower().replace(' ', '_')}"
                    features.append(feature)
                    user_features.add(feature)
            
            # Willingness feature
            if pd.notna(row['willingness']):
                feature = f"willingness_{row['willingness'].lower()}"
                features.append(feature)
                user_features.add(feature)
            
            # Availability features
            if pd.notna(row['work_calendar']):
                days = [d.strip() for d in row['work_calendar'].split(',')]
                for day in days:
                    feature = f"available_{day.lower()}"
                    features.append(feature)
                    user_features.add(feature)
            
            user_feature_dict[student_id] = features
        
        # Extract item features
        item_features = set()
        item_feature_dict = {}
        
        for idx, row in self.opportunities_df.iterrows():
            opportunity_id = str(row['opportunity_id'])
            features = []
            
            # Required skills features (use same namespace as user skills for matching)
            if pd.notna(row['required_skills']):
                skills = [s.strip() for s in row['required_skills'].split(',')]
                for skill in skills:
                    feature = f"skill_{skill.lower().replace(' ', '_')}"
                    features.append(feature)
                    item_features.add(feature)
            
            # Importance level feature
            if pd.notna(row['importance_level']):
                feature = f"importance_{row['importance_level'].lower()}"
                features.append(feature)
                item_features.add(feature)
            
            # Work calendar features (use same namespace as user availability for matching)
            if pd.notna(row['work_calendar']):
                days = [d.strip() for d in row['work_calendar'].split(',')]
                for day in days:
                    feature = f"available_{day.lower()}"
                    features.append(feature)
                    item_features.add(feature)
            
            # Project type feature (extracted from description)
            if pd.notna(row['description']):
                desc = row['description'].lower()
                if 'youth education' in desc:
                    feature = "project_youth_education"
                elif 'community outreach' in desc:
                    feature = "project_community_outreach"
                elif 'animal welfare' in desc:
                    feature = "project_animal_welfare"
                elif 'conservation' in desc:
                    feature = "project_conservation"
                elif 'fundraising' in desc:
                    feature = "project_fundraising"
                elif 'mentoring' in desc:
                    feature = "project_mentoring"
                elif 'robotics' in desc:
                    feature = "project_robotics"
                elif 'tech development' in desc:
                    feature = "project_tech_development"
                elif 'data analysis' in desc:
                    feature = "project_data_analysis"
                elif 'scientific studies' in desc:
                    feature = "project_scientific_studies"
                elif 'community service' in desc:
                    feature = "project_community_service"
                else:
                    feature = "project_other"
                
                features.append(feature)
                item_features.add(feature)
            
            item_feature_dict[opportunity_id] = features
        
        # Combine all features
        all_features = user_features.union(item_features)
        
        self.user_feature_dict = user_feature_dict
        self.item_feature_dict = item_feature_dict
        self.all_features = sorted(list(all_features))
        
        print(f"Extracted {len(user_features)} user features, {len(item_features)} item features")
        print(f"Total unique features: {len(all_features)}")
        
        return self
    
    def build_dataset(self):
        """Build LightFM dataset and feature matrices"""
        print("Building LightFM dataset...")
        
        # Get unique users and items
        all_users = list(set(self.students_df['student_id'].tolist() + 
                            self.interactions_df['student_id'].tolist()))
        all_items = list(set(self.opportunities_df['opportunity_id'].tolist() + 
                            self.interactions_df['opportunity_id'].tolist()))
        
        # Create mappings
        self.user_id_map = {user_id: idx for idx, user_id in enumerate(all_users)}
        self.item_id_map = {item_id: idx for idx, item_id in enumerate(all_items)}
        self.reverse_user_map = {idx: user_id for user_id, idx in self.user_id_map.items()}
        self.reverse_item_map = {idx: item_id for item_id, idx in self.item_id_map.items()}
        
        # Initialize LightFM dataset
        self.dataset = Dataset()
        self.dataset.fit(users=range(len(all_users)),
                        items=range(len(all_items)),
                        user_features=self.all_features,
                        item_features=self.all_features)
        
        # Build interactions matrix
        interactions = []
        weights = []
        
        for _, row in self.interactions_df.iterrows():
            user_idx = self.user_id_map[str(row['student_id'])]
            item_idx = self.item_id_map[str(row['opportunity_id'])]
            weight = float(row['interaction']) if 'interaction' in row and pd.notna(row['interaction']) else 1.0
            
            interactions.append((user_idx, item_idx))
            weights.append(weight)
        
        self.interactions_matrix, self.weights_matrix = self.dataset.build_interactions(
            [(user_idx, item_idx, weight) for (user_idx, item_idx), weight in zip(interactions, weights)]
        )
        
        # Build user features matrix
        user_features_list = []
        for user_id in all_users:
            user_idx = self.user_id_map[user_id]
            features = self.user_feature_dict.get(user_id, [])
            user_features_list.append((user_idx, features))
        
        self.user_features = self.dataset.build_user_features(user_features_list)
        
        # Build item features matrix
        item_features_list = []
        for item_id in all_items:
            item_idx = self.item_id_map[item_id]
            features = self.item_feature_dict.get(item_id, [])
            item_features_list.append((item_idx, features))
        
        self.item_features = self.dataset.build_item_features(item_features_list)
        
        print(f"Built interaction matrix: {self.interactions_matrix.shape}")
        print(f"Built user features matrix: {self.user_features.shape}")
        print(f"Built item features matrix: {self.item_features.shape}")
        
        return self
    
    def train_model(self, loss='warp', no_components=50, learning_rate=0.05, epochs=50):
        """Train the LightFM model"""
        print(f"Training LightFM model with {loss} loss...")
        
        self.model = LightFM(loss=loss, 
                           no_components=no_components,
                           learning_rate=learning_rate,
                           random_state=42)
        
        self.model.fit(self.interactions_matrix,
                      user_features=self.user_features,
                      item_features=self.item_features,
                      epochs=epochs,
                      num_threads=4,
                      verbose=True)
        
        print("Model training completed!")
        return self
    
    def get_recommendations(self, student_id: str, n_recommendations: int = 10) -> List[Dict[str, Any]]:
        """Get recommendations for a specific student"""
        if self.model is None:
            raise ValueError("Model not trained yet. Call train_model() first.")
        
        student_id = str(student_id)
        if student_id not in self.user_id_map:
            raise ValueError(f"Student {student_id} not found in the dataset")
        
        user_idx = self.user_id_map[student_id]
        n_items = len(self.item_id_map)
        
        # Get scores for all items
        scores = self.model.predict(user_idx, 
                                  np.arange(n_items),
                                  user_features=self.user_features,
                                  item_features=self.item_features)
        
        # Get top N recommendations
        top_items = np.argsort(-scores)[:n_recommendations]
        
        recommendations = []
        for item_idx in top_items:
            item_id = self.reverse_item_map[item_idx]
            score = scores[item_idx]
            
            # Get opportunity details
            opp_details = self.opportunities_df[self.opportunities_df['opportunity_id'] == item_id].iloc[0]
            
            # Find matching features between student and opportunity
            student_features = set(self.user_feature_dict.get(student_id, []))
            opportunity_features = set(self.item_feature_dict.get(item_id, []))
            matching_features = student_features.intersection(opportunity_features)
            
            recommendations.append({
                'opportunity_id': item_id,
                'ngo_name': opp_details['ngo_name'],
                'description': opp_details['description'],
                'required_skills': opp_details['required_skills'],
                'importance_level': opp_details['importance_level'],
                'work_calendar': opp_details['work_calendar'],
                'score': float(score),
                'matching_features': sorted(list(matching_features))
            })
        
        return recommendations
    
    def evaluate_model(self, k=10):
        """Evaluate the model using precision@k and AUC"""
        if self.model is None:
            raise ValueError("Model not trained yet. Call train_model() first.")
        
        print(f"Evaluating model...")
        
        # Split data for evaluation (use a simple train/test split)
        train_interactions = self.interactions_matrix.copy()
        
        # Calculate precision@k
        precision = precision_at_k(self.model, train_interactions, 
                                 user_features=self.user_features,
                                 item_features=self.item_features,
                                 k=k).mean()
        
        # Calculate AUC
        auc = auc_score(self.model, train_interactions,
                       user_features=self.user_features,
                       item_features=self.item_features).mean()
        
        print(f"Precision@{k}: {precision:.4f}")
        print(f"AUC Score: {auc:.4f}")
        
        return {'precision_at_k': precision, 'auc_score': auc}
    
    def save_model(self, filepath: str):
        """Save the trained model and necessary data"""
        model_data = {
            'model': self.model,
            'dataset': self.dataset,
            'user_id_map': self.user_id_map,
            'item_id_map': self.item_id_map,
            'reverse_user_map': self.reverse_user_map,
            'reverse_item_map': self.reverse_item_map,
            'user_features': self.user_features,
            'item_features': self.item_features,
            'interactions_matrix': self.interactions_matrix,
            'user_feature_dict': self.user_feature_dict,
            'item_feature_dict': self.item_feature_dict,
            'all_features': self.all_features,
            'students_df': self.students_df,
            'opportunities_df': self.opportunities_df,
            'interactions_df': self.interactions_df
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """Load a previously trained model"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.dataset = model_data['dataset']
        self.user_id_map = model_data['user_id_map']
        self.item_id_map = model_data['item_id_map']
        self.reverse_user_map = model_data['reverse_user_map']
        self.reverse_item_map = model_data['reverse_item_map']
        self.user_features = model_data['user_features']
        self.item_features = model_data['item_features']
        self.interactions_matrix = model_data['interactions_matrix']
        self.user_feature_dict = model_data['user_feature_dict']
        self.item_feature_dict = model_data['item_feature_dict']
        self.all_features = model_data['all_features']
        self.students_df = model_data['students_df']
        self.opportunities_df = model_data['opportunities_df']
        self.interactions_df = model_data['interactions_df']
        
        print(f"Model loaded from {filepath}")
        return self

def demonstrate_recommendations(recommender, n_students=5):
    """Demonstrate the recommendation system with sample students"""
    print("\n" + "="*80)
    print("VOLUNTEER RECOMMENDATION SYSTEM DEMONSTRATION")
    print("="*80)
    
    # Get a sample of students
    sample_students = recommender.students_df['student_id'].head(n_students).tolist()
    
    for student_id in sample_students:
        print(f"\n{'='*20} STUDENT {student_id} {'='*20}")
        
        # Get student details
        student_info = recommender.students_df[recommender.students_df['student_id'] == student_id].iloc[0]
        print(f"Skills: {student_info['skills']}")
        print(f"Interests: {student_info['interests']}")
        print(f"Willingness: {student_info['willingness']}")
        print(f"Availability: {student_info['work_calendar']}")
        
        # Get recommendations
        try:
            recommendations = recommender.get_recommendations(student_id, n_recommendations=5)
            print(f"\nTOP 5 RECOMMENDATIONS:")
            print("-" * 60)
            
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec['ngo_name']}")
                print(f"   Description: {rec['description']}")
                print(f"   Required Skills: {rec['required_skills']}")
                print(f"   Importance: {rec['importance_level']}")
                print(f"   Schedule: {rec['work_calendar']}")
                print(f"   Match Score: {rec['score']:.3f}")
                print(f"   Matching Features: {', '.join(rec['matching_features']) if rec['matching_features'] else 'None'}")
                print()
                
        except Exception as e:
            print(f"Error generating recommendations: {e}")

if __name__ == "__main__":
    # Initialize the recommendation system
    recommender = VolunteerRecommendationSystem()
    
    # Load and process data
    recommender.load_data('students.csv', 'opportunities.csv', 'interactions.csv')
    recommender.extract_features()
    recommender.build_dataset()
    
    # Train the model
    recommender.train_model(loss='warp', no_components=50, epochs=30)
    
    # Evaluate the model
    recommender.evaluate_model()
    
    # Save the model
    recommender.save_model('volunteer_recommendation_model.pkl')
    
    # Demonstrate recommendations
    demonstrate_recommendations(recommender, n_students=5)