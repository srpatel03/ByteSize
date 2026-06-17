# Goal: Remove Hour Ticks from History Charts

Format the date columns as string labels (`YYYY-MM-DD`) prior to rendering the Daily, Weekly, and Monthly charts in the "History & Insights" dashboard to prevent Streamlit/Altair from displaying hour/time increments (like "02 AM", "04 AM") on the X-axis.

## User Review Required

> [!NOTE]
> Converting the date/period start columns to strings (`%Y-%m-%d`) tells the underlying Altair chart engine to treat the X-axis as categorical (nominal) labels rather than a linear time-scale. This forces the chart to display *only* the specific date labels, eliminating automatic sub-day time intervals.

## Open Questions

None.

## Proposed Changes

---

### Visualization Formatting Updates

#### [MODIFY] [app.py](file:///c:/Users/srpat/Projects/ByteSize/app.py)

- **Daily Charts (Tab 2 - Daily Logs)**:
  - Format `df_daily_sorted["Date"]` as string using `.dt.strftime("%Y-%m-%d")` before calling `st.bar_chart`.
  - Format `df_weight_sorted["Date"]` as string using `.dt.strftime("%Y-%m-%d")` before calling `st.line_chart` or `st.scatter_chart`.
- **Weekly Charts (Tab 2 - Weekly Averages)**:
  - Format `df_weekly_avg["Week Starting"]` as string before rendering.
  - Format `df_weekly_w_avg["Week Starting"]` as string before rendering.
- **Monthly Charts (Tab 2 - Monthly Trends)**:
  - Format `df_monthly_avg["Month Starting"]` as string using `.dt.strftime("%Y-%m-%d")` before rendering.
  - Format `df_monthly_w_avg["Month Starting"]` as string using `.dt.strftime("%Y-%m-%d")` before rendering.

---

## Verification Plan

### Automated/Local Compilation
- Verify app.py compiles without errors.

### Manual Verification
1. **Daily Logs Chart Ticks**:
   - Navigate to "History & Insights" -> "📅 Daily Logs".
   - Verify that the X-axis of the "Calorie Intake (Per Day)" and "Body Weight Logs" charts show only dates (e.g. `2026-06-13`, `2026-06-14`) and do not display sub-day hour ticks (`02 AM`, `04 AM`).
2. **Weekly & Monthly Charts**:
   - Verify that the weekly and monthly charts show clean date strings.
