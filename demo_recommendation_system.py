#!/usr/bin/env python3
"""
Complete LightFM Recommendation System Demo

This script demonstrates a working volunteer recommendation system using the sample data.
"""

import pandas as pd
import numpy as np
from lightfm.data import Dataset
from lightfm import LightFM
import pickle

def create_lightfm_model():
    """Create and train a LightFM recommendation model"""
    
    print("🚀 Starting LightFM Volunteer Recommendation System")
    print("=" * 60)
    
    # Load data
    print("📁 Loading datasets...")
    students_df = pd.read_csv('students.csv')
    opportunities_df = pd.read_csv('opportunities.csv')
    interactions_df = pd.read_csv('interactions.csv')
    
    print(f"   ✓ Students: {len(students_df)}")
    print(f"   ✓ Opportunities: {len(opportunities_df)}")
    print(f"   ✓ Interactions: {len(interactions_df)}")
    
    # Convert IDs to strings for consistency
    students_df['student_id'] = students_df['student_id'].astype(str)
    opportunities_df['opportunity_id'] = opportunities_df['opportunity_id'].astype(str)
    interactions_df['student_id'] = interactions_df['student_id'].astype(str)
    interactions_df['opportunity_id'] = interactions_df['opportunity_id'].astype(str)
    
    # Extract unique features
    print("\n🔍 Extracting features...")
    
    # Get all unique skills
    all_skills = set()
    for skills_str in students_df['skills'].dropna():
        skills = [s.strip().lower().replace(' ', '_') for s in skills_str.split(',')]
        all_skills.update(skills)
    
    for skills_str in opportunities_df['required_skills'].dropna():
        skills = [s.strip().lower().replace(' ', '_') for s in skills_str.split(',')]
        all_skills.update(skills)
    
    # Get all unique interests/project types
    all_interests = set()
    for interest_str in students_df['interests'].dropna():
        interests = [i.strip().lower().replace(' ', '_') for i in interest_str.split(',')]
        all_interests.update(interests)
    
    # Extract project types from descriptions
    for desc in opportunities_df['description'].dropna():
        desc_lower = desc.lower()
        if 'youth education' in desc_lower:
            all_interests.add('youth_education')
        elif 'community outreach' in desc_lower:
            all_interests.add('community_outreach')
        elif 'animal welfare' in desc_lower:
            all_interests.add('animal_welfare')
        elif 'conservation' in desc_lower:
            all_interests.add('conservation')
        elif 'fundraising' in desc_lower:
            all_interests.add('fundraising')
        elif 'mentoring' in desc_lower:
            all_interests.add('mentoring')
        elif 'robotics' in desc_lower:
            all_interests.add('robotics')
        elif 'tech development' in desc_lower:
            all_interests.add('tech_development')
        elif 'data analysis' in desc_lower:
            all_interests.add('data_analysis')
        elif 'scientific studies' in desc_lower:
            all_interests.add('scientific_studies')
        elif 'community service' in desc_lower:
            all_interests.add('community_service')
    
    # Get all unique days
    all_days = set()
    for calendar_str in students_df['work_calendar'].dropna():
        days = [d.strip().lower() for d in calendar_str.split(',')]
        all_days.update(days)
    
    for calendar_str in opportunities_df['work_calendar'].dropna():
        days = [d.strip().lower() for d in calendar_str.split(',')]
        all_days.update(days)
    
    # Create feature sets with prefixes
    skill_features = [f"skill_{skill}" for skill in all_skills]
    interest_features = [f"interest_{interest}" for interest in all_interests]
    day_features = [f"day_{day}" for day in all_days]
    willingness_features = [f"willingness_{level}" for level in ['low', 'medium', 'high']]
    importance_features = [f"importance_{level}" for level in ['standard', 'high', 'emergency']]
    
    all_features = skill_features + interest_features + day_features + willingness_features + importance_features
    
    print(f"   ✓ Skills: {len(skill_features)}")
    print(f"   ✓ Interests/Project Types: {len(interest_features)}")
    print(f"   ✓ Days: {len(day_features)}")
    print(f"   ✓ Total features: {len(all_features)}")
    
    # Create user and item mappings
    unique_students = sorted(students_df['student_id'].unique())
    unique_opportunities = sorted(opportunities_df['opportunity_id'].unique())
    
    user_id_map = {user_id: idx for idx, user_id in enumerate(unique_students)}
    item_id_map = {item_id: idx for idx, item_id in enumerate(unique_opportunities)}
    
    # Initialize LightFM dataset
    print("\n🏗️  Building LightFM dataset...")
    dataset = Dataset()
    dataset.fit(users=range(len(unique_students)),
                items=range(len(unique_opportunities)),
                user_features=all_features,
                item_features=all_features)
    
    # Build interactions
    interactions_list = []
    for _, row in interactions_df.iterrows():
        if row['student_id'] in user_id_map and row['opportunity_id'] in item_id_map:
            user_idx = user_id_map[row['student_id']]
            item_idx = item_id_map[row['opportunity_id']]
            weight = float(row['interaction'])
            interactions_list.append((user_idx, item_idx, weight))
    
    interactions_matrix, weights_matrix = dataset.build_interactions(interactions_list)
    
    # Build user features
    user_features_list = []
    for _, student in students_df.iterrows():
        user_idx = user_id_map[student['student_id']]
        features = []
        
        # Skills
        if pd.notna(student['skills']):
            skills = [s.strip().lower().replace(' ', '_') for s in student['skills'].split(',')]
            features.extend([f"skill_{skill}" for skill in skills])
        
        # Interests
        if pd.notna(student['interests']):
            interests = [i.strip().lower().replace(' ', '_') for i in student['interests'].split(',')]
            features.extend([f"interest_{interest}" for interest in interests])
        
        # Availability
        if pd.notna(student['work_calendar']):
            days = [d.strip().lower() for d in student['work_calendar'].split(',')]
            features.extend([f"day_{day}" for day in days])
        
        # Willingness
        if pd.notna(student['willingness']):
            features.append(f"willingness_{student['willingness'].lower()}")
        
        user_features_list.append((user_idx, features))
    
    user_features_matrix = dataset.build_user_features(user_features_list)
    
    # Build item features
    item_features_list = []
    for _, opportunity in opportunities_df.iterrows():
        item_idx = item_id_map[opportunity['opportunity_id']]
        features = []
        
        # Required skills
        if pd.notna(opportunity['required_skills']):
            skills = [s.strip().lower().replace(' ', '_') for s in opportunity['required_skills'].split(',')]
            features.extend([f"skill_{skill}" for skill in skills])
        
        # Project type (from description)
        if pd.notna(opportunity['description']):
            desc_lower = opportunity['description'].lower()
            if 'youth education' in desc_lower:
                features.append('interest_youth_education')
            elif 'community outreach' in desc_lower:
                features.append('interest_community_outreach')
            elif 'animal welfare' in desc_lower:
                features.append('interest_animal_welfare')
            elif 'conservation' in desc_lower:
                features.append('interest_conservation')
            elif 'fundraising' in desc_lower:
                features.append('interest_fundraising')
            elif 'mentoring' in desc_lower:
                features.append('interest_mentoring')
            elif 'robotics' in desc_lower:
                features.append('interest_robotics')
            elif 'tech development' in desc_lower:
                features.append('interest_tech_development')
            elif 'data analysis' in desc_lower:
                features.append('interest_data_analysis')
            elif 'scientific studies' in desc_lower:
                features.append('interest_scientific_studies')
            elif 'community service' in desc_lower:
                features.append('interest_community_service')
        
        # Work schedule
        if pd.notna(opportunity['work_calendar']):
            days = [d.strip().lower() for d in opportunity['work_calendar'].split(',')]
            features.extend([f"day_{day}" for day in days])
        
        # Importance level
        if pd.notna(opportunity['importance_level']):
            features.append(f"importance_{opportunity['importance_level'].lower()}")
        
        item_features_list.append((item_idx, features))
    
    item_features_matrix = dataset.build_item_features(item_features_list)
    
    # Train the model
    print("\n🎯 Training LightFM model...")
    model = LightFM(loss='warp', no_components=20, learning_rate=0.05, random_state=42)
    model.fit(interactions_matrix,
              user_features=user_features_matrix,
              item_features=item_features_matrix,
              epochs=10,
              num_threads=1)
    
    print("   ✓ Model training completed!")
    
    return {
        'model': model,
        'dataset': dataset,
        'user_id_map': user_id_map,
        'item_id_map': item_id_map,
        'user_features_matrix': user_features_matrix,
        'item_features_matrix': item_features_matrix,
        'students_df': students_df,
        'opportunities_df': opportunities_df,
        'interactions_df': interactions_df
    }

