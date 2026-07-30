import streamlit as st
import pandas as pd

# Page setup
st.set_page_config(
    page_title="Control Panel",
    page_icon="⚙️",
    layout="wide"
)

# Sidebar
with st.sidebar:
    st.title("⚙️ Control Panel")
    st.markdown("**User Role:** `:green[user]`")
    
    harvesting_delay = st.slider(
        "Harvesting Delay (ms)",
        min_value=100,
        max_value=3000,
        value=800,
        step=100
    )
    
    target_mc = st.number_input("Target MC Number", value=1006438, step=1)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start Harvester", type="primary", use_container_width=True):
            st.session_state["harvesting"] = True
    with col2:
        if st.button("Stop", use_container_width=True):
            st.session_state["harvesting"] = False

# Main Area
if st.session_state.get("harvesting", False):
    st.info("🔄 Harvester is active and processing requests...")

tab1, tab2, tab3 = st.tabs(["📑 Master Log", "✅ Verified Active Leads", "📧 Extracted Emails"])

with tab1:
    st.subheader("All Extracted Records")
    
    sample_data = pd.DataFrame([
        {"MC Number": "1006435", "Legal Name": "NOT FOUND / INACTIVE", "DBA Name": "", "Entity Type": "UNKNOWN", "USDOT Status": "INACTIVE"},
        {"MC Number": "1006436", "Legal Name": "NOT FOUND / INACTIVE", "DBA Name": "", "Entity Type": "UNKNOWN", "USDOT Status": "INACTIVE"},
        {"MC Number": "1006437", "Legal Name": "NOT FOUND / INACTIVE", "DBA Name": "", "Entity Type": "UNKNOWN", "USDOT Status": "INACTIVE"}
    ])
    
    st.dataframe(sample_data, use_container_width=True, hide_index=True)
