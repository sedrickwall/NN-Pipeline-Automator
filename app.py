import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from difflib import get_close_matches
import io

st.set_page_config(page_title="Pipeline Automator", layout="wide")

st.title("🚀 Pipeline Status & Region Automator")

# --- 1. SETTINGS & ANCHOR ---
st.sidebar.header("Configuration")
anchor_date = st.sidebar.date_input("Select Anchor Date", datetime(2026, 1, 9))
one_year_out = pd.to_datetime(anchor_date) + timedelta(days=365)

# --- 2. REGION MAPPING LOGIC ---
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

# --- 3. FILE UPLOADER ---
uploaded_file = st.file_uploader("Upload Salesforce Export (CSV or Excel)", type=['csv', 'xlsx'])

if uploaded_file:
    # Read the file
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    # Clean column names (remove hidden spaces)
    df.columns = [c.strip() for c in df.columns]

    if st.button("Generate Cleaned Pipeline"):
        
        # --- 4. THE CUSTOM STATUS LOGIC ---
        def calculate_status(row):
            # Get values safely and handle "NaN" values
            name = str(row.get('Opportunity Name', '')).strip()
            desc = str(row.get('Opportunity Description', '')).lower()
            prop_age = str(row.get('Proposal age', '')).strip()
            
            # RULE A: HOLD CHECK (Looking for exactly 41 matches as per your sample)
            if "hold" in name.lower():
                return "On Hold"
            
            # RULE B: PROPOSAL AGE BYPASS (Active regardless of description)
            if prop_age in ["0-3 Months", "3-6 Months"]:
                return "Active"
            
            # RULE C: DESCRIPTION DATE LOGIC
            # Mark as Update Needed if: Blank, 'nan', or contains 2024
            if desc == "" or desc == "nan" or "2024" in desc:
                return "Direct Update Needed" if "direct" in name.lower() else "CRO Update Needed"
            
            # Mark as Active if: Contains 2025 or 2026
            if "2025" in desc or "2026" in desc:
                return "Active"
            
            # RULE D: FALLBACK (Anything else defaults to update needed)
            return "Direct Update Needed" if "direct" in name.lower() else "CRO Update Needed"

        # Apply Logic
        df['Status'] = df.apply(calculate_status, axis=1)
        
        # Apply Region Logic (Looks for any column with "Country" in it)
        country_col = next((c for c in df.columns if 'Country' in c), None)
        if country_col:
            df['Region'] = df[country_col].apply(get_region_fuzzy)
        else:
            df['Region'] = "Country Column Not Found"

        # --- 5. DISPLAY RESULTS ---
        st.subheader("Summary Breakdown")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Status Counts**")
            st.write(df['Status'].value_counts())
            
        with col2:
            st.write("**Region Counts**")
            st.write(df['Region'].value_counts())

        # --- 6. EXCEL DOWNLOAD ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Cleaned Pipeline')
        
        st.download_button(
            label="📥 Download Cleaned Excel File",
            data=output.getvalue(),
            file_name=f"Cleaned_Pipeline_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.subheader("Data Preview")
        st.dataframe(df.head(50))