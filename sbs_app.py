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
    key = f"{lift}_w{week}" # Unique key per lift per week
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

def calculate_current_tm(lift, base_max, history, current_week):
    """Iterates through history to calculate the TM for the CURRENT week."""
    tm = base_max
    # We only care about weeks BEFORE the current one to determine today's weight
    # Sort history by week to apply adjustments in order
    relevant_history = [
        v for k, v in history.items() 
        if v['lift'] == lift and v['week'] < current_week
    ]
    relevant_history.sort(key=lambda x: x['week'])
    
    for entry in relevant_history:
        tm = get_next_tm(tm, entry['reps'], entry['target'])
        
    return tm

# Programming data (Intensity, Reps, Rep Out Target, Sets)
# This would normally be a large JSON; for this version, we use a helper function 
# to simulate the SBS progression logic found in your 'Setup' sheet.
def get_lift_stats(week):
    # Simplified SBS linear progression logic based on your Setup sheet
    # We use week to modulate intensity (Week 1 = 70%, Week 2 = 75%, etc.)
    base_intensities = [0.7, 0.75, 0.8, 0.725, 0.775, 0.825, 0.6, 0.75, 0.8, 0.85, 0.775, 0.825, 0.875, 0.6, 0.8, 0.85, 0.9, 0.85, 0.9, 0.95, 0.6]
    base_reps = [5, 4, 3, 5, 4, 3, 7, 4, 3, 2, 4, 3, 2, 7, 3, 2, 1, 2, 1, 1, 7]
    idx = (week - 1) % len(base_intensities)
    return {
        "intensity": base_intensities[idx],
        "reps": base_reps[idx],
        "sets": 5,
        "rep_out": base_reps[idx] * 2
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
stats = get_lift_stats(week)
history = load_history()

# Store session data for saving later
session_results = {}

for lift in today_exercises:
    # 1. Calculate Weight
    base_tm = maxes.get(lift, 0)
    current_tm = calculate_current_tm(lift, base_tm, history, week)
    
    # Check if we have history for THIS week already to pre-fill
    prev_entry_key = f"{lift}_w{week}"
    pre_filled_reps = history.get(prev_entry_key, {}).get("reps", stats['rep_out'])
    
    weight = round((current_tm * stats['intensity']) / rounding) * rounding
    
    # Calculate completion
    completed_sets = sum([st.session_state.get(f"{lift}_{week}_{day}_s{i+1}", False) for i in range(stats['sets']-1)])
    is_amrap_done = st.session_state.get(f"{lift}_{week}_{day}_amrap", 0) > 0
    total_completed = completed_sets + (1 if is_amrap_done else 0)
    
    header_status = "✅" if total_completed == stats['sets'] else "🔄"
    
    with st.expander(f"{header_status} **{lift}** — {weight}kg ({total_completed}/{stats['sets']} sets)", expanded=True):
        st.caption(f"Training Max: {current_tm:.1f}kg (Original: {base_tm}kg)")
        
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