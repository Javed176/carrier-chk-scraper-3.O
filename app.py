import streamlit as st
import pandas as pd
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="Carrier Extraction Control Panel",
    page_icon="⚙️",
    layout="wide"
)

# --- Sidebar Configuration ---
with st.sidebar:
    st.title("⚙️ Control Panel")
    
    # User role badge
    st.markdown("**User Role:** `:green[user]`")
    
    # Harvesting Delay Slider
    harvesting_delay = st.slider(
        "Harvesting Delay (ms)",
        min_value=100,
        max_value=3000,
        value=800,
        step=100,
        help="Delay between requests to avoid rate limits."
    )
    
    # Target MC Number Input
    target_mc = st.number_input(
        "Target MC Number",
        value=1006438,
        step=1
    )
    
    col1, col2 = st.columns(2)
    with col1:
        # Updated: 'width="stretch"' replaces 'use_container_width=True'
        if st.button("Start Harvester", type="primary", width="stretch"):
            st.session_state["harvesting"] = True
            st.success("Harvester Started")
    with col2:
        # Updated: 'width="stretch"' replaces 'use_container_width=True'
        if st.button("Stop", width="stretch"):
            st.session_state["harvesting"] = False
            st.warning("Harvester Stopped")

# --- Main Dashboard ---
st.title("Carrier Extraction Dashboard")

# Search Bar Area
search_col1, search_col2 = st.columns([3, 1])
with search_col1:
    search_query = st.text_input("Search Carrier", placeholder="Enter MC Number or Name...", label_visibility="collapsed")
with search_col2:
    # Updated: width="stretch"
    st.button("Search Carrier", width="stretch")

st.write("---")

# Navigation Tabs
tab1, tab2, tab3 = st.tabs(["📑 Master Log", "✅ Verified Active Leads", "📧 Extracted Emails"])

with tab1:
    st.subheader("All Extracted Records")
    
    # Sample dataframe reflecting your current extracted state
    sample_data = pd.DataFrame([
        {"MC Number": "1006435", "Legal Name": "NOT FOUND / INACTIVE", "DBA Name": "", "Entity Type": "UNKNOWN", "USDOT Status": "INACTIVE"},
        {"MC Number": "1006436", "Legal Name": "NOT FOUND / INACTIVE", "DBA Name": "", "Entity Type": "UNKNOWN", "USDOT Status": "INACTIVE"},
        {"MC Number": "1006437", "Legal Name": "NOT FOUND / INACTIVE", "DBA Name": "", "Entity Type": "UNKNOWN", "USDOT Status": "INACTIVE"}
    ])
    
    # Updated: width="stretch" fixes the dataframe width deprecation warning
    st.dataframe(
        sample_data,
        width="stretch",
        hide_index=True
    )

with tab2:
    st.subheader("Verified Active Leads")
    st.info("No active leads extracted yet. Increase delay if scraper is returning inactive records.")

with tab3:
    st.subheader("Extracted Emails")
    st.info("No emails gathered.")
