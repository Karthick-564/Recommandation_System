#!/usr/bin/env python3
"""
full_pipeline_normalized.py

End-to-end pipeline:
 - Loads students.csv, opportunities.csv, interactions.csv
 - Normalizes tokens so user skills and opportunity required skills use the same tokens
 - Builds LightFM Dataset + feature matrices
 - Trains LightFM (WARP)
 - Saves model_data.pkl and lightfm_model.pkl
 - Prints demo recommendations with friendly scores and matched tokens

CSV expectations (flexible):
 - students.csv: student_id, skills, interests, willingness (text), work_calendar (comma sep), optional transport_access
 - opportunities.csv: opportunity_id, ngo_name/title, description, required_skills, importance_level, work_calendar
 - interactions.csv: student_id, opportunity_id, interaction (numeric weight) OR action_type (view/save/apply) and optional certainty_factor

Run:
    python3 full_pipeline_normalized.py
"""

import os
import pickle
from typing import List, Set, Tuple, Dict, Any

import numpy as np
import pandas as pd

try:
    from lightfm.data import Dataset
    from lightfm import LightFM
except Exception as e:
    raise RuntimeError("LightFM not installed in your venv. Install with: pip install lightfm") from e

# ---------------- Config ----------------
ACTION_WEIGHT = {'view': 0.3, 'save': 0.6, 'apply': 1.0}
IMPORTANCE_MAP = {'emerg': 5, 'emergency': 5, 'high': 4, 'standard': 3, 'std': 3, 'low': 1}
WILLINGNESS_MAP = {'very_high': 5, 'high': 5, 'medium': 3, 'med': 3, 'low': 1}

# ---------------- Helpers ----------------
def read_csv_flex(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found")
    # use python engine to better tolerate quoted commas
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=['', 'NA', 'N/A'], engine='python')

def safe_split(x) -> List[str]:
    if pd.isna(x) or x is None:
        return []
    if isinstance(x, (list, tuple)):
        return [str(i).strip() for i in x if str(i).strip()]
    return [t.strip() for t in str(x).split(',') if t.strip()]

def norm_token(tok: str) -> str:
    t = str(tok).strip().lower()
    t = t.replace(' ', '').replace('-', '').replace('.', '')
    t = t.strip('>\n\r\t ')
    return t

def skill_token(tok: str) -> str:
    return f"skill:{norm_token(tok)}"

def interest_token(tok: str) -> str:
    return f"interest:{norm_token(tok)}"

def city_token(tok: str) -> str:
    return f"city:{norm_token(tok)}"

def availability_token(tok: str) -> str:
    return f"avail:{norm_token(tok)}"

def willingness_token(val) -> str:
    if pd.isna(val) or val is None:
        return "willingness:3"
    s = str(val).strip().lower()
    for k, v in WILLINGNESS_MAP.items():
        if k in s:
            return f"willingness:{v}"
    if 'high' in s:
        return "willingness:5"
    if 'med' in s:
        return "willingness:3"
    if 'low' in s:
        return "willingness:1"
    try:
        n = int(round(float(s)))
        n = max(1, min(5, n))
        return f"willingness:{n}"
    except Exception:
        return "willingness:3"

def importance_token(val) -> str:
    if pd.isna(val) or val is None:
        return "importance:3"
    s = str(val).strip().lower()
    for k, v in IMPORTANCE_MAP.items():
        if k in s:
            return f"importance:{v}"
    try:
        n = int(round(float(s)))
        n = max(1, min(5, n))
        return f"importance:{n}"
    except Exception:
        return "importance:3"

def duration_token(val) -> str:
    try:
        d = float(str(val))
        if d <= 2:
            return "duration:short"
        if d <= 6:
            return "duration:medium"
        return "duration:long"
    except Exception:
        return "duration:unknown"

def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))

