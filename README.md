# 🥑 ByteSize Nutrition & Weight Tracker

ByteSize is a mobile-responsive, theme-adaptive Streamlit application designed for logging nutrition and forecasting weight goals. Powered by a **Supabase backend** and **Google Gemini API** (via the modern `google-genai` SDK), ByteSize makes it easy to log meals through photos or text and analyze long-term health trends.

---

## ✨ Features

### 1. 🧠 Smart AI Meal Parser (Multimodal)
- **Text & Photo Inputs**: Describe what you ate in plain English (e.g., *"2 scrambled eggs and a slice of sourdough toast for breakfast"*) or upload a meal image directly.
- **Structured Extraction**: Gemini 3.5 Flash processes inputs and returns structured JSON (validated using strict Pydantic schemas) containing food items, portions, and calories.
- **Editable Spreadsheet Grid**: Refine food logs, adjust serving sizes, delete items, and recalculate totals in real time before bulk submitting to the database.

### 2. ⚖️ Weight Tracker & Interactive Forecast
- **Scale Weight Log**: Log daily scale weights (capped at one check-in per calendar date).
- **Linear Trend Projections**: Fits historical weights using `numpy.polyfit` to model your rate-of-change and projects weight trajectories for the next 30 days.
- **Plotly Dual-Axis Graph**: Overlaps average weekly calorie intake against your scale weight and dashed goal trajectory lines.
- **Goal Trajectory Dashboard**: Computes an estimate of the number of days remaining until you reach your target weight.

### 3. 🔒 Secure Authentication & Onboarding
- **Supabase Auth**: Complete secure email signup and login gate.
- **Onboarding Guard**: Guides new users to set up their daily calorie budgets, target weights, and initial weights. Prevents dashboard access until setup is complete.

### 4. 🔥 Consistency Streaks & Gamification
- Calculates daily logging consistency across both weight and nutrition logs, displaying a streak badge (e.g., `🔥 5-Day Streak`) inside the sidebar.

### 5. 💬 AI Health Coach Engine
- Evaluates the past 30 days of tracking data (averages, weekday vs. weekend deviations, weight trend slope) and prompts Gemini to compile data-backed Strategic Observations.

---

## 🛠️ Technology Stack
- **Frontend / Dashboard**: [Streamlit](https://streamlit.io/) (including custom typography, responsive CSS overrides, and `@st.dialog` confirmation pop-ups)
- **Database / Auth**: [Supabase](https://supabase.com/) (`supabase-py` client)
- **AI Engine**: [Google Gemini SDK](https://github.com/google/generative-ai-python) (`google-genai`)
- **Plotting**: [Plotly Graph Objects](https://plotly.com/python/)
- **Data Engineering**: [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/), [Pydantic v2](https://docs.pydantic.dev/)

---

## ⚙️ Configuration & Installation

### 1. Prerequisites
Ensure you have Python 3.9+ installed. Clone the repository and install the dependencies:
```bash
pip install -r requirements.txt
```

### 2. Configure Credentials
Create a `.streamlit/secrets.toml` file inside the project root and add your API keys:
```toml
# Supabase Configuration
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-supabase-anon-key"

# Gemini API Configuration
GEMINI_API_KEY = "your-gemini-api-key"
```

### 3. Run the App Locally
```bash
python -m streamlit run app.py
```
The app will launch in your browser at `http://localhost:8501`.
