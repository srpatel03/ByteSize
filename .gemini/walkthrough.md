# Walkthrough - Supabase & Gemini Powered Nutrition Tracker

This document provides a summary of the components implemented for the nutrition and weight tracker Streamlit application.

## Completed Features

### 1. Database Connection & Client Setup
- Installed `streamlit`, `supabase`, `google-genai`, `pandas`, and `pydantic`.
- Configured client connections inside a cache utility using `st.cache_resource` for memory optimization.
- Created `c:\Users\srpat\Projects\ByteSize\.streamlit\secrets.toml` template to hold your credentials securely.
- Created a `.gitignore` file to ensure `.streamlit/secrets.toml`, virtual environments, and Python cache files are kept out of version control.


### 2. Multi-stage Security & Onboarding
- **Supabase Authentication**: Integrated `supabase.auth` inside a password login & registration screen. The dashboard only loads once a valid user session is active.
- **Onboarding Guard**: Intercepts unauthorized dashboard visits, prompting users to fill in their Target Calories and Target Weight. Saves configuration in the `profiles` table.

### 3. Log Intake Dashboard (Tab 1)
- **Real-Time Calorie Status**: Tracks logged vs target calories dynamically for the selected date.
- **AI Eating Tip**: Interacts with the new `google-genai` SDK using `gemini-3.5-flash` to output a custom one-sentence strategic suggestion, caching observations based on target date to optimize speed.
- **Smart parser**: Direct free-text entry ("scrambled eggs and sourdough bread for breakfast...") parsed via Gemini structured json configuration matching strict Pydantic schemas.
- **Data Editor**: Interactive spreadsheet with `st.data_editor` allowing users to edit, add, or delete items and calories before inserting them.
- **Scale Weight Tracker**: Logs body weights directly into the `weight_logs` table.

### 4. History & Analytics (Tab 2)
- **Granular Groupings**: Displays structured calorie intake and body weight trends by Day, Week, and Month.
- **Plotly Dual-Axis Graph**: Overlaps average weekly calorie consumption against scale weight logs.
- **AI Recommendation Engine**: Aggregates 30-day tracking statistics and requests Gemini to render encouraging health observations.

---

## How to Run the App