# ---------------- Feature construction ----------------
def build_feature_lists(students: pd.DataFrame, opps: pd.DataFrame) -> Tuple[List[Tuple[int, List[str]]], List[Tuple[int, List[str]]], Set[str], Set[str]]:
    user_features_list = []
    item_features_list = []
    all_user_feats = set()
    all_item_feats = set()

    # Users: expect 'uid_int'
    for _, r in students.iterrows():
        uid = int(r['uid_int'])
        feats = []

        for s in safe_split(r.get('skills', '')):
            t = skill_token(s)
            feats.append(t); all_user_feats.add(t)
        for it in safe_split(r.get('interests', '')):
            t = interest_token(it)
            feats.append(t); all_user_feats.add(t)
        if 'city' in r and r.get('city'):
            t = city_token(r.get('city')); feats.append(t); all_user_feats.add(t)
        for d in safe_split(r.get('work_calendar', r.get('availability', ''))):
            t = availability_token(d); feats.append(t); all_user_feats.add(t)
        if 'willingness' in r and r.get('willingness'):
            t = willingness_token(r.get('willingness')); feats.append(t); all_user_feats.add(t)
        if 'transport_access' in r and r.get('transport_access'):
            v = str(r.get('transport_access')).strip().lower()
            t = 'transport:yes' if v in ('1','true','t','yes','y') else 'transport:no'
            feats.append(t); all_user_feats.add(t)

        user_features_list.append((uid, feats))

    # Items: expect 'iid_int'
    for _, r in opps.iterrows():
        iid = int(r['iid_int'])
        feats = []

        for s in safe_split(r.get('required_skills', '')):
            # use same token prefix 'skill' for required skills to allow matching
            t = skill_token(s)
            feats.append(t); all_item_feats.add(t)
        if 'cause_type' in r and r.get('cause_type'):
            t = f"cause:{norm_token(r.get('cause_type'))}"; feats.append(t); all_item_feats.add(t)
        if 'city' in r and r.get('city'):
            t = city_token(r.get('city')); feats.append(t); all_item_feats.add(t)
        if 'importance_level' in r and r.get('importance_level'):
            t = importance_token(r.get('importance_level')); feats.append(t); all_item_feats.add(t)
        for d in safe_split(r.get('work_calendar', '')):
            t = availability_token(d); feats.append(t); all_item_feats.add(t)
        if 'duration_hours' in r and r.get('duration_hours'):
            t = duration_token(r.get('duration_hours')); feats.append(t); all_item_feats.add(t)
        if 'certification_offered' in r and r.get('certification_offered'):
            v = str(r.get('certification_offered')).strip().lower()
            t = 'cert:yes' if v in ('1','true','t','yes','y') else 'cert:no'
            feats.append(t); all_item_feats.add(t)

        item_features_list.append((iid, feats))

    return user_features_list, item_features_list, all_user_feats, all_item_feats

# ---------------- Main pipeline ----------------
def build_dataset_from_csvs(students_csv='students.csv', opp_csv='opportunities.csv', interactions_csv='interactions.csv', out_pkl='model_data.pkl'):
    print("Loading CSVs...")
    students = read_csv_flex(students_csv)
    opps = read_csv_flex(opp_csv)
    interactions = read_csv_flex(interactions_csv)

    # Ensure core id columns exist
    if 'student_id' not in students.columns:
        students.insert(0, 'student_id', students.iloc[:, 0].astype(str))
    if 'opportunity_id' not in opps.columns:
        opps.insert(0, 'opportunity_id', opps.iloc[:, 0].astype(str))
    if 'student_id' not in interactions.columns or 'opportunity_id' not in interactions.columns:
        raise ValueError("interactions.csv must contain 'student_id' and 'opportunity_id' columns")

    # prepare original id strings
    students['student_id_orig'] = students['student_id'].astype(str)
    opps['opportunity_id_orig'] = opps['opportunity_id'].astype(str)
    interactions['student_id_orig'] = interactions['student_id'].astype(str)
    interactions['opportunity_id_orig'] = interactions['opportunity_id'].astype(str)

    # build unique lists including ids that only appear in interactions
    unique_students = list(students['student_id_orig'].tolist())
    for s in interactions['student_id_orig'].unique():
        if s not in unique_students:
            unique_students.append(s)
    unique_opps = list(opps['opportunity_id_orig'].tolist())
    for o in interactions['opportunity_id_orig'].unique():
        if o not in unique_opps:
            unique_opps.append(o)

    user_to_int = {orig: i for i, orig in enumerate(unique_students)}
    int_to_user = {i: orig for orig, i in user_to_int.items()}
    item_to_int = {orig: i for i, orig in enumerate(unique_opps)}
    int_to_item = {i: orig for orig, i in item_to_int.items()}

    students['uid_int'] = students['student_id_orig'].map(user_to_int)
    opps['iid_int'] = opps['opportunity_id_orig'].map(item_to_int)
    interactions['uid_int'] = interactions['student_id_orig'].map(user_to_int)
    interactions['iid_int'] = interactions['opportunity_id_orig'].map(item_to_int)

    print(f"Total users: {len(user_to_int)}, total items: {len(item_to_int)}")

    # Build feature lists with normalized tokens (skills use same prefix)
    user_feats_list, item_feats_list, all_user_feats, all_item_feats = build_feature_lists(students, opps)

    # Use union of all features so mapping includes everything
    all_feats = set(all_user_feats).union(set(all_item_feats))

    # Fit LightFM dataset
    ds = Dataset()
    ds.fit(users=list(range(len(user_to_int))), items=list(range(len(item_to_int))),
           user_features=list(all_feats), item_features=list(all_feats))

    # Build interactions: prefer numeric 'interaction' column else fallback to action_type else default 1.0
    weight_col = 'interaction' if 'interaction' in interactions.columns and interactions['interaction'].astype(str).str.strip().replace('', 'nan').notna().any() else None
    has_action = 'action_type' in interactions.columns or 'action' in interactions.columns

    def interaction_gen():
        for _, r in interactions.iterrows():
            uid = int(r['uid_int'])
            iid = int(r['iid_int'])
            w = 1.0
            if weight_col:
                try:
                    w = float(r.get(weight_col, 1.0))
                except Exception:
                    w = 1.0
            elif has_action:
                act = str(r.get('action_type', r.get('action', ''))).strip().lower()
                w = ACTION_WEIGHT.get(act, 0.3)
                if 'certainty_factor' in r and r['certainty_factor']:
                    try: w *= float(r['certainty_factor'])
                    except Exception: pass
            else:
                w = 1.0
            yield (uid, iid, float(w))

    interactions_mat, weights_mat = ds.build_interactions(interaction_gen())

    user_feature_mat = ds.build_user_features(user_feats_list)
    item_feature_mat = ds.build_item_features(item_feats_list)

    payload = {
        'dataset': ds,
        'interactions': interactions_mat,
        'weights': weights_mat,
        'user_features': user_feature_mat,
        'item_features': item_feature_mat,
        'user_to_int': user_to_int,
        'int_to_user': int_to_user,
        'item_to_int': item_to_int,
        'int_to_item': int_to_item,
        'students_df': students,
        'opps_df': opps,
        'interactions_df': interactions
    }

    with open(out_pkl, 'wb') as f:
        pickle.dump(payload, f)
    print(f"Saved model data to {out_pkl}")
    return payload

