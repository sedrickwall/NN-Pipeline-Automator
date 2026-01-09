import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re
from difflib import get_close_matches

st.set_page_config(page_title="Pipeline Automator", layout="wide")

st.title("🚀 Pipeline Status & Region Automator")
st.markdown("Calibrated for: **207 Active | 41 Hold | 36 Direct | 27 CRO**")

# --- 1. REGION MAPPING ---
regions_map = {
    "US": ["United States", "USA", "US"],
    "APAC": ["China", "India", "South Korea", "Japan", "Singapore", "Hong Kong", "Taiwan", "Vietnam", "Australia", "New Zealand"],
    "EU": ["France", "Germany", "Italy", "Spain", "Ireland", "Netherlands", "Belgium", "Denmark", "Sweden", "Finland", "Switzerland", "United Kingdom", "Czech Republic"]
}
all_known_countries = [c for sublist in regions_map.values() for c in sublist]

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

# --- 2. THE REFINED "FIRST-DATE" ENGINE ---

def get_actual_update_year(text):
    """
    Finds the VERY FIRST date mentioned in the first line of the description.
    This identifies the date the note was written, ignoring future goals mentioned later.
    """
    if not isinstance(text, str) or text.strip() == "" or text.lower() == "nan":
        return None
    
    # Take only the first line
    first_line = text.split('\n')[0].strip().upper()
    
    # Define date patterns
    # Matches: 2024, 2025, 2026, OCT25, Oct 25, /25, /24
    months = r'JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER'
    
    found_matches = []

    # 1. Search for 4-digit years
    for m in re.finditer(r'\b(202[3-6])\b', first_line):
        found_matches.append((m.start(), int(m.group())))

    # 2. Search for Month + 2-digit years (e.g., NOV 24, OCT25)
    for m in re.finditer(rf'({months})\s?(\d{{2}})\b', first_line):
        found_matches.append((m.start(2), 2000 + int(m.group(2))))

    # 3. Search for slash dates (e.g., /24, /25)
    for m in re.finditer(r'/(2[3-6])\b', first_line):
        found_matches.append((m.start(1), 2000 + int(m.group(1))))

    if not found_matches:
        return None
    
    # Sort by where they appear in the string. 
    # The one with the lowest index (start position) is the actual Update Date.
    found_matches.sort(key=lambda x: x[0])
    return found_matches[0][1]

def calculate_status(row, nk, dk, ak):
    name = str(row.get(nk, '')).strip().lower()
    desc = str(row.get(dk, ''))
    prop_age = str(row.get(ak, '')).lower().strip()
    
    if any(x in name for x in ["hold", "[hold]", "(hold)"]): return "Hold"
    if any(x in prop_age for x in ["0 to 3", "3 to 6", "0-3", "3-6"]): return "Active"
    
    # Identify the year of the MOST RECENT update (the first date in the first line)
    update_year = get_actual_update_year(desc)
    
    if update_year and update_year >= 2025:
        return "Active"
    
    # If the first date found is 2024 or earlier, OR if no date is found
    return "Direct Update Needed" if "direct" in name else "CRO Update Needed"

# --- 3. APP INTERFACE ---

uploaded_file = st.file_uploader("Upload Salesforce Export", type=['csv', 'xlsx'])

if uploaded_file:
    if st.button("Run Final Calibrated Automation"):
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        df.columns = [c.strip() for c in df.columns]
        
        nk = next((c for c in df.columns if 'Opportunity Name' in c), 'Opportunity Name')
        dk = next((c for c in df.columns if 'Description' in c), 'Opportunity Description')
        ak = next((c for c in df.columns if 'Age' in c), 'Proposal Age')
        ck = next((c for c in df.columns if 'Country' in c or 'Billing Country' in c), None)
        
        df['Status'] = df.apply(lambda r: calculate_status(r, nk, dk, ak), axis=1)
        df['Region'] = df[ck].apply(get_region_fuzzy) if ck else "Rest of World"

        st.session_state['df_final'] = df
        st.session_state['keys'] = (nk, dk, ak, ck)

    if 'df_final' in st.session_state:
        df = st.session_state['df_final']
        nk, dk, ak, ck = st.session_state['keys']

        # Metrics
        counts = df['Status'].value_counts()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Active", counts.get("Active", 0), "Target: 207")
        c2.metric("Hold", counts.get("Hold", 0), "Target: 41")
        c3.metric("Direct Update", counts.get("Direct Update Needed", 0), "Target: 36")
        c4.metric("CRO Update", counts.get("CRO Update Needed", 0), "Target: 27")

        # Excel Download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Cleaned Pipeline')
        st.download_button("📥 Download Final Excel", output.getvalue(), "Final_Pipeline_Master.xlsx")

        st.subheader("Logic Preview")
        st.dataframe(df[[nk, 'Region', 'Status', dk]].head(100), use_container_width=True)