1. **Populate Secrets**:
   Open [secrets.toml](file:///c:/Users/srpat/Projects/ByteSize/.streamlit/secrets.toml) and update with your actual credentials:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `GEMINI_API_KEY`

## Advanced Features Added

### 1. Multimodal Photo Logging
- Added a file uploader `st.file_uploader` to accept JPG/PNG meal photos.
- Gemini 3.5 Flash processes the image bytes directly (`types.Part.from_bytes`) to identify food items, estimate portion sizes/servings, and calories per serving, populating the interactive data editor grid.

### 2. Consistency Streaks
- The app checks for unique dates logged under both `food_logs` and `weight_logs`.
- Calculates daily logging consistency and renders a burning flame badge (e.g., `🔥 5-Day Streak`) inside the sidebar control card.
- Implements cache-clearing (`st.cache_data.clear()`) on database submissions to update the streak instantly.

### 3. Weight Forecasting & Trajectory Forecast
- Analyzes weight change trends (slope) from your historical logs using `numpy.polyfit`.
- Renders a projected trend line (dashed blue line) on the weekly Plotly chart forecasting future weight for the next 30 days.
- Displays a smart "Weight Trajectory Forecast" panel detailing if you are on track to reach your goals and the estimated number of days.

---

## Bug Fixes & Usability Polish

### 1. Stable File Upload (Double-Upload Bug Fix)
- **Problem**: Previously, when first uploading an image, the file uploader key was initialized within the tab layout conditional block. When Streamlit triggered a rerun on file upload, the late initialization caused state mapping mismatch, resulting in the user needing to select and attach the file twice.
- **Solution**: Moved the initialization of `st.session_state.file_uploader_key` to the global application state block at the top of the file. This ensures the keys are initialized and registered on first boot and are fully stable across page reruns.

### 2. Reset Parser & Grid Button with Confirmation Dialog
- **Problem**: Users had no easy way to clear parsed data or loaded images if they wanted to start over without submitting, and clicking a reset button could accidentally discard changes without notice.
- **Solution**: Integrated a "Reset Parser & Grid" button inside the data editor action row, backed by a confirmation dialog decorated with `@st.dialog("Confirm Reset")`. Clicking the reset button opens a modal warning. If the user clicks "Yes, Reset", it:
  - Resets the `st.session_state.active_grid_data` to an empty state.
  - Increments `st.session_state.file_uploader_key` to reset the file uploader and text area inputs.
  - Triggers a rerun to dismiss the modal and refresh the UI.
  - Clicking "Cancel" simply reruns to dismiss the modal, keeping the state unchanged.

### 3. Responsive Sidebar Footer Credits
- **Problem**: The developer credit section at the bottom of the sidebar utilized a static `35vh` height spacer, pushing it down on desktops but creating massive unwanted empty space and vertical scroll on mobile/phone screens.
- **Solution**: Replaced the static inline spacer with a custom `.sidebar-footer-spacer` CSS class:
  - Defaults to `35vh` on desktop displays to keep the footer neatly at the bottom.
  - Adjusts down to `3vh !important` on screens narrower than `768px` using a CSS `@media` query, ensuring mobile users see the credits block dynamically positioned without any unnecessary scrolling.

### 4. Empty Body Weight Chart Fix
- **Problem**: When a user only has a single scale weight log (e.g., their starting weight from onboarding), Streamlit's `st.line_chart` renders as completely blank because it cannot draw a line with fewer than two points. Additionally, passing a Series with a datetime index can lead to index formatting and alignment bugs.
- **Solution**: 
  - Standardized all 6 daily, weekly, and monthly bar/line charts under the "History & Insights" page to use modern, robust DataFrame parameters (`x="Date"`, `y="Calories"`, etc.) instead of Series objects with `.set_index()`.
  - Added conditional checks for weight dataframes (`len(df) > 1`). If the dataframe contains more than one point, the app renders `st.line_chart`. If it contains exactly one point, the app automatically falls back to `st.scatter_chart` to render the single data point clearly as a marker.

### 5. Sign In Form Submission on Enter
- **Problem**: Previously, when entering credentials on the login screen, pressing the "Enter" key inside the fields did not submit the form. Users were forced to manually click the "Authenticate" button (or press TAB twice and then press Enter).
- **Solution**: Wrapped the text inputs and submit button inside an `st.form("login_form", border=False)` block and converted `st.button` to `st.form_submit_button`. This enables browser native form submission so that pressing "Enter" inside either input field triggers authentication immediately. Applied the same standard form wrapper to the "Create Account" sign up flow.

---

## Dietary Preference & Exclusions Integration

We added full-stack support for tracking user dietary preferences and food exclusions (e.g. Vegetarian, Vegan, Gluten-Free, Dairy-Free, Keto, Paleo, Halal, Kosher, Low-Carb, Nut-Free, Shellfish-Free).

### 1. Database Schema
Executed a migration to add a `food_preferences` column to the `profiles` table to store string arrays containing chosen options:
```sql
ALTER TABLE profiles ADD COLUMN food_preferences TEXT[] DEFAULT '{}';
```

### 2. Onboarding Workflow
- Added 3 columns of checkboxes inside the Onboarding Configuration form where new users select their dietary restrictions.
- The selections are collected in a list and inserted into the Supabase database.

### 3. Sidebar Display
- Automatically displays the user's logged preferences inside the sidebar card under `"Diet Preferences:"` for clear reference.

### 4. Updating Goals (Sidebar Intercept)
- Standardized the goals update panel to present the same checkboxes, pre-populating them based on the active user profile preferences.
- Updates the list in Supabase, and clears the front-end strategic eating tip cache to force a rerun using the new rules.

### 5. AI Prompt Compliance
- **Eating Coach Tip**: Passed the list of preferences into the prompt for the daily context tip to guide the model when formulating ideas (e.g. preventing meat suggestions for vegetarians).
- **AI Health Coach Engine**: Passed the constraints into the strategic recommendation coach prompt, forcing all suggested macro adjustments, recipes, and dietary improvements to strictly comply with the active preference rules.

---

## Historical Food Logs Search Table

We added a stand-alone, interactive query panel to retrieve and browse past logged food items on the "History & Insights" page.

### 1. Separate State & Query Flow
- The feature is fully stand-alone and executes its own Supabase select queries on demand.
- It does not modify, intercept, or impact the 30-day analytics datasets, metric widgets, Plotly graphs, or the AI Health Coach suggestions.

### 2. Date Range Picker & Table Placement
- Rendered an `st.date_input` configured for date range selection, defaulting to the last 7 days.
- Safely parses boundaries (handling both full ranges and in-progress single-date selection clicks).
- **Location**: Positioned at the very bottom of the "History & Insights" page, below the "AI Health Coach Engine" observations card, serving as a global log explorer.

### 3. Log Details Dataframe & Summary
- Queries the database for food logs matching the user's ID within the selected start and end dates.
- Formats dates and renders food entries in a clean `st.dataframe` showing columns: `Date`, `Food Name`, `Meal Type`, and `Calories (kcal)`.
- Automatically aggregates and displays the sum total of calories consumed during the selected date range.

---

## Remove Hour Ticks from History Charts

We adjusted all chart formatting rules to remove granular hour ticks and sub-day values (like "02 AM", "04 AM") from the X-axes of the History & Insights graphs.

### 1. Daily, Weekly, and Monthly Charts (Altair)
- Converted date columns in all 6 calorie intake and body weight dataframes to formatted strings (`%Y-%m-%d`) prior to rendering.
- This forces the underlying Altair chart engine to treat the dates as categorical (nominal) labels rather than a linear time-scale, preventing sub-day tick divisions.

### 2. Plotly Weight vs. Calorie Trends Graph
- Explicitly configured the Plotly layout to treat the X-axis as category data by adding `type="category"` to the `xaxis` layout parameter.
- This eliminates timestamp interpolation, ensuring the X-axis only displays the formatted date labels without empty fractional ticks.

---

## Persistent Login (Remember Me) Session Management

We implemented a full cookie-based user session manager to preserve user authentication state across browser refreshes and tab closures.

### 1. Dependencies & Cookie Controller
- Installed and registered `streamlit-cookies-controller` inside Python [requirements.txt](file:///c:/Users/srpat/Projects/ByteSize-AI/requirements.txt).
- Set up a global `CookieController` instance inside [app.py](file:///c:/Users/srpat/Projects/ByteSize-AI/app.py) to manage browser-side cookie parameters, combined with inline CSS overrides to clean up and hide component iframes from page views.

### 2. Native Synchronous Session Restoration
- Replaced custom client-side asynchronous checking loops with Streamlit's native `st.context.cookies` API.
- Because `st.context.cookies` reads standard HTTP request headers sent by the client during connection handshakes, the application evaluates credentials synchronously on the very first frame check.
- Bypasses any asynchronous loading spinner flags. Logged-in users are routed straight to their tracker dashboard on the very first page render with zero page lag or flashing.

### 3. Integrated Authentication Hook Actions
- **Secure Login & User Registration**: Captures valid user sessions and writes the corresponding `sb_access_token` and `sb_refresh_token` to browser cookies (defined with a 30-day expiration date).
- **Secure Log Out**: Clearing the session removes active tokens from the user's browser, forcing a manual credentials prompt on their next application visit.

---

## Edit & Delete Logged Records

We implemented direct controls to edit or delete logged entries for both food consumption and scale weights.

### 1. Scale Weight Deletion & Modification (Tab 1 - Log Intake)
- Modified the weight logging widget to remain enabled even if a record exists for the selected date.
- Shows two side-by-side action buttons: `Update Weight` (to modify the entry) and `Delete Entry` (to remove it).
- Implemented `@st.dialog("Confirm Delete Weight")` to ask the user for confirmation before purging the database log, clearing cached streak observations, and reloading the interface.
- Added persistent weight update, record, and deletion success prompts via `st.session_state` that display right inside the weight container to keep the user informed.

### 2. Historical Food Logs Modification & Deletion (Tab 2 - History & Insights)
- Converted the query explorer search table from a read-only `st.dataframe` to an interactive `st.data_editor` grid, capturing database primary key IDs hidden from the user (`"id": None`).
- Added a visual `"Delete?"` boolean checkbox column.
- Rendered a `Save Changes to Database` button. Saving compiles:
  - Rows with `Delete` checked are bulk-deleted from Supabase.
  - Rows with modified cells (comparing values to original query states) are bulk-updated in Supabase.
  - Total Calories metrics and charts clear their local data caches and reload instantly.
