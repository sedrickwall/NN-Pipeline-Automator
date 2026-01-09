import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re

st.set_page_config(page_title="Pipeline Automator", layout="wide")

st.title("🚀 Pipeline Status Automator (Final Calibration)")

# --- 1. SETTINGS ---
st.sidebar.header("Configuration")
anchor_date = st.sidebar.date_input("Select Anchor Date", datetime(2026, 1, 9))

# --- 2. FILE UPLOADER ---
uploaded_file = st.file_uploader("Upload Salesforce Export", type=['csv', 'xlsx'])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    df.columns = [c.strip() for c in df.columns]

    if st.button("Run Final Logic Calibration"):
        
        def calculate_status(row):
            name = str(row.get('Opportunity Name', '')).strip().lower()
            raw_desc = row.get('Opportunity Description', '')
            desc = str(raw_desc).strip().upper() if pd.notna(raw_desc) else ""
            prop_age = str(row.get('Proposal age', '')).strip()
            
            # 1. PRIORITY: HOLD
            if "hold" in name:
                return "On Hold"
            
            # 2. PRIORITY: PROPOSAL AGE (0-6 Months is ALWAYS Active)
            # This handles the blank rows you showed that are 3-6 Months
            if prop_age in ["0-3 Months", "3-6 Months"]:
                return "Active"
            
            # 3. DATE EXTRACTION LOGIC
            # We look for any mention of 25 or 26 in various formats (July 25, OCT25, /25, 2025)
            # We also check for 'Jan 26' or '2026'
            future_date_patterns = [
                r'25', r'26', r'2025', r'2026', r'OCT25', r'JULY 25', r'JAN 26', r'MAY 25', r'JUNE 25'
            ]
            
            # Check if any future date exists in the description
            # We use regex to find '25' or '26' as whole words or attached to months
            is_future = False
            if desc:
                # This regex looks for 25 or 26 that aren't part of a larger number like 125
                if re.search(r'(?:\b|/)(25|26|2025|2026)\b', desc) or any(m in desc for m in ['OCT25', 'OCT 25', 'JULY 25', 'JUL 25', 'JAN 26', 'JUN 25']):
                    is_future = True

            # 4. DECISION TREE
            if is_future:
                # Even if it says 2024, if it also says 2025/2026, it is ACTIVE
                return "Active"
            
            # If description mentions 2024 but NO 2025/26
            if "2024" in desc or "2023" in desc:
                return "Direct Update Needed" if "direct" in name else "CRO Update Needed"
            
            # If description is totally blank and not a new proposal
            if desc == "" or desc == "NAN":
                return "Direct Update Needed" if "direct" in name else "CRO Update Needed"

            # Fallback
            return "Direct Update Needed" if "direct" in name else "CRO Update Needed"

        # Run Logic
        df['Status'] = df.apply(calculate_status, axis=1)

        # --- 3. DISPLAY RESULTS ---
        counts = df['Status'].value_counts()
        st.subheader("Final Calibrated Results")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Active", counts.get("Active", 0))
        c2.metric("On Hold", counts.get("On Hold", 0))
        c3.metric("Direct Update", counts.get("Direct Update Needed", 0))
        c4.metric("CRO Update", counts.get("CRO Update Needed", 0))

        # --- 4. DOWNLOAD ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Cleaned Pipeline')
        st.download_button("📥 Download Final Excel", output.getvalue(), "Final_Calibrated_Pipeline.xlsx")
        
        st.dataframe(df[['Opportunity Name', 'Proposal age', 'Status', 'Opportunity Description']].head(100))