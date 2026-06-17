import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
from pydantic import BaseModel, Field
from typing import List, Literal
import json

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="ByteSize Nutrition & Weight Tracker",
    page_icon="🥑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling & Typography
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

/* Theme Adaptive Reset & Styling */
html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
    background-color: var(--background-color);
    color: var(--text-color);
}

/* Header style */
.main-title {
    font-size: 2.8rem;
    font-weight: 700;
    background: linear-gradient(135deg, #60a5fa 0%, #34d399 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.5rem;
    text-align: center;
}

.subtitle {
    font-size: 1.1rem;
    color: var(--text-color);
    opacity: 0.7;
    margin-bottom: 2rem;
    text-align: center;
}

/* Premium Adaptive Card Styles */
.glass-card, div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--secondary-background-color) !important;
    border: 1px solid rgba(128, 128, 128, 0.15) !important;
    border-radius: 16px !important;
    padding: 2rem !important;
    margin-bottom: 1.5rem !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08) !important;
}

.banner-card {
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.12) 0%, rgba(16, 185, 129, 0.12) 100%);
    border-left: 5px solid #3b82f6;
    border-radius: 12px;
    padding: 1.25rem;
    margin-top: 1rem;
    margin-bottom: 2rem;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
}

/* Button Custom Styles */
div.stButton > button {
    background: linear-gradient(135deg, #3b82f6 0%, #10b981 100%);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 0.6rem 1.8rem;
    font-weight: 600;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
}

div.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(59, 130, 246, 0.45);
    background: linear-gradient(135deg, #2563eb 0%, #059669 100%);
    color: #ffffff;
}

div.stButton > button:active {
    transform: translateY(1px);
}

/* Sidebar Custom Signout Styling */
.sidebar-info {
    font-size: 0.9rem;
    color: var(--text-color);
    background: rgba(128, 128, 128, 0.1);
    padding: 1rem;
    border-radius: 10px;
    margin-bottom: 1rem;
}

.sidebar-footer-spacer {
    height: 35vh;
}

/* Mobile Friendly Responsive Overrides */
@media (max-width: 768px) {
    .sidebar-footer-spacer {
        height: 3vh !important;
    }
    .main-title {
        font-size: 2.0rem !important;
        margin-top: 0.5rem !important;
    }
    .subtitle {
        font-size: 0.95rem !important;
        margin-bottom: 1.5rem !important;
    }
    .glass-card, div[data-testid="stVerticalBlockBorderWrapper"] {
        padding: 1.25rem !important;
        margin-bottom: 1rem !important;
    }
    .banner-card {
        padding: 1.0rem !important;
        margin-bottom: 1.5rem !important;
    }
    div.stButton > button {
        padding: 0.5rem 1.2rem !important;
        font-size: 0.9rem !important;
    }
}

/* Hide Cookie Controller Iframe */
div[data-testid='element-container']:has(iframe[title='streamlit_cookies_controller.cookie_controller']) {
    display: none;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# Configuration Guard & Imports
# -------------------------------------------------------------
try:
    from supabase import create_client, Client
    from google import genai
    from google.genai import types
    from streamlit_cookies_controller import CookieController
except ImportError as e:
    st.error(f"Required package not found: {e}. Please run 'pip install -r requirements.txt'")
    st.stop()

# Ensure secrets exist
if ("SUPABASE_URL" not in st.secrets or 
    "SUPABASE_KEY" not in st.secrets or 
    "GEMINI_API_KEY" not in st.secrets):
    st.error("Missing configuration! Please configure `SUPABASE_URL`, `SUPABASE_KEY`, and `GEMINI_API_KEY` in `.streamlit/secrets.toml` or your environment secrets.")
    st.stop()

# -------------------------------------------------------------
# Clients Initialization (Cached)
# -------------------------------------------------------------
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase_client = get_supabase()

# -------------------------------------------------------------
# Session State & Helper Definitions
# -------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None
if "session" not in st.session_state:
    st.session_state.session = None
if "profile" not in st.session_state:
    st.session_state.profile = None
if "active_grid_data" not in st.session_state:
    st.session_state.active_grid_data = pd.DataFrame(columns=["food_name", "meal_type", "servings", "calories_per_serving", "total_calories"])
if "tip_cache" not in st.session_state:
    st.session_state.tip_cache = {}
if "file_uploader_key" not in st.session_state:
    st.session_state.file_uploader_key = 0

# Initialize Cookie Controller
cookie_controller = CookieController()


def check_profile(user_id: str):
    """Query Supabase to fetch user's profile if it exists."""
    try:
        res = supabase_client.table("profiles").select("*").eq("id", user_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
    except Exception as e:
        st.error(f"Database error checking profile: {e}")
    return None

from datetime import timedelta

@st.cache_data(ttl=60)
def get_user_activity_dates(user_id: str):
    try:
        f_res = supabase_client.table("food_logs").select("date").eq("user_id", user_id).execute()
        w_res = supabase_client.table("weight_logs").select("date").eq("user_id", user_id).execute()
        
        f_dates = {x["date"] for x in f_res.data} if f_res.data else set()
        w_dates = {x["date"] for x in w_res.data} if w_res.data else set()
        return f_dates.union(w_dates)
    except Exception:
        return set()

def calculate_streak(user_id: str) -> int:
    dates_set = get_user_activity_dates(user_id)
    if not dates_set:
        return 0
    
    parsed_dates = []
    for d in dates_set:
        try:
            if isinstance(d, str):
                parsed_dates.append(datetime.strptime(d, "%Y-%m-%d").date())
            elif isinstance(d, (date, datetime)):
                parsed_dates.append(d if isinstance(d, date) else d.date())
        except Exception:
            continue
            
    if not parsed_dates:
        return 0
        
    sorted_dates = sorted(parsed_dates, reverse=True)
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    if sorted_dates[0] not in (today, yesterday):
        return 0
        
    streak = 1
    current_date = sorted_dates[0]
    
    for next_date in sorted_dates[1:]:
        diff = (current_date - next_date).days
        if diff == 1:
            streak += 1
            current_date = next_date
        elif diff == 0:
            continue
        else:
            break
            
    return streak

def sign_out():
    """Sign the user out of the application."""
    try:
        supabase_client.auth.sign_out()
    except Exception:
        pass
        
    # Clear cookies
    try:
        cookie_controller.remove("sb_access_token")
        cookie_controller.remove("sb_refresh_token")
    except Exception:
        pass
        
    st.session_state.user = None
    st.session_state.session = None
    st.session_state.profile = None
    st.session_state.active_grid_data = pd.DataFrame(columns=["food_name", "meal_type", "servings", "calories_per_serving", "total_calories"])
    st.session_state.tip_cache = {}
    st.cache_data.clear()
    st.rerun()

@st.dialog("Confirm Reset")
def confirm_reset_dialog():
    st.write("Are you sure you want to clear the parser inputs and reset the log entries grid?")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Yes, Reset", use_container_width=True):
            st.session_state.active_grid_data = pd.DataFrame(columns=["food_name", "meal_type", "servings", "calories_per_serving", "total_calories"])
            if "file_uploader_key" in st.session_state:
                st.session_state.file_uploader_key += 1
            st.rerun()
    with c2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()

# -------------------------------------------------------------
# Auto-Login Session Restoration via Cookies
# -------------------------------------------------------------
if not st.session_state.user:
    # Read cookies natively and synchronously from request headers
    access_token = st.context.cookies.get("sb_access_token")
    refresh_token = st.context.cookies.get("sb_refresh_token")
    
    # Fallback to cookie controller if native cookies are not yet populated
    if not access_token or not refresh_token:
        access_token = cookie_controller.get("sb_access_token")
        refresh_token = cookie_controller.get("sb_refresh_token")
        
    if access_token and refresh_token:
        try:
            res = supabase_client.auth.set_session(access_token=access_token, refresh_token=refresh_token)
            if res.user:
                st.session_state.user = res.user
                st.session_state.session = res.session
                
                # Fetch and store profile
                profile = check_profile(res.user.id)
                if profile:
                    st.session_state.profile = profile
                
                # Save refreshed tokens back to cookies (30 days expiration)
                try:
                    cookie_controller.set("sb_access_token", res.session.access_token, expires=datetime.now() + timedelta(days=30))
                    cookie_controller.set("sb_refresh_token", res.session.refresh_token, expires=datetime.now() + timedelta(days=30))
                except Exception:
                    pass
                st.rerun()
        except Exception:
            # Clear invalid/expired cookies
            try:
                cookie_controller.remove("sb_access_token")
                cookie_controller.remove("sb_refresh_token")
            except Exception:
                pass

# -------------------------------------------------------------
# Authentication Flow Interface
# -------------------------------------------------------------
if not st.session_state.user:
    st.markdown("<h1 class='main-title'>ByteSize Nutrition</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Production-grade nutrition parsing, macro budgeting, & weight forecasting</p>", unsafe_allow_html=True)

    auth_action = st.tabs(["🔒 Secure Login", "📝 Create Account"])
    
    # Login Tab
    with auth_action[0]:
        with st.container(border=True):
            with st.form("login_form", border=False):
                login_email = st.text_input("Email Address", key="login_email")
                login_password = st.text_input("Password", type="password", key="login_password")
                submit_login = st.form_submit_button("Authenticate", use_container_width=True)
                
            if submit_login:
                if not login_email or not login_password:
                    st.error("Fields cannot be blank.")
                else:
                    try:
                        res = supabase_client.auth.sign_in_with_password({
                            "email": login_email,
                            "password": login_password
                        })
                        if res.user:
                            st.session_state.user = res.user
                            st.session_state.session = res.session
                            
                            # Save session to cookies for 30 days
                            try:
                                cookie_controller.set("sb_access_token", res.session.access_token, expires=datetime.now() + timedelta(days=30))
                                cookie_controller.set("sb_refresh_token", res.session.refresh_token, expires=datetime.now() + timedelta(days=30))
                            except Exception:
                                pass
                                
                            # Check and cache profile
                            profile = check_profile(res.user.id)
                            if profile:
                                st.session_state.profile = profile
                            st.success("Session verified! Loading...")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Authentication Failed: {e}")

    # Sign Up Tab
    with auth_action[1]:
        with st.container(border=True):
            with st.form("signup_form", border=False):
                signup_email = st.text_input("Email Address", key="signup_email")
                signup_password = st.text_input("Password", type="password", key="signup_password")
                signup_confirm = st.text_input("Confirm Password", type="password", key="signup_confirm")
                submit_signup = st.form_submit_button("Register Account", use_container_width=True)
                
            if submit_signup:
                if not signup_email or not signup_password:
                    st.error("Fields cannot be blank.")
                elif signup_password != signup_confirm:
                    st.error("Passwords must match.")
                else:
                    try:
                        res = supabase_client.auth.sign_up({
                            "email": signup_email,
                            "password": signup_password
                        })
                        if res.user:
                            st.success("Account registered! Check email verification if required, then proceed to log in.")
                            if res.session:
                                st.session_state.user = res.user
                                st.session_state.session = res.session
                                # Save session to cookies for 30 days
                                try:
                                    cookie_controller.set("sb_access_token", res.session.access_token, expires=datetime.now() + timedelta(days=30))
                                    cookie_controller.set("sb_refresh_token", res.session.refresh_token, expires=datetime.now() + timedelta(days=30))
                                except Exception:
                                    pass
                                st.rerun()
                    except Exception as e:
                        st.error(f"Registration Failed: {e}")
        
    st.stop()

# -------------------------------------------------------------
# Onboarding Guard
# -------------------------------------------------------------
if st.session_state.user and not st.session_state.profile:
    # Double check in database
    profile = check_profile(st.session_state.user.id)
    if profile:
        st.session_state.profile = profile
    else:
        # Prevent accessing the app until profile is created
        st.markdown("<h1 class='main-title'>Welcome to ByteSize!</h1>", unsafe_allow_html=True)
        st.markdown("<p class='subtitle'>Let's configure your daily goals first.</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.subheader("🏁 Core Nutrition Config")
            
            target_calories = st.number_input(
                "Target Daily Calories (kcal)",
                min_value=500,
                max_value=8000,
                value=2000,
                step=50
            )
            current_weight = st.number_input(
                "Current Body Weight",
                min_value=30.0,
                max_value=400.0,
                value=150.0,
                step=0.5,
                help="Your starting body weight today."
            )
            target_weight = st.number_input(
                "Target Body Weight",
                min_value=30.0,
                max_value=400.0,
                value=150.0,
                step=0.5,
                help="Your target weight goals."
            )
            st.markdown("🥑 **Dietary Preferences & Exclusions**")
            popular_options = [
                "Vegetarian", "Vegan", "Gluten-Free", "Dairy-Free",
                "Keto", "Paleo", "Halal", "Kosher",
                "Low-Carb", "Nut-Free", "Shellfish-Free"
            ]
            selected_prefs = []
            pref_cols = st.columns(3)
            for idx, option in enumerate(popular_options):
                col = pref_cols[idx % 3]
                if col.checkbox(option, key=f"onboard_pref_{option}"):
                    selected_prefs.append(option)
            
            if st.button("Complete Onboarding", use_container_width=True):
                try:
                    # 1. Insert Profile
                    profile_payload = {
                        "id": st.session_state.user.id,
                        "target_calories": int(target_calories),
                        "target_weight": float(target_weight),
                        "food_preferences": selected_prefs,
                        "is_onboarded": True
                    }
                    profile_res = supabase_client.table("profiles").insert(profile_payload).execute()
                    
                    # 2. Insert Starting Weight Log
                    weight_payload = {
                        "user_id": st.session_state.user.id,
                        "date": str(date.today()),
                        "weight": float(current_weight)
                    }
                    supabase_client.table("weight_logs").insert(weight_payload).execute()
                    st.cache_data.clear()
                    
                    if profile_res.data:
                        st.session_state.profile = profile_res.data[0]
                        st.success("Configuration and starting weight saved! Redirecting...")
                        st.rerun()
                except Exception as e:
                    st.error(f"Failed to record onboarding configurations: {e}")
        st.stop()

# -------------------------------------------------------------
# Setup App Shell (Sidebar & Tabs)
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("<h3 style='margin-bottom: 0px;'>🥑 ByteSize App</h3>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 0.8rem; color: #64748b;'>Control Center</p>", unsafe_allow_html=True)
    
    # Calculate consecutive daily logging streak
    streak_val = calculate_streak(st.session_state.user.id)
    streak_badge = f"🔥 <strong>{streak_val}-Day Streak</strong>" if streak_val > 0 else "❄️ 0-Day Streak"
    
    prefs_list = st.session_state.profile.get("food_preferences") or []
    prefs_str = ", ".join(prefs_list) if prefs_list else "None"
    
    st.markdown(f"""
    <div class='sidebar-info'>
        <strong>Session:</strong><br>{st.session_state.user.email}<br>
        <strong>Streak:</strong> {streak_badge}<br>
        <strong>Daily Budget:</strong><br>{st.session_state.profile['target_calories']} kcal<br>
        <strong>Target Weight:</strong><br>{st.session_state.profile['target_weight']}<br>
        <strong>Diet Preferences:</strong><br>{prefs_str}
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Update Goals", use_container_width=True):
        st.session_state.editing_profile = True
        st.rerun()
        
    if st.button("Sign Out Session", use_container_width=True):
        sign_out()
        
    st.markdown("<div class='sidebar-footer-spacer'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align: center; font-size: 0.8rem; color: #64748b; font-style: italic; border-top: 1px solid rgba(128,128,128,0.15); padding-top: 15px;'>
        Made with ❤️ by <br><strong>Sunny Patel</strong> (Senior Data Analyst) <br>for his loving wife
    </div>
    """, unsafe_allow_html=True)

# Initialize editing state if not present
if "editing_profile" not in st.session_state:
    st.session_state.editing_profile = False

# Edit Profile Intercept
if st.session_state.editing_profile:
    st.markdown("<h1 class='main-title'>Update Your Goals</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Modify your calorie and weight targets below.</p>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.subheader("🏁 Modify Targets")
        new_calories = st.number_input(
            "Target Daily Calories (kcal)",
            min_value=500,
            max_value=8000,
            value=int(st.session_state.profile["target_calories"]),
            step=50
        )
        new_weight = st.number_input(
            "Target Body Weight",
            min_value=30.0,
            max_value=400.0,
            value=float(st.session_state.profile["target_weight"]),
            step=0.5
        )
        
        st.markdown("🥑 **Dietary Preferences & Exclusions**")
        popular_options = [
            "Vegetarian", "Vegan", "Gluten-Free", "Dairy-Free",
            "Keto", "Paleo", "Halal", "Kosher",
            "Low-Carb", "Nut-Free", "Shellfish-Free"
        ]
        selected_prefs = []
        existing_prefs = st.session_state.profile.get("food_preferences") or []
        if not isinstance(existing_prefs, list):
            existing_prefs = list(existing_prefs)
            
        pref_cols = st.columns(3)
        for idx, option in enumerate(popular_options):
            col = pref_cols[idx % 3]
            is_checked = option in existing_prefs
            if col.checkbox(option, value=is_checked, key=f"edit_pref_{option}"):
                selected_prefs.append(option)
        
        c_save, c_cancel = st.columns(2)
        with c_save:
            if st.button("Save Changes", use_container_width=True):
                try:
                    res = supabase_client.table("profiles").update({
                        "target_calories": int(new_calories),
                        "target_weight": float(new_weight),
                        "food_preferences": selected_prefs
                    }).eq("id", st.session_state.user.id).execute()
                    if res.data:
                        st.session_state.profile = res.data[0]
                        st.session_state.editing_profile = False
                        st.session_state.tip_cache = {}
                        st.success("Goals updated successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Failed to update goals: {e}")
        with c_cancel:
            if st.button("Cancel", use_container_width=True):
                st.session_state.editing_profile = False
                st.rerun()
    st.stop()

# Initialize Navigation Tabs
tab_log, tab_insights = st.tabs(["Log Intake", "History & Insights"])

# -------------------------------------------------------------
# Parsing Schema Definitions
# -------------------------------------------------------------
class MealItem(BaseModel):
    food_name: str = Field(description="Single item/food name (e.g. 'eggs', 'sourdough bread')")
    meal_type: Literal['breakfast', 'lunch', 'dinner', 'snack'] = Field(description="Meal type category")
    servings: float = Field(description="Quantity or number of servings (e.g. 1.0, 2.5, 0.5), defaulting to 1.0", default=1.0)
    calories_per_serving: int = Field(description="Calories count estimate for a single serving of this item")

class ParsedMeals(BaseModel):
    items: List[MealItem] = Field(description="List of food items parsed from description")

def generate_eating_tip(target: int, logged: int, remaining: int, food_preferences: list = None) -> str:
    """Invokes Gemini to output a quick encouraging macro-eating tip."""
    try:
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        pref_str = f" User dietary preferences/exclusions: {', '.join(food_preferences)}." if food_preferences else ""
        prompt = (
            f"Daily target: {target} kcal. Logged today: {logged} kcal. "
            f"Remaining: {remaining} kcal.{pref_str} "
            "Write a dynamic, helpful, single-sentence strategic eating tip or encouragement based on this remaining budget. "
            "Ensure the tip respects their dietary preferences/exclusions (e.g. do not suggest dairy if dairy-free, meat if vegetarian). "
            "Do not use markdown formatting, bolding, or introductory text. Return only the single sentence."
        )
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        return f"Focus on eating nutrient-dense whole foods to meet your targets! (Remaining: {remaining} kcal)"

# -------------------------------------------------------------
# TAB 1: Log Intake
# -------------------------------------------------------------
with tab_log:
    st.markdown("<h2 style='margin-bottom:0.2rem;'>Log Your Daily Intake</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8;'>Add calories and track weight for a selected day using AI smart parsing.</p>", unsafe_allow_html=True)
    
    # 1. Date selection
    selected_date = st.date_input("Target Logging Date", value=date.today())
    
    # 2. Cumulative calorie summary
    try:
        log_res = supabase_client.table("food_logs").select("calories").eq("user_id", st.session_state.user.id).eq("date", str(selected_date)).execute()
        total_logged = sum(x["calories"] for x in log_res.data) if log_res.data else 0
    except Exception as e:
        total_logged = 0
        st.error(f"Error checking log metrics: {e}")
        
    target_cal = st.session_state.profile["target_calories"]
    remaining_cal = target_cal - total_logged
    
    # Metrics Banner
    st.markdown("### Budget Progress")
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Total Logged", f"{total_logged} kcal")
    mc2.metric("Target Calories", f"{target_cal} kcal")
    mc3.metric("Remaining Budget", f"{remaining_cal} kcal", delta=f"{remaining_cal}" if remaining_cal >= 0 else f"{remaining_cal}", delta_color="normal" if remaining_cal >= 0 else "inverse")
    
    # Context tip using Gemini
    cache_key = f"{selected_date}_{total_logged}"
    if cache_key in st.session_state.tip_cache:
        tip = st.session_state.tip_cache[cache_key]
    else:
        with st.spinner("AI coach is crafting today's recommendation..."):
            user_prefs = st.session_state.profile.get("food_preferences") or []
            tip = generate_eating_tip(target_cal, total_logged, remaining_cal, user_prefs)
            st.session_state.tip_cache[cache_key] = tip
            
    st.markdown(f"""
    <div class='banner-card'>
        💡 <strong>AI Strategic Tip:</strong> {tip}
    </div>
    """, unsafe_allow_html=True)

    # 3. Smart Input Form
    with st.container(border=True):
        st.subheader("🧠 Smart AI Meal Parser")
        st.markdown("<p style='font-size:0.9rem; color:#94a3b8;'>Describe what you ate in natural language or upload an image of your meal, and Gemini will extract the items, servings, and calories.</p>", unsafe_allow_html=True)
        

        meal_description = st.text_area(
            "Describe meals (optional if uploading image)...",
            placeholder="For breakfast had two large scrambled eggs with a slice of sourdough toast. Had a standard green salad with chicken breast for lunch, and a protein shake after working out.",
            height=120,
            key=f"meal_desc_{st.session_state.file_uploader_key}"
        )
        
        uploaded_file = st.file_uploader(
            "📷 Or Upload an Image of your meal", 
            type=["jpg", "jpeg", "png"],
            key=f"meal_uploader_{st.session_state.file_uploader_key}"
        )
        
        if st.button("Parse Meal / Image", use_container_width=True):
            if not meal_description.strip() and not uploaded_file:
                st.warning("Please enter a text description or upload a meal image before parsing.")
            else:
                with st.spinner("Analyzing input with Gemini 3.5 Flash..."):
                    try:
                        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                        
                        contents = []
                        if uploaded_file:
                            image_bytes = uploaded_file.read()
                            contents.append(
                                types.Part.from_bytes(
                                    data=image_bytes,
                                    mime_type=uploaded_file.type
                                )
                            )
                        
                        prompt = "Analyze this meal input and extract all food items, estimated servings, and calories per serving. "
                        if meal_description.strip():
                            prompt += f"Context provided by user: '{meal_description.strip()}'"
                        contents.append(prompt)
                        
                        response = client.models.generate_content(
                            model='gemini-3.5-flash',
                            contents=contents,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                response_schema=ParsedMeals,
                                temperature=0.1
                            )
                        )
                        
                        # Read parsed outputs
                        raw_res = response.text
                        parsed_data = json.loads(raw_res)
                        items_list = parsed_data.get("items", [])
                        
                        if items_list:
                            processed_items = []
                            for item in items_list:
                                servs = float(item.get("servings", 1.0))
                                cps = int(item.get("calories_per_serving", item.get("calories", 100)))
                                processed_items.append({
                                    "food_name": item.get("food_name", ""),
                                    "meal_type": item.get("meal_type", "snack"),
                                    "servings": servs,
                                    "calories_per_serving": cps,
                                    "total_calories": int(round(servs * cps))
                                })
                            new_df = pd.DataFrame(processed_items)
                            st.session_state.active_grid_data = new_df
                            st.success(f"Parsed {len(items_list)} items successfully! Adjust values below if needed.")
                        else:
                            st.warning("Gemini couldn't find distinct food items in the input.")
                    except Exception as e:
                        st.error(f"Failed to parse: {e}")

    # 4. Editable Grid
    with st.container(border=True):
        st.subheader("📋 Refine Log Entries")
        st.markdown("<p style='font-size:0.85rem; color:#94a3b8;'>Use this grid to double-check entries, adjust servings, or add custom lines before bulk submitting.</p>", unsafe_allow_html=True)
        
        edited_df = st.data_editor(
            st.session_state.active_grid_data,
            num_rows="dynamic",
            column_config={
                "food_name": st.column_config.TextColumn("Food Name", required=True),
                "meal_type": st.column_config.SelectboxColumn("Meal Type", options=["breakfast", "lunch", "dinner", "snack"], required=True),
                "servings": st.column_config.NumberColumn("Servings", min_value=0.0, format="%.2f", step=0.1, required=True),
                "calories_per_serving": st.column_config.NumberColumn("Calories/Serving (kcal)", min_value=0, step=1, required=True),
                "total_calories": st.column_config.NumberColumn("Total Calories (kcal)", help="Calculated dynamically on Recalculate")
            },
            disabled=["total_calories"],
            use_container_width=True,
            key="editor_grid"
        )
        
        # Check if there are changes between editor state and stored state
        has_changes = not edited_df.equals(st.session_state.active_grid_data)
        
        if has_changes:
            st.warning("⚠️ Unrecalculated changes detected in the grid. Click 'Recalculate Totals' to update values and unlock the submit button.")
            
        col_recalc, col_reset, col_submit = st.columns(3)
        
        with col_recalc:
            if st.button("Recalculate Totals", use_container_width=True):
                rec_df = edited_df.copy()
                if not rec_df.empty:
                    rec_df["servings"] = pd.to_numeric(rec_df["servings"], errors="coerce").fillna(1.0)
                    rec_df["calories_per_serving"] = pd.to_numeric(rec_df["calories_per_serving"], errors="coerce").fillna(0).astype(int)
                    rec_df["total_calories"] = (rec_df["servings"] * rec_df["calories_per_serving"]).round().astype(int)
                st.session_state.active_grid_data = rec_df
                st.info("Totals recalculated! Submit is now enabled.")
                st.rerun()
                
        with col_reset:
            if st.button("Reset Parser & Grid", use_container_width=True):
                confirm_reset_dialog()
                
        with col_submit:
            if st.button("Submit Data to Database", disabled=has_changes, use_container_width=True):
                if edited_df.empty:
                    st.warning("No items to submit.")
                else:
                    try:
                        records = []
                        for _, row in edited_df.iterrows():
                            if pd.isna(row["food_name"]) or not str(row["food_name"]).strip():
                                continue
                            records.append({
                                "user_id": st.session_state.user.id,
                                "date": str(selected_date),
                                "food_name": str(row["food_name"]),
                                "meal_type": str(row["meal_type"]) if str(row["meal_type"]) in ['breakfast', 'lunch', 'dinner', 'snack'] else 'snack',
                                "calories": int(row["total_calories"])
                            })
                        
                        if records:
                            res = supabase_client.table("food_logs").insert(records).execute()
                            if res.data:
                                st.cache_data.clear()
                                # Reset the file uploader and text area widgets
                                if "file_uploader_key" in st.session_state:
                                    st.session_state.file_uploader_key += 1
                                st.success(f"Successfully logged {len(records)} meal items for {selected_date}!")
                                st.session_state.active_grid_data = pd.DataFrame(columns=["food_name", "meal_type", "servings", "calories_per_serving", "total_calories"])
                                st.rerun()
                        else:
                            st.warning("No valid items detected in the editor grid.")
                    except Exception as e:
                        st.error(f"Bulk insert failed: {e}")

    # 5. Weight Log
    with st.container(border=True):
        st.subheader("⚖️ Log Scale Weight (Optional)")
        
        # Check if already logged for the selected_date
        try:
            w_check = supabase_client.table("weight_logs").select("weight").eq("user_id", st.session_state.user.id).eq("date", str(selected_date)).execute()
            weight_logged = len(w_check.data) > 0
            logged_w = float(w_check.data[0]["weight"]) if weight_logged else 0.0
        except Exception:
            weight_logged = False
            logged_w = 0.0
            
        wc1, wc2 = st.columns([3, 1])
        with wc1:
            if weight_logged:
                weight_input = st.number_input(
                    "Current Weight Number",
                    min_value=0.0,
                    max_value=600.0,
                    value=logged_w,
                    disabled=True,
                    help="Weight has already been logged for this date."
                )
            else:
                weight_input = st.number_input(
                    "Current Weight Number",
                    min_value=0.0,
                    max_value=600.0,
                    value=0.0,
                    step=0.1,
                    key=f"weight_input_{selected_date}",
                    help="Enter body weight for selected target date."
                )
        with wc2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True) # Spacer
            if weight_logged:
                st.button("Logged for Today", disabled=True, use_container_width=True)
            else:
                if st.button("Record Weight", use_container_width=True):
                    if weight_input <= 0:
                        st.error("Please enter a valid weight record.")
                    else:
                        try:
                            weight_payload = {
                                "user_id": st.session_state.user.id,
                                "date": str(selected_date),
                                "weight": float(weight_input)
                            }
                            res = supabase_client.table("weight_logs").insert(weight_payload).execute()
                            if res.data:
                                st.cache_data.clear()
                                st.success(f"Weight of {weight_input} successfully logged for {selected_date}!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Failed to record weight: {e}")

# -------------------------------------------------------------
# TAB 2: History & Insights
# -------------------------------------------------------------
with tab_insights:
    st.markdown("<h2>Analytics, Trends, & Coach Insights</h2>", unsafe_allow_html=True)
    
    # Fetch user data
    try:
        food_res = supabase_client.table("food_logs").select("*").eq("user_id", st.session_state.user.id).order("date", desc=True).execute()
        weight_res = supabase_client.table("weight_logs").select("*").eq("user_id", st.session_state.user.id).order("date", desc=True).execute()
        food_logs = food_res.data
        weight_logs = weight_res.data
    except Exception as e:
        st.error(f"Failed to fetch historical trends: {e}")
        food_logs = []
        weight_logs = []
        
    if not food_logs and not weight_logs:
        st.info("No tracking metrics recorded. Start logging your food or scale weight to unlock this analysis dashboard!")
    else:
        # 1. Aggregations (Pandas manipulation)
        df_food = pd.DataFrame(food_logs) if food_logs else pd.DataFrame(columns=["date", "calories"])
        df_weight = pd.DataFrame(weight_logs) if weight_logs else pd.DataFrame(columns=["date", "weight"])
        
        # Parse Dates
        if not df_food.empty:
            df_food["date"] = pd.to_datetime(df_food["date"])
        if not df_weight.empty:
            df_weight["date"] = pd.to_datetime(df_weight["date"])
            
        # Layout metrics
        st.markdown("### Aggregated History Dashboard")
        
        # Sub-tabs for granular views
        view_day, view_week, view_month = st.tabs(["📅 Daily Logs", "🗓️ Weekly Averages", "📊 Monthly Trends"])
        
        # Calculate daily food calories
        df_daily_food = pd.DataFrame(columns=["Date", "Calories"])
        if not df_food.empty:
            df_daily_food = df_food.groupby(df_food["date"].dt.date)["calories"].sum().reset_index()
            df_daily_food.columns = ["Date", "Calories"]
            df_daily_food["Date"] = pd.to_datetime(df_daily_food["Date"])
            
        # View Day
        with view_day:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Calorie Intake (Per Day)")
                if not df_daily_food.empty:
                    df_daily_sorted = df_daily_food.sort_values("Date").copy()
                    df_daily_sorted["Date"] = df_daily_sorted["Date"].dt.strftime("%Y-%m-%d")
                    st.bar_chart(df_daily_sorted, x="Date", y="Calories")
                else:
                    st.caption("No food records available.")
            with col2:
                st.markdown("#### Body Weight Logs")
                if not df_weight.empty:
                    df_weight_daily = df_weight.groupby(df_weight["date"].dt.date)["weight"].mean().reset_index()
                    df_weight_daily.columns = ["Date", "Weight"]
                    df_weight_daily["Date"] = pd.to_datetime(df_weight_daily["Date"])
                    df_weight_sorted = df_weight_daily.sort_values("Date").copy()
                    df_weight_sorted["Date"] = df_weight_sorted["Date"].dt.strftime("%Y-%m-%d")
                    if len(df_weight_sorted) > 1:
                        st.line_chart(df_weight_sorted, x="Date", y="Weight")
                    else:
                        st.scatter_chart(df_weight_sorted, x="Date", y="Weight")
                else:
                    st.caption("No weight logs available.")

                    
        # View Week
        with view_week:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Weekly Average Intake (kcal/day)")
                if not df_daily_food.empty:
                    df_weekly_food = df_daily_food.copy()
                    df_weekly_food["Week Starting"] = df_weekly_food["Date"].dt.to_period("W").dt.start_time
                    df_weekly_avg = df_weekly_food.groupby("Week Starting")["Calories"].mean().reset_index()
                    df_weekly_avg.columns = ["Week Starting", "Average Daily Calories"]
                    df_weekly_avg["Week Starting"] = df_weekly_avg["Week Starting"].dt.strftime("%Y-%m-%d")
                    st.bar_chart(df_weekly_avg, x="Week Starting", y="Average Daily Calories")
                else:
                    st.caption("No nutrition records available.")
            with col2:
                st.markdown("#### Weekly Average Weight")
                if not df_weight.empty:
                    df_weekly_w = df_weight.copy()
                    df_weekly_w["Week Starting"] = df_weekly_w["date"].dt.to_period("W").dt.start_time
                    df_weekly_w_avg = df_weekly_w.groupby("Week Starting")["weight"].mean().reset_index()
                    df_weekly_w_avg.columns = ["Week Starting", "Average Weight"]
                    df_weekly_w_avg["Week Starting"] = df_weekly_w_avg["Week Starting"].dt.strftime("%Y-%m-%d")
                    if len(df_weekly_w_avg) > 1:
                        st.line_chart(df_weekly_w_avg, x="Week Starting", y="Average Weight")
                    else:
                        st.scatter_chart(df_weekly_w_avg, x="Week Starting", y="Average Weight")
                else:
                    st.caption("No weight logs available.")
                    
        # View Month
        with view_month:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Monthly Average Intake (kcal/day)")
                if not df_daily_food.empty:
                    df_monthly_food = df_daily_food.copy()
                    df_monthly_food["Month Starting"] = df_monthly_food["Date"].dt.to_period("M").dt.start_time
                    df_monthly_avg = df_monthly_food.groupby("Month Starting")["Calories"].mean().reset_index()
                    df_monthly_avg.columns = ["Month Starting", "Average Daily Calories"]
                    df_monthly_avg["Month Starting"] = df_monthly_avg["Month Starting"].dt.strftime("%Y-%m-%d")
                    st.bar_chart(df_monthly_avg, x="Month Starting", y="Average Daily Calories")
                else:
                    st.caption("No nutrition records available.")
            with col2:
                st.markdown("#### Monthly Average Weight")
                if not df_weight.empty:
                    df_monthly_w = df_weight.copy()
                    df_monthly_w["Month Starting"] = df_monthly_w["date"].dt.to_period("M").dt.start_time
                    df_monthly_w_avg = df_monthly_w.groupby("Month Starting")["weight"].mean().reset_index()
                    df_monthly_w_avg.columns = ["Month Starting", "Average Weight"]
                    df_monthly_w_avg["Month Starting"] = df_monthly_w_avg["Month Starting"].dt.strftime("%Y-%m-%d")
                    if len(df_monthly_w_avg) > 1:
                        st.line_chart(df_monthly_w_avg, x="Month Starting", y="Average Weight")
                    else:
                        st.scatter_chart(df_monthly_w_avg, x="Month Starting", y="Average Weight")
                else:
                    st.caption("No weight logs available.")

        # 2. Overlapping Weight vs Intake Comparison (Weekly Average basis)
        st.markdown("---")
        st.markdown("### ⚖️ Weight vs. Calorie Intake Trends")
        st.markdown("<p style='font-size:0.9rem; color:#94a3b8;'>Compare weekly average calories consumed (left-axis) against your scale weight (right-axis), including a projected trajectory forecast based on your weight slope.</p>", unsafe_allow_html=True)
        
        if not df_daily_food.empty and not df_weight.empty:
            try:
                # Merge calories and weights weekly
                df_c_week = df_daily_food.copy()
                df_c_week["Week Starting"] = df_c_week["Date"].dt.to_period("W").dt.start_time
                df_c_week_avg = df_c_week.groupby("Week Starting")["Calories"].mean().reset_index()
                
                df_w_week = df_weight.copy()
                df_w_week["Week Starting"] = df_w_week["date"].dt.to_period("W").dt.start_time
                df_w_week_avg = df_w_week.groupby("Week Starting")["weight"].mean().reset_index()
                
                # Weight Projection math if we have at least 3 entries
                df_w_sorted = df_weight.sort_values("date")
                slope = 0.0
                weight_proj_weekly_avg = None
                has_forecast = False
                
                if len(df_w_sorted) >= 3 and df_w_sorted["date"].nunique() > 1:
                    start_date = df_w_sorted["date"].min()
                    df_w_sorted["days_since_start"] = (df_w_sorted["date"] - start_date).dt.days
                    x_val = df_w_sorted["days_since_start"].values
                    y_val = df_w_sorted["weight"].values.astype(float)
                    
                    slope, intercept = np.polyfit(x_val, y_val, 1)
                    
                    latest_weight = float(df_w_sorted.iloc[-1]["weight"])
                    latest_date = df_w_sorted.iloc[-1]["date"]
                    
                    # Generate 30-day projection
                    proj_dates = [latest_date + pd.Timedelta(days=i) for i in range(1, 31)]
                    proj_weights = [latest_weight + slope * i for i in range(1, 31)]
                    
                    df_proj = pd.DataFrame({
                        "date": proj_dates,
                        "weight_proj": proj_weights
                    })
                    
                    df_proj["Week Starting"] = df_proj["date"].dt.to_period("W").dt.start_time
                    weight_proj_weekly_avg = df_proj.groupby("Week Starting")["weight_proj"].mean().reset_index()
                    has_forecast = True
                
                # Merge datasets
                compare_df = pd.merge(df_c_week_avg, df_w_week_avg, on="Week Starting", how="outer")
                if has_forecast:
                    compare_df = pd.merge(compare_df, weight_proj_weekly_avg, on="Week Starting", how="outer")
                compare_df = compare_df.sort_values("Week Starting")
                compare_df["Week Label"] = compare_df["Week Starting"].dt.strftime("%Y-%m-%d")
                
                # Render using Plotly for premium dual-axis overlap
                import plotly.graph_objects as go
                from plotly.subplots import make_subplots
                
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                # Calories Trace
                fig.add_trace(
                    go.Scatter(
                        x=compare_df["Week Label"],
                        y=compare_df["Calories"],
                        name="Avg Calorie Intake (kcal)",
                        mode="lines+markers",
                        line=dict(color="#10b981", width=3)
                    ),
                    secondary_y=False
                )
                
                # Weight Trace
                fig.add_trace(
                    go.Scatter(
                        x=compare_df["Week Label"],
                        y=compare_df["weight"],
                        name="Avg Weight",
                        mode="lines+markers",
                        line=dict(color="#3b82f6", width=3)
                    ),
                    secondary_y=True
                )
                
                # Projected Weight Trace
                if has_forecast and "weight_proj" in compare_df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=compare_df["Week Label"],
                            y=compare_df["weight_proj"],
                            name="Projected Weight (Trend)",
                            mode="lines+markers",
                            line=dict(color="#3b82f6", width=2, dash="dash")
                        ),
                        secondary_y=True
                    )
                
                fig.update_layout(
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(l=20, r=20, t=30, b=20),
                    height=450,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)", type="category"),
                    yaxis=dict(title="Calorie Intake (kcal/day)", showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
                    yaxis2=dict(title="Body Weight", showgrid=False)
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Show Forecasting Insights Card
                if has_forecast:
                    target_w = float(st.session_state.profile["target_weight"])
                    latest_weight = float(df_w_sorted.iloc[-1]["weight"])
                    
                    st.markdown("#### 🔮 Weight Trajectory Forecast")
                    if abs(slope) < 0.01:
                        st.info("⚖️ **Trend Status: Stable/Plateau**  \nYour weight has been holding steady over the recorded period. Maintain consistency to see long-term changes.")
                    else:
                        is_losing = slope < 0
                        is_gaining = slope > 0
                        needs_lose = latest_weight > target_w
                        needs_gain = latest_weight < target_w
                        
                        if (is_losing and needs_lose) or (is_gaining and needs_gain):
                            days_to_target = abs((target_w - latest_weight) / slope)
                            target_date_est = date.today() + pd.Timedelta(days=days_to_target)
                            st.success(
                                f"📈 **Trend Status: On Track**  \n"
                                f"Based on your recent rate of change ({slope*7:.2f} units per week), "
                                f"you are on track to reach your goal of **{target_w}** in approximately **{int(round(days_to_target))} days** "
                                f"(around **{target_date_est.strftime('%B %d, %Y')}**). Keep up the fantastic work!"
                            )
                        elif (is_losing and not needs_lose) or (is_gaining and not needs_gain):
                            st.info(
                                f"🎉 **Trend Status: Goal Exceeded**  \n"
                                f"You have already crossed your target weight of **{target_w}**! Your current trend is "
                                f"{'downward' if is_losing else 'upward'}. Focus on healthy weight maintenance."
                            )
                        else:
                            st.warning(
                                f"⚠️ **Trend Status: Direction Shift**  \n"
                                f"Your recent weight trend ({slope*7:+.2f} units per week) is moving away from your target of **{target_w}**. "
                                f"Check your daily caloric balance or review your activity logs with the AI Health Coach below for suggestions."
                            )
                else:
                    st.info("💡 *Log your scale weight at least 3 times on different days to activate the interactive weight projection forecast!*")
            except Exception as e:
                st.error(f"Could not render the dual-axis chart comparison: {e}")
        else:
            st.info("Log both meal logs and weight logs for at least one week to display overlap analysis.")

        # 3. AI recommendation section
        st.markdown("---")
        st.markdown("### 🧠 AI Health Coach Engine")
        st.markdown("<p style='font-size:0.9rem; color:#94a3b8;'>Analyze your consolidated metrics from the past 30 days to extract key behaviors and optimize macro goals.</p>", unsafe_allow_html=True)
        
        if st.button("Generate Coach Analysis", use_container_width=True):
            with st.spinner("AI is analyzing weight trends and calorie budget deviations..."):
                try:
                    # Construct window metrics
                    today = pd.Timestamp.now().normalize()
                    limit_30d = today - pd.Timedelta(days=30)
                    limit_7d = today - pd.Timedelta(days=7)
                    
                    # 7 & 30 day daily calorie averages
                    c_7d_avg = 0.0
                    c_30d_avg = 0.0
                    
                    if not df_daily_food.empty:
                        df_df_7 = df_daily_food[df_daily_food["Date"] >= limit_7d]
                        df_df_30 = df_daily_food[df_daily_food["Date"] >= limit_30d]
                        c_7d_avg = df_df_7["Calories"].mean() if not df_df_7.empty else 0.0
                        c_30d_avg = df_df_30["Calories"].mean() if not df_df_30.empty else 0.0
                        
                        # Weekend vs weekday
                        df_df_30 = df_df_30.copy()
                        df_df_30["is_weekend"] = df_df_30["Date"].dt.dayofweek.isin([5, 6])
                        c_wd = df_df_30[~df_df_30["is_weekend"]]["Calories"].mean()
                        c_we = df_df_30[df_df_30["is_weekend"]]["Calories"].mean()
                        wd_vs_we = f"Weekend Average: {c_we:.0f} kcal vs Weekdays: {c_wd:.0f} kcal."
                    else:
                        wd_vs_we = "No intake logs found."
                        
                    # Weight change
                    w_trend = "No weight records in the last 30 days."
                    if not df_weight.empty:
                        df_w_30 = df_weight[df_weight["date"] >= limit_30d].sort_values("date")
                        if not df_w_30.empty:
                            w_start = df_w_30.iloc[0]["weight"]
                            w_end = df_w_30.iloc[-1]["weight"]
                            w_trend = f"Weight changed from {w_start:.1f} to {w_end:.1f} over the recorded period."
                            
                            # Check plateau
                            if len(df_w_30) >= 3:
                                last_few = df_w_30.tail(5)["weight"]
                                if last_few.std() < 0.6:
                                    w_trend += f" Weight has plateaued at {last_few.mean():.1f} recently."
                                    
                    profile_target_c = st.session_state.profile.get("target_calories", 2000)
                    profile_target_w = st.session_state.profile.get("target_weight", 150)
                    
                    summary_payload = (
                        f"Current Target Daily Calorie Budget: {profile_target_c} kcal. "
                        f"Actual average intake (last 7 days): {c_7d_avg:.0f} kcal. "
                        f"Actual average intake (last 30 days): {c_30d_avg:.0f} kcal. "
                        f"Weight status: {w_trend}. Target Weight: {profile_target_w}. "
                        f"Weekly patterns: {wd_vs_we}"
                    )
                    
                    user_prefs = st.session_state.profile.get("food_preferences") or []
                    prefs_str = f"User's dietary preferences & exclusions: {', '.join(user_prefs)}." if user_prefs else "User has no specific dietary preferences or exclusions."
                    
                    # Prompt Gemini
                    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                    system_prompt = (
                        "You are an expert, supportive dietitian and wellness advisor. "
                        f"Important constraint: {prefs_str} "
                        "Given the user's historical fitness summaries, construct a bulleted set "
                        "of 3-4 highly encouraging, data-backed feedback points. Suggest concrete adjustments "
                        "based on their target goals. Ensure that any meal, food, or recipe suggestions strictly "
                        "comply with their dietary preferences and exclusions. Do not output raw text blocks. Keep insights analytical and easy to digest."
                    )
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=f"{system_prompt}\n\nUser Data Summary:\n{summary_payload}",
                    )
                    
                    st.session_state.coach_recommendations = response.text
                except Exception as e:
                    st.error(f"Could not generate AI coach feedback: {e}")
                    
        if "coach_recommendations" in st.session_state:
            st.markdown(f"""
            <div class='glass-card' style='background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.25);'>
                <h4 style='color:#34d399;'>📋 Strategic Observations:</h4>
                <div style='line-height:1.6;'>
                    {st.session_state.coach_recommendations}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🔍 Retrieve Historical Food Entry Logs")
        st.markdown("<p style='font-size:0.9rem; color:#94a3b8;'>Select a start and end date to retrieve a complete list of your past logged food entries.</p>", unsafe_allow_html=True)
        
        # Select date range
        range_cols = st.columns([1, 2])
        with range_cols[0]:
            selected_range = st.date_input(
                "Date Range Selector",
                value=(date.today() - timedelta(days=7), date.today()),
                help="Select a range of dates to pull entries for."
            )
        
        # Parse dates
        if isinstance(selected_range, (tuple, list)) and len(selected_range) == 2:
            q_start, q_end = selected_range
        elif isinstance(selected_range, (tuple, list)) and len(selected_range) == 1:
            q_start = selected_range[0]
            q_end = q_start
        else:
            q_start = selected_range
            q_end = selected_range
            
        # Perform query
        try:
            hist_res = supabase_client.table("food_logs") \
                .select("*") \
                .eq("user_id", st.session_state.user.id) \
                .gte("date", str(q_start)) \
                .lte("date", str(q_end)) \
                .order("date", desc=True) \
                .execute()
            hist_logs = hist_res.data if hist_res.data else []
        except Exception as e:
            st.error(f"Error fetching historical logs: {e}")
            hist_logs = []
            
        # Render logs
        if hist_logs:
            df_hist = pd.DataFrame(hist_logs)
            df_hist["date"] = pd.to_datetime(df_hist["date"]).dt.strftime("%Y-%m-%d")
            df_hist = df_hist[["date", "food_name", "meal_type", "calories"]]
            df_hist.columns = ["Date", "Food Name", "Meal Type", "Calories (kcal)"]
            
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
            
            total_range_cals = df_hist["Calories (kcal)"].sum()
            st.markdown(f"**Total Calorie Intake in Range:** {total_range_cals} kcal")
        else:
            st.info("No food logs found for the selected date range.")