def get_recommendations(model_data, student_id, n_recommendations=5):
    """Get recommendations for a specific student"""
    model = model_data['model']
    user_id_map = model_data['user_id_map']
    item_id_map = model_data['item_id_map']
    reverse_item_map = {v: k for k, v in item_id_map.items()}
    
    if str(student_id) not in user_id_map:
        return []
    
    user_idx = user_id_map[str(student_id)]
    n_items = len(item_id_map)
    
    # Get predictions
    scores = model.predict(user_idx, 
                          np.arange(n_items),
                          user_features=model_data['user_features_matrix'],
                          item_features=model_data['item_features_matrix'])
    
    # Get top recommendations
    top_items = np.argsort(-scores)[:n_recommendations]
    
    recommendations = []
    for item_idx in top_items:
        item_id = reverse_item_map[item_idx]
        score = scores[item_idx]
        
        # Get opportunity details
        opp = model_data['opportunities_df'][
            model_data['opportunities_df']['opportunity_id'] == item_id
        ].iloc[0]
        
        recommendations.append({
            'opportunity_id': item_id,
            'ngo_name': opp['ngo_name'],
            'description': opp['description'],
            'required_skills': opp['required_skills'],
            'importance_level': opp['importance_level'],
            'work_calendar': opp['work_calendar'],
            'score': float(score)
        })
    
    return recommendations

