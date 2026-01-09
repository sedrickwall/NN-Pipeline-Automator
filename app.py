import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from difflib import get_close_matches
import io

st.set_page_config(page_title="Pipeline Automator", layout="wide")

st.title("🚀 Pipeline Status & Region Automator")

# --- 1. SETTINGS ---
st.sidebar.header("Configuration")
anchor_date = st.sidebar.date_input("Select Anchor Date", datetime(2026, 1, 9))
one_year_out = pd.to_datetime(anchor_date) + timedelta(days=365)

# --- 2. REGION MAPPING ---
regions = {
    "US": ["United States", "USA", "US"],
    "APAC": ["China", "India", "South Korea", "Japan", "Singapore", "Hong Kong", "Taiwan", "Vietnam", "Australia", "New Zealand"],
    "EU": ["France", "Germany", "Italy", "Spain", "Ireland", "Netherlands", "Belgium", "Denmark", "Sweden", "Finland", "Switzerland", "United Kingdom", "Czech Republic"]
}
all_known_countries = [c for sublist in regions.values() for c in sublist]

def get_region_fuzzy(input_country):
    if pd.isna(input_country): return "Missing Country"
    name = str(input_country).strip()
    for region, countries in regions.items():
        if name.lower() in [c.lower() for c in countries]: return region
    matches = get_close_matches(name, all_known_countries, n=1, cutoff=0.7)
    if matches:
        for region, countries in regions.items():
            if matches[0] in countries: return region
    return "Rest of World"

# --- 3. PROCESSING ---
uploaded_file = st.file_uploader("Upload Salesforce Export", type=['csv', 'xlsx'])

if uploaded_file:
    # Handle both file types for import
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # Auto-detect column names
    name_col = next((c for c in df.columns if 'Opportunity Name' in c), 'Opportunity Name')
    date_col = next((c for c in df.columns if 'Close Date' in c or 'Date' in c), 'Close Date')
    country_col = next((c for c in df.columns if 'Country' in c), None)

    if st.button("Generate Cleaned Pipeline"):
        # Calculate Status Logic
        def calculate_status(row):
            opp_name = str(row.get(name_col, '')).strip()
            close_date = pd.to_datetime(row.get(date_col), errors='coerce')
            if "Hold" in opp_name: return "On Hold"
            if pd.notnull(close_date) and close_date <= one_year_out: return "Active"
            return "Direct Update Needed" if "Direct" in opp_name else "CRO Update Needed"

        df['Status'] = df.apply(calculate_status, axis=1)
        df['Region'] = df[country_col].apply(get_region_fuzzy) if country_col else "N/A"

        # --- 4. DATA SUMMARY TABLE ---
        st.subheader("Summary: Items Requiring Updates")
        # Creates a pivot table showing counts of status per region
        summary_table = pd.crosstab(df['Region'], df['Status'])
        st.table(summary_table)

        # --- 5. EXCEL EXPORT LOGIC ---
        # We create a buffer to store the Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Cleaned Pipeline')
        
        processed_data = output.getvalue()

        st.download_button(
            label="📥 Download Cleaned Data (Excel File)",
            data=processed_data,
            file_name=f"Cleaned_Pipeline_{anchor_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )