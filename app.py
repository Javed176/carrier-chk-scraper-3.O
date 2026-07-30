import os
import time
import requests
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# ==========================================
# 1. PAGE CONFIGURATION & SECRETS RETRIEVAL
# ==========================================
st.set_page_config(page_title="Carrier CHK Data Harvester", layout="wide")

# Fetch credentials directly from Streamlit Secrets or Environment Variables
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
CARRIER_API_TOKEN = st.secrets.get("CARRIER_API_TOKEN") or os.getenv("CARRIER_API_TOKEN")

# Initialize Supabase client
@st.cache_resource
def init_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("⚠️ Missing SUPABASE_URL or SUPABASE_KEY in Streamlit Secrets.")
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()


# ==========================================
# 2. BACKGROUND WORKER LOGIC (SCRAPER)
# ==========================================
def fetch_and_update_carrier(mc_number: str, record_id: str):
    """Fetches carrier data from the external API and updates Supabase."""
    if not CARRIER_API_TOKEN:
        st.error("Cannot scrape: CARRIER_API_TOKEN is missing in Secrets.")
        return

    url = f"https://api.carrierchk.com/v1/carrier/{mc_number}"  # Adjust endpoint as needed
    headers = {
        "Authorization": f"Bearer {CARRIER_API_TOKEN}",
        "Content-Type": "application/json"
    }

    max_retries = 3
    delay = 2  # Base delay in seconds for exponential backoff

    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # Update Supabase on success
                supabase.table("carriers").update({
                    "carrier_name": data.get("name", "N/A"),
                    "entity_type": data.get("entity_type", "N/A"),
                    "operating_status": data.get("operating_status", "ACTIVE"),
                    "status": "COMPLETED"
                }).eq("id", record_id).execute()
                st.toast(f"✅ Successfully harvested MC-{mc_number}")
                return

            elif response.status_code == 429:
                # Rate limited -> Exponential backoff pause
                time.sleep(delay)
                delay *= 2

            else:
                supabase.table("carriers").update({
                    "carrier_name": f"ERROR ({response.status_code})",
                    "status": f"FAILED_{response.status_code}"
                }).eq("id", record_id).execute()
                return

        except Exception as e:
            time.sleep(delay)

    # If all retries failed due to 429 throttling
    supabase.table("carriers").update({
        "carrier_name": "⚠️ API THROTTLED (Retrying)",
        "status": "THROTTLED"
    }).eq("id", record_id).execute()


# ==========================================
# 3. SIDEBAR NAVIGATION & STATUS BADGES
# ==========================================
st.sidebar.title("Logged In As:")
st.sidebar.write("👤 **tony**")

if st.sidebar.button("Log Out"):
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown("---")

# Dynamic status badge for API Token
if CARRIER_API_TOKEN:
    st.sidebar.success("✅ API Token Loaded")
else:
    st.sidebar.error("⚠️ Missing API Token")

# Manual Trigger for Scraping Batch
st.sidebar.subheader("Worker Controls")
if st.sidebar.button("🚀 Run Scraper Batch"):
    # Fetch pending queue
    pending_resp = supabase.table("carriers").select("*").eq("status", "PENDING").execute()
    pending_records = pending_resp.data

    if not pending_records:
        st.sidebar.info("No pending MC numbers to scrape.")
    else:
        progress_bar = st.sidebar.progress(0)
        for i, item in enumerate(pending_records):
            fetch_and_update_carrier(item["mc_number"], item["id"])
            progress_bar.progress((i + 1) / len(pending_records))
            time.sleep(1.5)  # 1.5s delay to strictly avoid rate limits
        st.sidebar.success("Batch processing completed!")
        st.rerun()


# ==========================================
# 4. MAIN DASHBOARD UI & DATA DISPLAY
# ==========================================
st.title("Carrier CHK Data Harvester")

# Fetch all records from Supabase
@st.cache_data(ttl=5)
def fetch_master_log():
    try:
        response = supabase.table("carriers").select("*").execute()
        return response.data
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return []

records = fetch_master_log()

# Filtering Bar
col1, col2, col3, col4 = st.columns(4)
with col1:
    search_query = st.text_input("🔍 Search Name / MC:", "")
with col2:
    entity_filter = st.selectbox("🚛 Filter Entity Type:", ["ALL", "CARRIER", "BROKER"])
with col3:
    status_filter = st.selectbox("📌 Filter Status:", ["ALL", "ACTIVE", "INACTIVE", "THROTTLED"])
with col4:
    state_filter = st.selectbox("📍 Filter State:", ["ALL"])

# Apply UI filters
filtered_records = records
if search_query:
    filtered_records = [
        r for r in filtered_records 
        if search_query.lower() in str(r.get("mc_number", "")).lower() 
        or search_query.lower() in str(r.get("carrier_name", "")).lower()
    ]

st.write(f"Showing **{len(filtered_records)}** of **{len(records)}** total harvested records.")

# Dashboard Tabs
tab1, tab2, tab3 = st.tabs(["📄 Complete Master Log", "🎯 Verified Leads (Active Only)", "✉️ Raw Active Email"])

with tab1:
    if filtered_records:
        # Fixed deprecation warning by using width="stretch"
        st.dataframe(filtered_records, width="stretch")
    else:
        st.info("No records available.")

with tab2:
    active_leads = [r for r in filtered_records if r.get("operating_status") == "ACTIVE"]
    if active_leads:
        st.dataframe(active_leads, width="stretch")
    else:
        st.info("No active leads found.")

with tab3:
    emails = [r for r in filtered_records if r.get("email")]
    if emails:
        st.dataframe(emails, width="stretch")
    else:
        st.info("No active emails available.")

# Export to CSV Section
if filtered_records:
    df = pd.DataFrame(filtered_records)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Export Master Sheet to CSV",
        data=csv,
        file_name="carrier_master_log.csv",
        mime="text/csv",
        width="stretch"
    )