def demonstrate_system():
    """Demonstrate the recommendation system"""
    
    # Create and train model
    model_data = create_lightfm_model()
    
    # Demonstrate recommendations
    print("\n🎯 RECOMMENDATION DEMONSTRATIONS")
    print("=" * 60)
    
    students_df = model_data['students_df']
    sample_students = ['0', '1', '2', '3', '4']  # First 5 students
    
    for student_id in sample_students:
        if str(student_id) in model_data['user_id_map']:
            print(f"\n👤 STUDENT {student_id}")
            print("-" * 30)
            
            # Get student info
            student_info = students_df[students_df['student_id'] == student_id].iloc[0]
            print(f"Skills: {student_info['skills']}")
            print(f"Interests: {student_info['interests']}")
            print(f"Willingness: {student_info['willingness']}")
            print(f"Available: {student_info['work_calendar']}")
            
            # Get recommendations
            recommendations = get_recommendations(model_data, student_id, n_recommendations=3)
            
            print(f"\n🎯 TOP 3 RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"\n{i}. {rec['ngo_name']}")
                print(f"   📋 {rec['description']}")
                print(f"   🛠️  Required: {rec['required_skills']}")
                print(f"   ⭐ Priority: {rec['importance_level']}")
                print(f"   📅 Schedule: {rec['work_calendar']}")
                print(f"   🎯 Score: {rec['score']:.3f}")
    
    # Save model
    print(f"\n💾 Saving model to 'lightfm_model.pkl'...")
    with open('lightfm_model.pkl', 'wb') as f:
        pickle.dump(model_data, f)
    
    print("\n✅ Demo completed successfully!")
    print("📊 Model performance stats:")
    interactions_matrix = model_data['dataset'].build_interactions([
        (model_data['user_id_map'][row['student_id']], 
         model_data['item_id_map'][row['opportunity_id']], 
         row['interaction'])
        for _, row in model_data['interactions_df'].iterrows()
        if row['student_id'] in model_data['user_id_map'] 
        and row['opportunity_id'] in model_data['item_id_map']
    ])[0]
    
    print(f"   - Users: {interactions_matrix.shape[0]}")
    print(f"   - Items: {interactions_matrix.shape[1]}")
    print(f"   - Interactions: {interactions_matrix.nnz}")
    print(f"   - Sparsity: {(1 - interactions_matrix.nnz / (interactions_matrix.shape[0] * interactions_matrix.shape[1])) * 100:.2f}%")

if __name__ == "__main__":
    demonstrate_system()