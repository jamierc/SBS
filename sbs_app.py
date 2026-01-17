import streamlit as st
import pandas as pd
import json
import os

# --- APP CONFIGURATION ---
st.set_page_config(page_title="SBS Strength Tracker", page_icon="💪", layout="centered")

HISTORY_FILE = "workout_history.json"

# --- DATA MAPPING (Extracted from your Spreadsheet) ---
# Maps frequencies and days to specific exercises
EXERCISE_MAP = {
  "2x": {
    "1": ["Squat", "Bench Press", "Romanian Deadlift", "DB OHP"],
    "2": ["Deadlift", "OHP", "Leg Press", "Incline Press"]
  },
  "3x": {
    "1": ["Squat", "Romanian Deadlift", "Incline Press", "Pull-downs"],
    "2": ["Bench Press", "OHP", "Leg Press", "Pull-ups"],
    "3": ["Deadlift", "Incline Press", "Leg Press", "DB OHP"]
  },
  "4x": {
    "1": ["Squat", "Incline Press", "Romanian Deadlift"],
    "2": ["Bench Press", "Leg Press", "DB OHP"],
    "3": ["Deadlift", "Incline Press"],
    "4": ["OHP", "Leg Press"]
  },
  "5x": {
    "1": ["Squat", "DB OHP"],
    "2": ["Bench Press", "Leg Press"],
    "3": ["Deadlift", "Incline Press"],
    "4": ["OHP", "Leg Press"],
    "5": ["Incline Press", "Romanian Deadlift"]
  },
  "6x": {
    "1": ["Squat", "Incline Press"],
    "2": ["DB OHP", "Romanian Deadlift"],
    "3": ["Bench Press", "Leg Press"],
    "4": ["Incline Press", "Leg Press"],
    "5": ["Deadlift"],
    "6": ["OHP"]
  }
}

# --- HELPER FUNCTIONS ---

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_history_entry(week, day, lift, reps, target):
    history = load_history()
    key = f"{lift}_w{week}_d{day}" # Unique key per lift per week per day
    history[key] = {
        "week": week,
        "day": day,
        "lift": lift,
        "reps": reps,
        "target": target
    }
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def get_next_tm(current_tm, reps_done, target_reps):
    """Calculates the NEW Training Max based on AMRAP performance."""
    diff = reps_done - target_reps
    
    if diff <= -2:
        return current_tm * 0.95
    elif diff == -1:
        return current_tm * 0.98
    elif diff == 0:
        return current_tm # No change
    elif diff == 1:
        return current_tm * 1.005
    elif diff == 2:
        return current_tm * 1.01
    elif diff == 3:
        return current_tm * 1.015
    elif diff == 4:
        return current_tm * 1.02
    else: # diff >= 5
        return current_tm * 1.03

# Spreadsheet Training Maxes at the start of Week 16
W16_TM_ANCHORS = {
    "Squat": 100.0, # Reset to 100 as per user request for Week 16 matching
    "Romanian Deadlift": 106.25, # Derived from 85kg / 0.8 intensity? No, user saw 85 in app but maybe wants 82.5.
    "Incline Press": 90.0,
    "Bench Press": 100.0,
    "OHP": 50.0,
    "Leg Press": 190.0,
    "Deadlift": 140.0,
    "DB OHP": 25.0
}

# Override with exact spreadsheet values found
W16_TM_ANCHORS = {
    "Squat": 101.5,
    "Romanian Deadlift": 113.7,
    "Incline Press": 96.0,
    "Bench Press": 107.2,
    "OHP": 50.2,
    "Leg Press": 216.0,
    "Deadlift": 150.8,
    "DB OHP": 25.5
}

def calculate_current_tm(lift, base_max, history, current_week, is_aux):
    """Calculates TM starting from the Week 16 Spreadsheet Anchor."""
    # Start with the Spreadsheet's Week 16 TM
    tm = W16_TM_ANCHORS.get(lift, base_max)
    logs = [f"W16 Spreadsheet Anchor: {tm}kg"]
    
    # Only apply history recorded IN THE APP from Week 16 onwards
    relevant_history = [
        v for k, v in history.items() 
        if v['lift'] == lift and 16 <= v['week'] < current_week
    ]
    relevant_history.sort(key=lambda x: x['week'])
    
    for entry in relevant_history:
        prev_tm = tm
        tm = get_next_tm(tm, entry['reps'], entry['target'])
        logs.append(f"Week {entry['week']} (App Log): {entry['reps']} reps -> TM {tm:.1f}kg")
        
    return tm, logs

