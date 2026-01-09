import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re
from difflib import get_close_matches

st.set_page_config(page_title="Pipeline Automator", layout="wide")

st.title("🚀 Pipeline Status & Region Automator")
st.markdown("Calibrated for: **207 Active | 41 Hold | 36 Direct | 27 CRO**")

# --- 1. CONFIGURATION & REGION MAP ---
st.sidebar.header("Configuration")
anchor_date = st.sidebar.date_input("Select Anchor Date", datetime(2026, 1, 9))

regions_map = {
    "US": ["United States", "USA", "US"],
    "APAC": ["China", "India", "South Korea", "Japan", "Singapore", "Hong Kong", "Taiwan", "Vietnam", "Australia", "New Zealand"],
    "EU": ["France", "Germany", "Italy", "Spain", "Ireland", "Netherlands", "Belgium", "Denmark", "Sweden", "Finland", "Switzerland", "United Kingdom", "Czech Republic"]
}
all_known_countries = [c for sublist in regions_map.values() for c in sublist]

# --- 2. LOGIC ENGINES ---

def get_region_fuzzy(input_country):
    if pd.isna(input_country) or str(input_country).strip() == "": return "Rest of World"
    name = str(input_country).strip()
    for region, countries in regions_map.items():
        if name.lower() in [c.lower() for c in countries]: return region
    matches = get_close_matches(name, all_known_countries, n=1, cutoff=0.7)
    if matches:
        for region, countries in regions_map.items():
            if matches[0] in countries: return region
    return "Rest of World"

def get_first_line_year(text):
    if not isinstance(text, str) or text.strip() == "" or text.lower() == "nan":
        return None
    first_line = text.split('\n')[0].strip().upper()
    snippet = first_line[:35]
    
    y4 = re.findall(r'202[5-7]', first_line) 
    if y4: return int(y4[0])
    
    months = r'JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER'
    y2_match = re.findall(rf'({months})\s?(\d{{2}})\b', first_line)
    if y2_match: return 2000 + int(y2_match[0][1])
    
    y2_standalone = re.findall(r'(?:\s|/)(2[5-7])\b', first_line)
    if y2_standalone: return 2000 + int(y2_standalone[0])

    if "2024" in first_line or "24" in first_line: return 2024
    return None

def calculate_status(row, nk, dk, ak):
    name = str(row.get(nk, '')).strip().lower()
    desc = str(row.get(dk, ''))
    prop_age = str(row.get(ak, '')).lower().strip()
    
    if any(x in name for x in ["hold", "[hold]", "(hold)"]): return "Hold"
    if any(x in prop_age for x in ["0 to 3", "3 to 6", "0-3", "3-6"]): return "Active"
    
    year = get_first_line_year(desc)
    if year and year >= 2025: return "Active"
    
    return "Direct Update Needed" if "direct" in name else "CRO Update Needed"

# --- 3. APP INTERFACE ---

uploaded_file = st.file_uploader("Upload Salesforce Export", type=['csv', 'xlsx'])

if uploaded_file:
    # Clear session state if a brand new file is uploaded to prevent 'unpacking' errors
    if 'last_uploaded' not in st.session_state or st.session_state.last_uploaded != uploaded_file.name:
        for key in ['df_final', 'keys']:
            if key in st.session_state: del st.session_state[key]
        st.session_state.last_uploaded = uploaded_file.name

    if st.button("Run Full Automation"):
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        df.columns = [c.strip() for c in df.columns]
        
        # Identification
        nk = next((c for c in df.columns if 'Opportunity Name' in c), 'Opportunity Name')
        dk = next((c for c in df.columns if 'Description' in c), 'Opportunity Description')
        ak = next((c for c in df.columns if 'Age' in c), 'Proposal Age')
        ck = next((c for c in df.columns if 'Country' in c or 'Billing Country' in c), None)
        
        # Apply Status & Region
        df['Status'] = df.apply(lambda r: calculate_status(r, nk, dk, ak), axis=1)
        df['Region'] = df[ck].apply(get_region_fuzzy) if ck else "Rest of World"

        # Save everything to session state at once
        st.session_state['df_final'] = df
        st.session_state['keys'] = (nk, dk, ak, ck)

    # Use a robust check for session state
    if 'df_final' in st.session_state and 'keys' in st.session_state:
        df = st.session_state['df_final']
        keys = st.session_state['keys']
        
        # Safeguard unpacking
        nk = keys[0]
        dk = keys[1]
        ak = keys[2]
        ck = keys[3]

        # --- SUMMARY ---
        st.subheader("Classification Summary")
        counts = df['Status'].value_counts()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Active", counts.get("Active", 0), "Target: 207")
        c2.metric("Hold", counts.get("Hold", 0), "Target: 41")
        c3.metric("Direct Update", counts.get("Direct Update Needed", 0), "Target: 36")
        c4.metric("CRO Update", counts.get("CRO Update Needed", 0), "Target: 27")

        # --- DOWNLOAD ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Cleaned Pipeline')
        
        st.download_button("📥 Download Final Excel", output.getvalue(), "Final_Pipeline_Master.xlsx")

        st.subheader("Logic Preview")
        st.dataframe(df[[nk, 'Region', 'Status', dk]].head(100), use_container_width=True) 