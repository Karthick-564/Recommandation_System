#!/usr/bin/env python3
"""
Simple test of the LightFM Recommendation System
"""

from lightfm_recommendation_system import VolunteerRecommendationSystem
import pandas as pd

def test_basic_functionality():
    print("Testing LightFM Volunteer Recommendation System")
    print("=" * 50)
    
    try:
        # Initialize the recommendation system
        recommender = VolunteerRecommendationSystem()
        
        # Load data
        print("Loading data...")
        recommender.load_data('students.csv', 'opportunities.csv', 'interactions.csv')
        
        # Extract features
        print("Extracting features...")
        recommender.extract_features()
        
        print(f"Sample user features: {list(recommender.user_feature_dict.keys())[:3]}")
        print(f"Sample item features: {list(recommender.item_feature_dict.keys())[:3]}")
        print(f"Total features: {len(recommender.all_features)}")
        
        # Build dataset
        print("Building dataset...")
        recommender.build_dataset()
        
        # Train model with fewer epochs for testing
        print("Training model (quick test)...")
        recommender.train_model(epochs=5, no_components=10)
        
        # Test recommendations for first student
        print("Getting sample recommendations...")
        student_id = recommender.students_df['student_id'].iloc[0]
        recommendations = recommender.get_recommendations(student_id, n_recommendations=3)
        
        print(f"\nRecommendations for Student {student_id}:")
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec['ngo_name']} (Score: {rec['score']:.3f})")
        
        print("\n✅ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_basic_functionality()