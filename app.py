import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re

st.set_page_config(page_title="Pipeline Automator", layout="wide")

st.title("🚀 Pipeline Status Automator (v6 - Final Calibration)")
st.info("Calibrated for: 207 Active | 41 Hold | 36 Direct | 27 CRO")

# --- 1. SETTINGS ---
st.sidebar.header("Configuration")
anchor_date = st.sidebar.date_input("Select Anchor Date", datetime(2026, 1, 9))

# --- 2. LOGIC FUNCTIONS ---

def get_latest_year(text):
    """Finds the highest/latest year mentioned in the description."""
    if not isinstance(text, str) or text.strip() == "" or text.lower() == "nan":
        return None
    
    # Extract all 4-digit years (2023-2027)
    years = re.findall(r'\b(202[3-7])\b', text)
    
    # Extract 2-digit years with context (e.g., Oct 25, /26)
    months = 'JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC'
    short_years = re.findall(rf'(?:{months})[\s-]?(\d{{2}})\b', text, re.IGNORECASE)
    slash_years = re.findall(r'/(2[4-7])\b', text)
    
    found_years = [int(y) for y in years]
    found_years += [2000 + int(y) for y in short_years if 23 <= int(y) <= 27]
    found_years += [2000 + int(y) for y in slash_years]
    
    return max(found_years) if found_years else None

def calculate_status(row, name_col, desc_col, age_col):
    name = str(row.get(name_col, '')).strip().lower()
    desc = str(row.get(desc_col, '')).strip()
    # Cleaning 'Proposal age' string for comparison
    prop_age = str(row.get(age_key, '')).lower().replace('to', '-').replace(' ', '')
    
    # 1. HOLD CHECK (Priority 1)
    if any(x in name for x in ["hold", "(hold)", "[hold]"]):
        return "Hold"
    
    # 2. NEW PROPOSAL BYPASS (Priority 2)
    # Catches '0-3months', '3-6months', '0-3', '3-6'
    if any(x in prop_age for x in ["0-3", "3-6"]):
        # Rare exception: if name is Direct and desc is empty, it might need update
        # but overwhelmingly, 0-6 months is Active in your data.
        return "Active"
    
    # 3. DATE-BASED ACTIVE CHECK
    latest_year = get_latest_year(desc)
    
    # If 2025 or later is mentioned, it is Active
    if latest_year and latest_year >= 2025:
        return "Active"
    
    # If "Active" keyword is in the description and year is not 2024
    if "active" in desc.lower() and (latest_year is None or latest_year > 2024):
        return "Active"

    # 4. FALLBACK: UPDATE NEEDED
    if "direct" in name:
        return "Direct Update Needed"
    else:
        return "CRO Uipdate Needed"

# --- 3. FILE PROCESSING ---

uploaded_file = st.file_uploader("Upload Salesforce Export", type=['csv', 'xlsx'])

if uploaded_file:
    if "df_result" not in st.session_state:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        df.columns = [c.strip() for c in df.columns]
        
        # Identify columns
        name_key = next((c for c in df.columns if 'Opportunity Name' in c), 'Opportunity Name')
        desc_key = next((c for c in df.columns if 'Description' in c), 'Opportunity Description')
        age_key = next((c for c in df.columns if 'Age' in c), 'Proposal Age')
        
        # Process Logic
        df['Status'] = df.apply(lambda r: calculate_status(r, name_key, desc_key, age_key), axis=1)
        st.session_state.df_result = df
        st.session_state.cols = (name_key, desc_key, age_key)

    df = st.session_state.df_result
    name_key, desc_key, age_key = st.session_state.cols

    # --- 4. SUMMARY DASHBOARD ---
    counts = df['Status'].value_counts()
    
    st.subheader("Final Classification Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active", counts.get("Active", 0), "Target: 207")
    c2.metric("Hold", counts.get("Hold", 0), "Target: 41")
    c3.metric("Direct Update", counts.get("Direct Update Needed", 0), "Target: 36")
    c4.metric("CRO Update", counts.get("CRO Uipdate Needed", 0), "Target: 27")

    # --- 5. EXCEL EXPORT ---
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Cleaned Pipeline')
    
    st.download_button(
        label="📥 Download Cleaned Excel File",
        data=output.getvalue(),
        file_name=f"Cleaned_Pipeline_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # --- 6. PREVIEW WITH BOLD DATES ---
    st.subheader("Logic Preview")
    
    def highlight_logic(text):
        if not isinstance(text, str): return text
        # Bold 25/26/27 and "Hold"
        return re.sub(r'(2[5-7]|202[5-7]|Hold)', r'**\1**', text, flags=re.IGNORECASE)

    df_preview = df.copy().head(50)
    df_preview['Highlighted Notes'] = df_preview[desc_key].apply(highlight_logic)
    
    st.dataframe(
        df_preview[[name_key, age_key, 'Status', 'Highlighted Notes']],
        use_container_width=True
    )