# ---------------- Train and recommend ----------------
def train_and_save(payload_pkl='model_data.pkl', out_model='lightfm_model.pkl', epochs=12):
    with open(payload_pkl, 'rb') as f:
        payload = pickle.load(f)
    model = LightFM(loss='warp', no_components=30)
    print("Training LightFM model (WARP)...")
    model.fit(payload['interactions'], user_features=payload['user_features'], item_features=payload['item_features'], epochs=epochs, num_threads=4)
    with open(out_model, 'wb') as f:
        pickle.dump({'model': model, 'payload': payload}, f)
    print(f"Saved trained model to {out_model}")
    return model, payload

def recommend_for_student(original_student_id: Any, model_obj: Any, payload: Dict[str, Any], top_n: int = 5):
    user_to_int = payload['user_to_int']
    if str(original_student_id) not in user_to_int:
        raise KeyError(f"Student id {original_student_id} not in payload")
    uid = user_to_int[str(original_student_id)]
    num_users, num_items = payload['interactions'].shape
    raw_scores = model_obj.predict(uid, np.arange(num_items), user_features=payload['user_features'], item_features=payload['item_features'])
    top_idx = np.argsort(-raw_scores)[:top_n]
    # reconstruct student base tokens for explanation (normalized)
    students_df = payload['students_df']
    opps_df = payload['opps_df']
    stud_row = students_df[students_df['uid_int'] == uid]
    stud_base = set()
    if not stud_row.empty:
        r = stud_row.iloc[0]
        for s in safe_split(r.get('skills', '')):
            stud_base.add(norm_token(s))
        for it in safe_split(r.get('interests', '')):
            stud_base.add(norm_token(it))
        for d in safe_split(r.get('work_calendar', r.get('availability', ''))):
            stud_base.add(norm_token(d))

    results = []
    probs = sigmoid(raw_scores)  # friendly 0..1 display
    for iid in top_idx:
        orig_item = payload['int_to_item'][int(iid)]
        row = opps_df[opps_df['iid_int'] == iid]
        title = str(orig_item)
        item_base = set()
        if not row.empty:
            r = row.iloc[0]
            title = r.get('ngo_name', r.get('description', title))
            for s in safe_split(r.get('required_skills', '')):
                item_base.add(norm_token(s))
            for d in safe_split(r.get('work_calendar', '')):
                item_base.add(norm_token(d))
            # include importance mapped token in explanation if present
            if r.get('importance_level'):
                item_base.add(norm_token(r.get('importance_level')))

        matched = sorted(list(stud_base.intersection(item_base)))
        results.append({
            'opportunity_id': orig_item,
            'title': title,
            'raw_score': float(raw_scores[iid]),
            'score_0_1': float(probs[iid]),
            'matched_base_tokens': matched
        })
    return results

# ---------------- Script run ----------------
if __name__ == "__main__":
    students_csv = 'students.csv'
    opp_csv = 'opportunities.csv'
    interactions_csv = 'interactions.csv'

    payload = build_dataset_from_csvs(students_csv, opp_csv, interactions_csv, out_pkl='model_data.pkl')
    model, payload = train_and_save('model_data.pkl', 'lightfm_model.pkl', epochs=12)

    # Demo: show recommendations for first few students from students.csv
    print("\n=== Demo recommendations (first 10 students from students.csv) ===")
    sample_students = list(payload['students_df']['student_id_orig'].unique())[:10]
    for s in sample_students:
        try:
            recs = recommend_for_student(s, model, payload, top_n=5)
            print(f"\nStudent {s} recommendations:")
            for r in recs:
                print(f" - Opp {r['opportunity_id']}, score={r['score_0_1']:.3f}, matched={r['matched_base_tokens']}")
        except Exception as e:
            print(f"Could not produce recs for {s}: {e}")