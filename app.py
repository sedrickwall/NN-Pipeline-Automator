import streamlit as st
import pandas as pd
from datetime import datetime
import io

st.set_page_config(page_title="Pipeline Automator", layout="wide")

st.title("🚀 Pipeline Status Automator (Refined)")

# --- 1. SETTINGS ---
st.sidebar.header("Configuration")
anchor_date = st.sidebar.date_input("Select Anchor Date", datetime(2026, 1, 9))

# --- 2. FILE UPLOADER ---
uploaded_file = st.file_uploader("Upload Salesforce Export", type=['csv', 'xlsx'])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    df.columns = [c.strip() for c in df.columns]

    if st.button("Generate Cleaned Pipeline"):
        
        def calculate_status(row):
            name = str(row.get('Opportunity Name', '')).strip().lower()
            desc = str(row.get('Opportunity Description', '')).strip().lower()
            prop_age = str(row.get('Proposal age', '')).strip()
            
            # 1. PRIORITY: HOLD
            if "hold" in name:
                return "On Hold"
            
            # 2. PRIORITY: NEW PROPOSALS
            if prop_age in ["0-3 Months", "3-6 Months"]:
                return "Active"
            
            # 3. DATE SEARCH (Active if 2025/26 or shorthand 25/26 is found)
            # We look for '25', '26', '/25', '/26' but avoid '2024'
            active_keywords = ['2025', '2026', '/25', '/26', 'July 25', 'Aug 25', 'Sept 25', 'Oct 25', 'Nov 25', 'Dec 25']
            is_active = any(key.lower() in desc for key in active_keywords)
            
            if is_active and "2024" not in desc:
                return "Active"
            
            # Special case: If it has 2024 and 2025, the future date wins
            if "2025" in desc or "2026" in desc:
                return "Active"

            # 4. FALLBACK: UPDATE NEEDED
            if "direct" in name:
                return "Direct Update Needed"
            else:
                return "CRO Update Needed"

        # Run Logic
        df['Status'] = df.apply(calculate_status, axis=1)

        # --- 3. SUMMARY DASHBOARD ---
        st.subheader("Analysis Results")
        counts = df['Status'].value_counts()
        
        # Displaying your targets for comparison
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Active", counts.get("Active", 0), delta=f"Target: 207")
        c2.metric("On Hold", counts.get("On Hold", 0), delta=f"Target: 41")
        c3.metric("Direct Update", counts.get("Direct Update Needed", 0), delta=f"Target: 36")
        c4.metric("CRO Update", counts.get("CRO Update Needed", 0), delta=f"Target: 27")

        # --- 4. EXPORT ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Cleaned Pipeline')
        
        st.download_button("📥 Download Excel", output.getvalue(), "Final_Pipeline.xlsx")
        st.dataframe(df[['Opportunity Name', 'Status', 'Opportunity Description']].head(50))