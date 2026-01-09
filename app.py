import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re

st.set_page_config(page_title="Pipeline Automator", layout="wide")

st.title("🚀 Pipeline Status Automator (v7)")
st.markdown("Calibrated to hit your target distribution: **207 Active | 41 Hold | 36 Direct | 27 CRO**")

# --- 1. SETTINGS ---
st.sidebar.header("Configuration")
anchor_date = st.sidebar.date_input("Select Anchor Date", datetime(2026, 1, 9))

# --- 2. LOGIC FUNCTIONS ---

def get_first_line_year(text):
    """
    Looks only at the first line of notes to find the date of the latest update.
    Returns the year (e.g., 2024, 2025) or None.
    """
    if not isinstance(text, str) or text.strip() == "" or text.lower() == "nan":
        return None
    
    # We only care about the very first line
    first_line = text.split('\n')[0].strip().upper()
    
    # Snippet search: Look for year markers in the first 30 characters
    snippet = first_line[:35]
    
    # 1. Look for 4-digit years (2024-2027)
    y4 = re.findall(r'202[3-7]', snippet)
    if y4: return int(y4[0])
    
    # 2. Look for Month + 2-digit Year (e.g., OCT 25, July 25, 25-AUG)
    months = r'JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER'
    y2_match = re.findall(rf'({months}).*?\b(\d{{2}})\b', snippet)
    if y2_match: return 2000 + int(y2_match[0][1])
        
    # 3. Look for Slash dates (e.g., /25)
    slash_match = re.findall(r'/(2[4-7])\b', snippet)
    if slash_match: return 2000 + int(slash_match[0])
    
    return None

def calculate_status(row, name_key, desc_key, age_key):
    name = str(row.get(name_key, '')).strip().lower()
    desc = str(row.get(desc_key, ''))
    prop_age = str(row.get(age_key, '')).lower().strip()
    
    # 1. PRIORITY: HOLD
    if any(x in name for x in ["hold", "[hold]", "(hold)"]):
        return "Hold"
    
    # 2. PRIORITY: NEW PROPOSALS (0-6 Months is Active)
    if any(x in prop_age for x in ["0 to 3", "3 to 6", "0-3", "3-6"]):
        return "Active"
    
    # 3. DATE CHECK (First Line Only)
    year = get_first_line_year(desc)
    if year:
        if year >= 2025:
            return "Active"
        else:
            # Update needed because the latest note is from 2024 or earlier
            return "Direct Update Needed" if "direct" in name else "CRO Update Needed"
    
    # 4. FALLBACK: If no date found in the first line
    return "Direct Update Needed" if "direct" in name else "CRO Update Needed"

# --- 3. APP PROCESSING ---

uploaded_file = st.file_uploader("Upload Salesforce Export", type=['csv', 'xlsx'])

if uploaded_file:
    # Logic to process and store result in session to keep download stable
    if "df_final" not in st.session_state:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        df.columns = [c.strip() for c in df.columns]
        
        # Mapping Columns
        nk = next((c for c in df.columns if 'Opportunity Name' in c), 'Opportunity Name')
        dk = next((c for c in df.columns if 'Description' in c), 'Opportunity Description')
        ak = next((c for c in df.columns if 'Age' in c), 'Proposal Age')
        
        df['Status'] = df.apply(lambda r: calculate_status(r, nk, dk, ak), axis=1)
        
        st.session_state.df_final = df
        st.session_state.keys = (nk, dk, ak)

    df = st.session_state.df_final
    nk, dk, ak = st.session_state.keys

    # --- 4. SUMMARY METRICS ---
    counts = df['Status'].value_counts()
    st.subheader("Classification Results")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active", counts.get("Active", 0), "Target: 207")
    c2.metric("Hold", counts.get("Hold", 0), "Target: 41")
    c3.metric("Direct Update", counts.get("Direct Update Needed", 0), "Target: 36")
    c4.metric("CRO Update", counts.get("CRO Update Needed", 0), "Target: 27")

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

    # --- 6. PREVIEW & HIGHLIGHTING ---
    def highlight_first_line(text):
        if not isinstance(text, str) or '\n' not in text: return text
        parts = text.split('\n', 1)
        # Bold the first line to show where the logic focused
        return f"**{parts[0]}**\n{parts[1]}"

    st.subheader("Audit Preview")
    df_preview = df.copy().head(100)
    df_preview['Notes (First Line Bolded)'] = df_preview[dk].apply(highlight_first_line)
    st.dataframe(df_preview[[nk, ak, 'Status', 'Notes (First Line Bolded)']], use_container_width=True)