import os
import streamlit as st
from supabase import create_client, Client

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Carrier CHK Dashboard", layout="wide")

# --- RETRIEVE SECRETS / TOKENS ---
# Retrieve Supabase credentials
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

# Retrieve Carrier API Token
CARRIER_API_TOKEN = st.secrets.get("CARRIER_API_TOKEN") or os.getenv("CARRIER_API_TOKEN")

# Initialize Supabase client
@st.cache_resource
def init_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("Missing Supabase credentials in Secrets/Environment variables.")
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()

# --- SIDEBAR STATUS ---
st.sidebar.title("Logged In As:")
st.sidebar.write("👤 **tony**")

if st.sidebar.button("Log Out"):
    st.session_state.clear()
    st.rerun()

# Display API Token Status Indicator
if CARRIER_API_TOKEN:
    st.sidebar.success("✅ API Token Loaded")
else:
    st.sidebar.error("⚠️ Missing API Token")

# --- MAIN DASHBOARD ---
st.title("Carrier CHK Data Harvester")

# Fetch records from Supabase
@st.cache_data(ttl=5)
def fetch_harvested_records():
    response = supabase.table("carriers").select("*").execute()
    return response.data

try:
    records = fetch_harvested_records()
except Exception as e:
    st.error(f"Failed to fetch data from Supabase: {e}")
    records = []

# Filtering Controls
col1, col2, col3, col4 = st.columns(4)
with col1:
    search_query = st.text_input("🔍 Search Name / MC:")
with col2:
    entity_filter = st.selectbox("🚛 Filter Entity Type:", ["ALL", "CARRIER", "BROKER"])
with col3:
    status_filter = st.selectbox("📌 Filter Status:", ["ALL", "ACTIVE", "INACTIVE"])
with col4:
    state_filter = st.selectbox("📍 Filter State:", ["ALL"])

st.write(f"Showing **{len(records)}** of **{len(records)}** total harvested records.")

# Data Display Tabs
tab1, tab2, tab3 = st.tabs(["📄 Complete Master Log", "🎯 Verified Leads (Active Only)", "✉️ Raw Active Email"])

with tab1:
    if records:
        # Displaying data with updated width parameter (fixing deprecation warning)
        st.dataframe(records, width="stretch")
    else:
        st.info("No records found in the database.")

# Export Action
if records:
    import pandas as pd
    df = pd.DataFrame(records)
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Master Sheet to CSV",
        data=csv_data,
        file_name="carrier_master_log.csv",
        mime="text/csv",
        width="stretch"
    )
