#!/usr/bin/env python3
"""
Quick LightFM Demo - Minimal Version
"""

import pandas as pd
import numpy as np
from lightfm.data import Dataset
from lightfm import LightFM

def quick_demo():
    print("🚀 Quick LightFM Demo")
    print("=" * 30)
    
    # Load data
    print("Loading data...")
    students_df = pd.read_csv('students.csv')
    opportunities_df = pd.read_csv('opportunities.csv')
    interactions_df = pd.read_csv('interactions.csv')
    
    print(f"Students: {len(students_df)}, Opportunities: {len(opportunities_df)}, Interactions: {len(interactions_df)}")
    
    # Simple feature extraction
    print("Creating simple features...")
    
    # Extract skills
    all_skills = set()
    for skills_str in pd.concat([students_df['skills'], opportunities_df['required_skills']]).dropna():
        skills = [s.strip().lower().replace(' ', '_') for s in str(skills_str).split(',')]
        all_skills.update(skills)
    
    skill_features = [f"skill_{skill}" for skill in sorted(all_skills)]
    print(f"Features: {len(skill_features)} skills")
    
    # Create mappings
    users = sorted(students_df['student_id'].astype(str).tolist())
    items = sorted(opportunities_df['opportunity_id'].astype(str).tolist())
    user_map = {u: i for i, u in enumerate(users)}
    item_map = {u: i for i, u in enumerate(items)}
    
    # Build dataset
    print("Building LightFM dataset...")
    dataset = Dataset()
    dataset.fit(users=range(len(users)), items=range(len(items)), item_features=skill_features)
    
    # Build interactions (simple)
    interactions_list = []
    for _, row in interactions_df.iterrows():
        user_id = str(row['student_id'])
        item_id = str(row['opportunity_id'])
        if user_id in user_map and item_id in item_map:
            interactions_list.append((user_map[user_id], item_map[item_id], float(row['interaction'])))
    
    interactions_matrix, _ = dataset.build_interactions(interactions_list)
    
    # Train simple model
    print("Training model (1 epoch)...")
    model = LightFM(loss='warp', no_components=5, random_state=42)
    model.fit(interactions_matrix, epochs=1, num_threads=1, verbose=False)
    
    # Generate sample recommendations
    print("\nSample Recommendations:")
    print("-" * 40)
    
    user_idx = 0  # First user
    user_id = users[user_idx]
    
    # Get scores
    scores = model.predict(user_idx, np.arange(len(items)))
    top_items = np.argsort(-scores)[:5]
    
    print(f"Student {user_id}:")
    student_info = students_df[students_df['student_id'].astype(str) == user_id].iloc[0]
    print(f"  Skills: {student_info['skills']}")
    print(f"  Interests: {student_info['interests']}")
    
    print(f"\nTop 5 recommendations:")
    for i, item_idx in enumerate(top_items, 1):
        item_id = items[item_idx]
        score = scores[item_idx]
        opp_info = opportunities_df[opportunities_df['opportunity_id'].astype(str) == item_id].iloc[0]
        print(f"  {i}. {opp_info['ngo_name']}")
        print(f"     Required: {opp_info['required_skills']}")
        print(f"     Score: {score:.3f}")
        print()
    
    print("✅ Demo completed!")

if __name__ == "__main__":
    quick_demo()