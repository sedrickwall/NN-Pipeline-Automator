import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re

st.set_page_config(page_title="Pipeline Automator", layout="wide")

st.title("🚀 Pipeline Status Automator (Calibration v4)")

# --- 1. SETTINGS ---
st.sidebar.header("Configuration")
anchor_date = st.sidebar.date_input("Select Anchor Date", datetime(2026, 1, 9))

# --- 2. FILE UPLOADER ---
uploaded_file = st.file_uploader("Upload Salesforce Export", type=['csv', 'xlsx'])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # Standardize ALL column names to lowercase and remove spaces for internal logic
    df.columns = [c.strip() for c in df.columns]
    mapping = {c.lower(): c for c in df.columns}
    
    # Helper to find columns even with slight naming differences
    def find_col(possible_names):
        for p in possible_names:
            if p.lower() in mapping:
                return mapping[p.lower()]
        return None

    # Identify key columns
    name_key = find_col(['Opportunity Name', 'Opp Name', 'Name'])
    desc_key = find_col(['Opportunity Description', 'Description', 'Opp Description'])
    age_key = find_col(['Proposal age', 'Proposal Age', 'Age'])

    if st.button("Run Final Logic Calibration"):
        
        def calculate_status(row):
            name = str(row.get(name_key, '')).strip().lower()
            raw_desc = row.get(desc_key, '')
            desc = str(raw_desc).strip().upper() if pd.notna(raw_desc) else ""
            prop_age = str(row.get(age_key, '')).strip()
            
            # 1. PRIORITY: HOLD
            if "hold" in name:
                return "On Hold"
            
            # 2. PRIORITY: PROPOSAL AGE (0-6 Months is ALWAYS Active)
            if prop_age in ["0-3 Months", "3-6 Months"]:
                return "Active"
            
            # 3. DATE EXTRACTION LOGIC
            # Regex for 25/26/2025/2026 or specific months attached to 25/26
            future_patterns = r'(25|26|2025|2026|OCT25|JULY 25|JAN 26|MAY 25|JUNE 25|JUL 25|JUN 25)'
            is_future = bool(re.search(future_patterns, desc))

            # 4. DECISION TREE
            if is_future:
                return "Active"
            
            if "2024" in desc or "2023" in desc:
                return "Direct Update Needed" if "direct" in name else "CRO Update Needed"
            
            if desc == "" or desc == "NAN":
                return "Direct Update Needed" if "direct" in name else "CRO Update Needed"

            return "Direct Update Needed" if "direct" in name else "CRO Update Needed"

        # Run Logic
        df['Status'] = df.apply(calculate_status, axis=1)

        # 5. HIGHLIGHTING FEATURE (For the UI only)
        def bold_dates(text):
            if not isinstance(text, str): return text
            # Highlight 25, 26, 2025, 2026
            pattern = r'(\b25\b|\b26\b|2025|2026|OCT25|JULY 25|JAN 26|MAY 25|JUNE 25)'
            return re.sub(pattern, r'**\1**', text, flags=re.IGNORECASE)

        df_display = df.copy()
        df_display['Highlighted Description'] = df_display[desc_key].apply(bold_dates)

        # --- SUMMARY ---
        counts = df['Status'].value_counts()
        st.subheader("Final Calibrated Results")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Active", counts.get("Active", 0))
        c2.metric("On Hold", counts.get("On Hold", 0))
        c3.metric("Direct Update", counts.get("Direct Update Needed", 0))
        c4.metric("CRO Update", counts.get("CRO Update Needed", 0))

        # --- DOWNLOAD ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Cleaned Pipeline')
        
        st.download_button("📥 Download Final Excel", output.getvalue(), "Final_Pipeline.xlsx")
        
        # Displaying with bolded dates
        st.subheader("Review Logic (Bolding found dates)")
        st.dataframe(
            df_display[[name_key, age_key, 'Status', 'Highlighted Description']].head(100),
            use_container_width=True
        )