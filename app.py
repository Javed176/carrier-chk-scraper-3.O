import streamlit as st
import pandas as pd
import time

st.set_page_config(
    page_title="Carrier Extraction Control Panel",
    page_icon="⚙️",
    layout="wide"
)

# Initialize background state
if "is_harvesting" not in st.session_state:
    st.session_state.is_harvesting = False

# --- Sidebar Configuration ---
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
            st.session_state.is_harvesting = True
            st.toast("Harvester Started")
    with col2:
        if st.button("Stop", use_container_width=True):
            st.session_state.is_harvesting = False
            st.toast("Harvester Stopped")

# --- Main Dashboard ---
st.title("Carrier Extraction Dashboard")

# Search Bar
search_col1, search_col2 = st.columns([3, 1])
with search_col1:
    search_query = st.text_input("Search Carrier", placeholder="Enter MC Number or Name...", label_visibility="collapsed")
with search_col2:
    st.button("Search Carrier", use_container_width=True)

st.write("---")

# Display Status Indicator
if st.session_state.is_harvesting:
    st.info("🔄 Harvester is active and processing requests...")
else:
    st.warning("⏸️ Harvester is idle.")

# Tabs
tab1, tab2, tab3 = st.tabs(["📑 Master Log", "✅ Verified Active Leads", "📧 Extracted Emails"])

with tab1:
    st.subheader("All Extracted Records")
    
    sample_data = pd.DataFrame([
        {"MC Number": "1006435", "Legal Name": "NOT FOUND / INACTIVE", "DBA Name": "", "Entity Type": "UNKNOWN", "USDOT Status": "INACTIVE"},
        {"MC Number": "1006436", "Legal Name": "NOT FOUND / INACTIVE", "DBA Name": "", "Entity Type": "UNKNOWN", "USDOT Status": "INACTIVE"},
        {"MC Number": "1006437", "Legal Name": "NOT FOUND / INACTIVE", "DBA Name": "", "Entity Type": "UNKNOWN", "USDOT Status": "INACTIVE"}
    ])
    
    st.dataframe(sample_data, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Verified Active Leads")

with tab3:
    st.subheader("Extracted Emails")
