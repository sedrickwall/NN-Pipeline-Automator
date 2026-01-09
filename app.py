import streamlit as st
import pandas as pd
from datetime import datetime
import io

# ... (Region mapping code from previous version remains the same) ...

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # Standardizing column names to handle Salesforce variations
    df.columns = [c.strip() for c in df.columns]

    if st.button("Generate Cleaned Pipeline"):
        
        def calculate_status(row):
            # Get values safely
            name = str(row.get('Opportunity Name', '')).strip()
            desc = str(row.get('Opportunity Description', '')).strip().lower()
            prop_age = str(row.get('Proposal age', '')).strip()
            
            # 1. HOLD CHECK (Case insensitive)
            if "hold" in name.lower():
                return "On Hold"
            
            # 2. PROPOSAL AGE BYPASS (0-6 months = Active)
            if prop_age in ["0-3 Months", "3-6 Months"]:
                return "Active"
            
            # 3. DESCRIPTION DATE LOGIC
            # If blank or contains 2024, it's not active
            if desc == "" or desc == "nan" or "2024" in desc:
                # Determine if Direct or CRO
                return "Direct Update Needed" if "direct" in name.lower() else "CRO Update Needed"
            
            # If it contains a future year within 1 yr of 2026
            if "2025" in desc or "2026" in desc:
                return "Active"
            
            # 4. FALLBACK (If no date found at all)
            return "Direct Update Needed" if "direct" in name.lower() else "CRO Update Needed"

        # Apply the new logic
        df['Status'] = df.apply(calculate_status, axis=1)
        
        # ... (Rest of the Region Mapping code) ...

        # --- RESULTS ---
        st.subheader("Final Status Count")
        st.write(df['Status'].value_counts())
        
        # Highlight the specific 'On Hold' count for verification
        hold_count = len(df[df['Status'] == "On Hold"])
        st.info(f"Verified: {hold_count} items identified as 'On Hold'")

        # Export to Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Cleaned Pipeline')
        st.download_button("📥 Download Excel", output.getvalue(), "Cleaned_Pipeline.xlsx")