# Programming data (Intensity, Reps, Rep Out Target, Sets)
MAIN_LIFTS = ["Squat", "Bench Press", "Deadlift", "OHP"]

# Exact Progression derived from Spreadsheet Data
# Format: (Intensity, Reps)
MAIN_SCHEDULE = [
    (0.7, 5), (0.75, 4), (0.8, 3), (0.725, 5), (0.775, 4), (0.825, 3), 
    (0.6, 5), (0.75, 4), (0.8, 3), (0.85, 2), (0.775, 4), (0.825, 3), 
    (0.875, 2), (0.6, 5), (0.8, 3), (0.875, 2), (0.925, 1), (0.875, 2), 
    (0.925, 1), (0.975, 1), (0.6, 5)
]

# Aux Intensity (derived from Incline Press row)
AUX_SCHEDULE = [
    (0.639, 7), (0.75, 6), (0.667, 5), (0.667, 7), (0.722, 6), (0.778, 5), 
    (0.528, 5), (0.694, 6), (0.75, 5), (0.806, 4), (0.722, 6), (0.778, 5), 
    (0.833, 4), (0.528, 5), (0.75, 5), (0.806, 4), (0.861, 3), (0.806, 4), 
    (0.861, 3), (0.917, 2), (0.528, 5)
]

# Exact Planned Weights from Spreadsheet (Weeks 16-21)
PLANNED_WEIGHTS = {
    "Squat": {16: 87.5, 17: 92.5, 18: 87.5, 19: 92.5, 20: 97.5, 21: 60.0},
    "Romanian Deadlift": {16: 85.0, 17: 90.0, 18: 85.0, 19: 90.0, 20: 97.5, 21: 57.5},
    "Incline Press": {16: 72.5, 17: 77.5, 18: 72.5, 19: 77.5, 20: 82.5, 21: 47.5},
    "Bench Press": {16: 90.0, 17: 97.5, 18: 90.0, 19: 97.5, 20: 102.5, 21: 65.0},
    "OHP": {16: 42.5, 17: 45.0, 18: 42.5, 19: 45.0, 20: 47.5, 21: 30.0},
    "Leg Press": {16: 162.5, 17: 172.5, 18: 162.5, 19: 172.5, 20: 182.5, 21: 107.5},
    "Deadlift": {16: 127.5, 17: 135.0, 18: 127.5, 19: 135.0, 20: 142.5, 21: 90.0},
    "DB OHP": {16: 20.0, 17: 20.0, 18: 20.0, 19: 20.0, 20: 22.5, 21: 12.5}
}

def get_lift_stats(week, is_aux=False):
    # Clamp week to 1-21
    idx = max(0, min(week - 1, 20))
    
    if is_aux:
        intensity, reps = AUX_SCHEDULE[idx]
    else:
        intensity, reps = MAIN_SCHEDULE[idx]
        
    return {
        "intensity": intensity,
        "reps": reps,
        "sets": 5,
        "rep_out": reps * 2 if week < 20 else reps # No rep out on peak week usually
    }

# --- SIDEBAR: SETUP & 1RMs ---
st.sidebar.title("⚙️ Setup")
frequency = st.sidebar.selectbox("Training Frequency", ["2x", "3x", "4x", "5x", "6x"], index=1)
rounding = st.sidebar.selectbox("Rounding (kg)", [1.0, 1.25, 2.5, 5.0], index=2)

st.sidebar.subheader("Initial 1RMs")
maxes = {
    "Squat": st.sidebar.number_input("Squat Max", 100),
    "Bench Press": st.sidebar.number_input("Bench Max", 100),
    "Deadlift": st.sidebar.number_input("Deadlift Max", 140),
    "OHP": st.sidebar.number_input("OHP Max", 50),
    "Leg Press": st.sidebar.number_input("Leg Press Max", 190),
    "Incline Press": st.sidebar.number_input("Incline Max", 90),
    "Romanian Deadlift": st.sidebar.number_input("RDL Max", 100),
    "DB OHP": st.sidebar.number_input("DB OHP Max", 25),
}

# --- MAIN UI ---
st.title("🏋️ SBS Workout Log")
col_w, col_d = st.columns(2)
week = col_w.selectbox("Week", range(1, 22))
day = col_d.selectbox("Day", range(1, int(frequency[0]) + 1))

