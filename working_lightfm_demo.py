#!/usr/bin/env python3
"""
Simple Working LightFM Demo - Fixed Version
This version will definitely show recommendations!
"""

import pandas as pd
import numpy as np
from lightfm.data import Dataset
from lightfm import LightFM

def create_working_demo():
    print("🚀 Fixed LightFM Recommendation Demo")
    print("=" * 50)
    
    # Load data
    print("Loading data...")
    students_df = pd.read_csv('students.csv')
    opportunities_df = pd.read_csv('opportunities.csv')
    interactions_df = pd.read_csv('interactions.csv')
    
    print(f"✅ Loaded: {len(students_df)} students, {len(opportunities_df)} opportunities, {len(interactions_df)} interactions")
    
    # Convert IDs to strings
    students_df['student_id'] = students_df['student_id'].astype(str)
    opportunities_df['opportunity_id'] = opportunities_df['opportunity_id'].astype(str)
    interactions_df['student_id'] = interactions_df['student_id'].astype(str)
    interactions_df['opportunity_id'] = interactions_df['opportunity_id'].astype(str)
    
    # Create simple features
    print("Creating features...")
    
    # Get all unique skills (simplified)
    all_skills = set()
    for skills_str in pd.concat([students_df['skills'], opportunities_df['required_skills']]).dropna():
        skills = [s.strip().lower().replace(' ', '_') for s in str(skills_str).split(',')]
        all_skills.update(skills)
    
    skill_features = [f"skill_{skill}" for skill in sorted(all_skills)]
    print(f"✅ Created {len(skill_features)} skill features")
    
    # Create user and item mappings
    all_users = sorted(students_df['student_id'].unique())
    all_items = sorted(opportunities_df['opportunity_id'].unique())
    
    user_id_map = {user_id: idx for idx, user_id in enumerate(all_users)}
    item_id_map = {item_id: idx for idx, item_id in enumerate(all_items)}
    reverse_item_map = {idx: item_id for item_id, idx in item_id_map.items()}
    
    print(f"✅ Mapped {len(all_users)} users and {len(all_items)} items")
    
    # Build LightFM dataset
    print("Building LightFM dataset...")
    dataset = Dataset()
    dataset.fit(users=range(len(all_users)), 
                items=range(len(all_items)),
                user_features=skill_features,
                item_features=skill_features)
    
    # Build interactions
    interactions_list = []
    for _, row in interactions_df.iterrows():
        user_id = str(row['student_id'])
        item_id = str(row['opportunity_id'])
        if user_id in user_id_map and item_id in item_id_map:
            user_idx = user_id_map[user_id]
            item_idx = item_id_map[item_id]
            weight = float(row['interaction'])
            interactions_list.append((user_idx, item_idx, weight))
    
    interactions_matrix, weights_matrix = dataset.build_interactions(interactions_list)
    print(f"✅ Built interactions matrix: {interactions_matrix.shape}")
    
    # Build user features (simplified - just skills)
    user_features_list = []
    for user_id in all_users:
        user_idx = user_id_map[user_id]
        student_row = students_df[students_df['student_id'] == user_id].iloc[0]
        features = []
        
        if pd.notna(student_row['skills']):
            skills = [s.strip().lower().replace(' ', '_') for s in student_row['skills'].split(',')]
            features = [f"skill_{skill}" for skill in skills if f"skill_{skill}" in skill_features]
        
        user_features_list.append((user_idx, features))
    
    user_features_matrix = dataset.build_user_features(user_features_list)
    
    # Build item features (simplified - just required skills)
    item_features_list = []
    for item_id in all_items:
        item_idx = item_id_map[item_id]
        opp_row = opportunities_df[opportunities_df['opportunity_id'] == item_id].iloc[0]
        features = []
        
        if pd.notna(opp_row['required_skills']):
            skills = [s.strip().lower().replace(' ', '_') for s in opp_row['required_skills'].split(',')]
            features = [f"skill_{skill}" for skill in skills if f"skill_{skill}" in skill_features]
        
        item_features_list.append((item_idx, features))
    
    item_features_matrix = dataset.build_item_features(item_features_list)
    
    print(f"✅ Built feature matrices")
    
    # Train model (minimal epochs to avoid hanging)
    print("Training LightFM model (2 epochs only)...")
    model = LightFM(loss='warp', no_components=10, random_state=42)
    
    try:
        model.fit(interactions_matrix, 
                  user_features=user_features_matrix,
                  item_features=item_features_matrix,
                  epochs=2, 
                  num_threads=1, 
                  verbose=False)
        print("✅ Model training completed!")
    except Exception as e:
        print(f"❌ Training failed: {e}")
        return None
    
    # Generate recommendations
    def get_recommendations_for_student(student_id, n_recs=5):
        if student_id not in user_id_map:
            return []
        
        user_idx = user_id_map[student_id]
        n_items = len(all_items)
        
        # Get predictions
        scores = model.predict(user_idx, 
                              np.arange(n_items),
                              user_features=user_features_matrix,
                              item_features=item_features_matrix)
        
        # Get top items
        top_items = np.argsort(-scores)[:n_recs]
        
        recommendations = []
        for item_idx in top_items:
            item_id = reverse_item_map[item_idx]
            score = scores[item_idx]
            
            # Get opportunity details
            opp_info = opportunities_df[opportunities_df['opportunity_id'] == item_id].iloc[0]
            
            recommendations.append({
                'opportunity_id': item_id,
                'ngo_name': opp_info['ngo_name'],
                'description': opp_info['description'],
                'required_skills': opp_info['required_skills'],
                'importance_level': opp_info['importance_level'],
                'work_calendar': opp_info['work_calendar'],
                'score': float(score)
            })
        
        return recommendations
    
    # Test with multiple students
    print(f"\n🎯 TESTING RECOMMENDATIONS")
    print("=" * 60)
    
    test_students = ['0', '1', '2', '3', '4']  # First 5 students
    
    for student_id in test_students:
        if student_id in user_id_map:
            print(f"\n👤 STUDENT {student_id}")
            print("-" * 30)
            
            # Show student profile
            student_info = students_df[students_df['student_id'] == student_id].iloc[0]
            print(f"Skills: {student_info['skills']}")
            print(f"Interests: {student_info['interests']}")
            print(f"Availability: {student_info['work_calendar']}")
            
            # Get recommendations
            recommendations = get_recommendations_for_student(student_id, n_recs=3)
            
            if recommendations:
                print(f"\n🏆 TOP 3 RECOMMENDATIONS:")
                for i, rec in enumerate(recommendations, 1):
                    print(f"{i}. {rec['ngo_name']}")
                    print(f"   Score: {rec['score']:.3f}")
                    print(f"   Required: {rec['required_skills']}")
                    print(f"   Priority: {rec['importance_level']}")
                    print()
            else:
                print("❌ No recommendations found")
    
    # Return the working components for the web app
    return {
        'model': model,
        'dataset': dataset,
        'user_id_map': user_id_map,
        'item_id_map': item_id_map,
        'reverse_item_map': reverse_item_map,
        'user_features_matrix': user_features_matrix,
        'item_features_matrix': item_features_matrix,
        'students_df': students_df,
        'opportunities_df': opportunities_df,
        'interactions_df': interactions_df,
        'get_recommendations': get_recommendations_for_student
    }

if __name__ == "__main__":
    model_data = create_working_demo()
    if model_data:
        print("\n✅ SUCCESS! The recommendation system is working!")
        print("🌐 Ready to create the web application...")
    else:
        print("\n❌ FAILED! Need to fix the model first.")