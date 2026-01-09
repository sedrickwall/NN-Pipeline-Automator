import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re

st.set_page_config(page_title="Pipeline Automator", layout="wide")

st.title("🚀 Pipeline Status Automator")
st.markdown("Calibrated for: **207 Active | 41 Hold | 36 Direct | 27 CRO**")

# --- 1. SETTINGS ---
st.sidebar.header("Configuration")
anchor_date = st.sidebar.date_input("Select Anchor Date", datetime(2026, 1, 9))

# --- 2. LOGIC FUNCTIONS ---

def get_first_line_year(text):
    """Focuses only on the first line to determine update freshness."""
    if not isinstance(text, str) or text.strip() == "" or text.lower() == "nan":
        return None
    
    # Extract only the first line
    first_line = text.split('\n')[0].strip().upper()
    snippet = first_line[:35]
    
    # 1. 4-digit years
    y4 = re.findall(r'202[3-7]', snippet)
    if y4: return int(y4[0])
    
    # 2. Month + 2-digit Year
    months = r'JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER'
    y2_match = re.findall(rf'({months}).*?\b(\d{{2}})\b', snippet)
    if y2_match: return 2000 + int(y2_match[0][1])
        
    # 3. Slash dates
    slash_match = re.findall(r'/(2[4-7])\b', snippet)
    if slash_match: return 2000 + int(slash_match[0])
    
    return None

def calculate_status(row, nk, dk, ak):
    name = str(row.get(nk, '')).strip().lower()
    desc = str(row.get(dk, ''))
    prop_age = str(row.get(ak, '')).lower().strip()
    
    if any(x in name for x in ["hold", "[hold]", "(hold)"]):
        return "Hold"
    
    if any(x in prop_age for x in ["0 to 3", "3 to 6", "0-3", "3-6"]):
        return "Active"
    
    year = get_first_line_year(desc)
    if year and year >= 2025:
        return "Active"
    
    return "Direct Update Needed" if "direct" in name else "CRO Update Needed"

# --- 3. FILE UPLOADER ---
uploaded_file = st.file_uploader("Upload Salesforce Export", type=['csv', 'xlsx'])

if uploaded_file:
    # Use a 'Process' flag to avoid the Unpacking Error
    if st.button("Apply Logic Calibration"):
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        df.columns = [c.strip() for c in df.columns]
        
        # Identify columns
        nk = next((c for c in df.columns if 'Opportunity Name' in c), 'Opportunity Name')
        dk = next((c for c in df.columns if 'Description' in c), 'Opportunity Description')
        ak = next((c for c in df.columns if 'Age' in c), 'Proposal Age')
        
        # Process and save to state
        df['Status'] = df.apply(lambda r: calculate_status(r, nk, dk, ak), axis=1)
        st.session_state['df_final'] = df
        st.session_state['keys'] = (nk, dk, ak)

    # Only show results if they exist in session state
    if 'df_final' in st.session_state:
        df = st.session_state['df_final']
        nk, dk, ak = st.session_state['keys']

        # --- SUMMARY ---
        counts = df['Status'].value_counts()
        st.subheader("Classification Results")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Active", counts.get("Active", 0), "Target: 207")
        c2.metric("Hold", counts.get("Hold", 0), "Target: 41")
        c3.metric("Direct Update", counts.get("Direct Update Needed", 0), "Target: 36")
        c4.metric("CRO Update", counts.get("CRO Update Needed", 0), "Target: 27")

        # --- DOWNLOAD ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Cleaned Pipeline')
        
        st.download_button("📥 Download Excel", output.getvalue(), "Cleaned_Pipeline.xlsx")

        # --- PREVIEW ---
        def bold_first(text):
            if not isinstance(text, str) or '\n' not in text: return text
            parts = text.split('\n', 1)
            return f"**{parts[0]}**\n{parts[1]}"

        st.subheader("Logic Preview (First Line Bolded)")
        df_preview = df.copy().head(100)
        df_preview['Notes'] = df_preview[dk].apply(bold_first)
        st.dataframe(df_preview[[nk, ak, 'Status', 'Notes']], use_container_width=True)