st.divider()

# Get exercises for today
today_exercises = EXERCISE_MAP[frequency].get(str(day), [])
history = load_history()

# Store session data for saving later
session_results = {}

for lift in today_exercises:
    # Determine if lift is Main or Aux
    is_aux = lift not in MAIN_LIFTS
    stats = get_lift_stats(week, is_aux=is_aux)

    # 1. Calculate Weight
    # Strategy: 
    # If week >= 16 and we have NO history for the week immediately before this,
    # use the PLANNED_WEIGHTS from the spreadsheet.
    # Otherwise, calculate dynamically.
    
    planned = PLANNED_WEIGHTS.get(lift, {}).get(week)
    
    # Check if we have app history for the previous week
    prev_week_history = [v for v in history.values() if v['lift'] == lift and v['week'] == week - 1]
    
    # Force Week 16 to use Planned Weights (Start Fresh). 
    # For Week 17+, use Planned unless we have history for the previous week.
    if planned and (week == 16 or not prev_week_history):
        weight = planned
        current_tm = weight / stats['intensity'] if stats['intensity'] > 0 else 0
        tm_logs = [f"Using Planned Weight from Spreadsheet: {weight}kg"]
    else:
        base_tm = maxes.get(lift, 0)
        current_tm, tm_logs = calculate_current_tm(lift, base_tm, history, week, is_aux=is_aux)
        weight = round((current_tm * stats['intensity']) / rounding) * rounding
    
    # Check if we have history for THIS week already to pre-fill
    prev_entry_key = f"{lift}_w{week}_d{day}"
    pre_filled_reps = history.get(prev_entry_key, {}).get("reps", stats['rep_out'])
    
    # Calculate completion
    completed_sets = sum([st.session_state.get(f"{lift}_{week}_{day}_s{i+1}", False) for i in range(stats['sets']-1)])
    is_amrap_done = st.session_state.get(f"{lift}_{week}_{day}_amrap", 0) > 0
    total_completed = completed_sets + (1 if is_amrap_done else 0)
    
    header_status = "✅" if total_completed == stats['sets'] else "🔄"
    
    with st.expander(f"{header_status} **{lift}** — {weight}kg ({total_completed}/{stats['sets']} sets)", expanded=True):
        st.caption(f"Calculated Weight: {weight}kg | Intensity: {stats['intensity']*100:.1f}%")
        with st.expander("📊 TM Calculation Details"):
            for log in tm_logs:
                st.text(log)
        
        # 1. Standard Sets Checkboxes
        st.write(f"**Working Sets:** {stats['sets']-1} sets of {stats['reps']}")
        set_cols = st.columns(stats['sets']-1)
        for i, col in enumerate(set_cols):
            col.checkbox(f"S{i+1}", key=f"{lift}_{week}_{day}_s{i+1}")
            
        st.divider()
        
        # 2. Final AMRAP Set
        c1, c2 = st.columns([1, 2])
        c1.metric("Rep Out Goal", f"{stats['rep_out']}+")
        
        # Default to the rep_out goal or saved value
        reps_done = c2.number_input(
            f"Actual reps on final set", 
            min_value=0, 
            max_value=50, 
            value=pre_filled_reps, 
            key=f"{lift}_{week}_{day}_amrap"
        )
        
        # Queue for saving
        session_results[lift] = {
            "reps": reps_done, 
            "target": stats['rep_out']
        }
        
        # User Interaction Logic
        diff = reps_done - stats['rep_out']
        if reps_done > 0:
            if diff > 0:
                st.success(f"🔥 +{diff} reps! New TM: {get_next_tm(current_tm, reps_done, stats['rep_out']):.1f}kg")
            elif diff == 0:
                st.info("🎯 Hit the target! TM stays the same.")
            else:
                st.warning(f"📉 Missed target. TM decreases.")

# Accessories Section
st.subheader("📓 Accessories")
st.text_area("Notes for accessories (Back, Biceps, Delts, etc.)", placeholder="e.g. Lat Pulldowns 3x12 @ 60kg")

if st.button("Complete Workout"):
    # Save all AMRAPs from this session
    for lift, data in session_results.items():
        save_history_entry(week, day, lift, data['reps'], data['target'])
    
    st.balloons()
    st.success(f"Workout Saved! Data written to {HISTORY_FILE}")