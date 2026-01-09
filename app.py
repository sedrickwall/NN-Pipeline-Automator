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
# The anchor date helps the code understand that 25/26 are future/current dates
anchor_date = st.sidebar.date_input("Select Anchor Date", datetime(2026, 1, 9))

# --- 2. THE REFINED DATE ENGINE ---

def get_first_line_year(text):
    """
    Scans the first line for the latest update year.
    Matches: '29OCT25', 'July 25', '2025', '/26', etc.
    """
    if not isinstance(text, str) or text.strip() == "" or text.lower() == "nan":
        return None
    
    # We focus strictly on the first line
    first_line = text.split('\n')[0].strip().upper()
    
    # 1. Look for 4-digit years (2025-2027)
    y4 = re.findall(r'202[5-7]', first_line)
    if y4: return int(y4[0])
    
    # 2. Look for Month + 2-digit Year (e.g., OCT25, OCT 25, JULY 25)
    # This regex is now more flexible to catch 'KMT 29OCT25'
    months = r'JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER'
    y2_match = re.findall(rf'({months})\s?(\d{{2}})\b', first_line)
    if y2_match: return 2000 + int(y2_match[0][1])
    
    # 3. Look for any standalone 25, 26, or 27 that isn't a day of the month
    # We look for 25/26/27 preceded by a space or slash
    y2_standalone = re.findall(r'(?:\s|/)(2[5-7])\b', first_line)
    if y2_standalone: return 2000 + int(y2_standalone[0])

    # 4. Fallback for 2024 (if no future date found)
    if "2024" in first_line or "24" in first_line:
        return 2024
    
    return None

def calculate_status(row, nk, dk, ak):
    name = str(row.get(nk, '')).strip().lower()
    desc = str(row.get(dk, ''))
    prop_age = str(row.get(ak, '')).lower().strip()
    
    # RULE 1: HOLD (Absolute Priority)
    if any(x in name for x in ["hold", "[hold]", "(hold)"]):
        return "Hold"
    
    # RULE 2: NEW PROPOSAL (0-6 Months is Active)
    if any(x in prop_age for x in ["0 to 3", "3 to 6", "0-3", "3-6"]):
        return "Active"
    
    # RULE 3: FIRST-LINE DATE CHECK
    year = get_first_line_year(desc)
    if year and year >= 2025:
        return "Active"
    
    # RULE 4: FALLBACK
    return "Direct Update Needed" if "direct" in name else "CRO Update Needed"

# --- 3. APP INTERFACE ---

uploaded_file = st.file_uploader("Upload Salesforce Export", type=['csv', 'xlsx'])

if uploaded_file:
    if st.button("Run Automation"):
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        df.columns = [c.strip() for c in df.columns]
        
        # Column Identification
        nk = next((c for c in df.columns if 'Opportunity Name' in c), 'Opportunity Name')
        dk = next((c for c in df.columns if 'Description' in c), 'Opportunity Description')
        ak = next((c for c in df.columns if 'Age' in c), 'Proposal Age')
        
        # Processing
        df['Status'] = df.apply(lambda r: calculate_status(r, nk, dk, ak), axis=1)
        st.session_state['df_final'] = df
        st.session_state['keys'] = (nk, dk, ak)

    if 'df_final' in st.session_state:
        df = st.session_state['df_final']
        nk, dk, ak = st.session_state['keys']

        # Metrics
        counts = df['Status'].value_counts()
        st.subheader("Classification Results")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Active", counts.get("Active", 0), "Target: 207")
        c2.metric("Hold", counts.get("Hold", 0), "Target: 41")
        c3.metric("Direct Update", counts.get("Direct Update Needed", 0), "Target: 36")
        c4.metric("CRO Update", counts.get("CRO Update Needed", 0), "Target: 27")

        # Download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Cleaned Pipeline')
        
        st.download_button("📥 Download Excel", output.getvalue(), "Final_Pipeline.xlsx")

        # Preview
        def bold_first(text):
            if not isinstance(text, str) or '\n' not in text: return text
            parts = text.split('\n', 1)
            return f"**{parts[0]}**\n{parts[1]}"

        st.subheader("Logic Preview (First Line Bolded)")
        df_preview = df.copy().head(100)
        df_preview['First Line Note'] = df_preview[dk].apply(bold_first)
        st.dataframe(df_preview[[nk, ak, 'Status', 'First Line Note']], use_container_width=True)