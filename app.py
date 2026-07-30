import os
import re
import time
import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from supabase import create_client, Client

# ==========================================
# 1. PAGE CONFIGURATION & SECRETS RETRIEVAL
# ==========================================
st.set_page_config(page_title="Carrier CHK Data Harvester", layout="wide")

SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

@st.cache_resource
def init_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("⚠️ Missing SUPABASE_URL or SUPABASE_KEY in Streamlit Secrets.")
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()


# ==========================================
# 2. FMCSA SAFER SCRAPER LOGIC (NO TOKEN)
# ==========================================
def scrape_safer_and_update(mc_number: str, record_id: str):
    """Scrapes FMCSA SAFER directly without any API key and updates Supabase."""
    url = "https://safer.fmcsa.dot.gov/query.asp"
    
    payload = {
        "searchtype": "ANY",
        "query_type": "queryCarrierSnapshot",
        "query_param": "MC_MX",
        "query_string": str(mc_number).strip()
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://safer.fmcsa.dot.gov/CompanySnapshot.aspx"
    }

    try:
        response = requests.post(url, data=payload, headers=headers, timeout=15)
        
        if response.status_code != 200:
            supabase.table("carriers").update({
                "carrier_name": f"HTTP {response.status_code} Error",
                "status": f"FAILED_{response.status_code}"
            }).eq("id", record_id).execute()
            return

        if "No record found" in response.text or "Record Not Found" in response.text:
            supabase.table("carriers").update({
                "carrier_name": "NOT FOUND",
                "status": "NOT_FOUND"
            }).eq("id", record_id).execute()
            return

        soup = BeautifulSoup(response.text, "html.parser")

        def get_val(label_text):
            tag = soup.find(lambda t: t.name in ['td', 'th'] and label_text in t.text)
            if tag and tag.find_next_sibling('td'):
                raw = tag.find_next_sibling('td').get_text(separator=" ", strip=True)
                return re.sub(r'\s+', ' ', raw)
            return "N/A"

        legal_name = get_val("Legal Name:")
        entity_type = get_val("Entity Type:")
        operating_status = get_val("Operating Status:")

        # Update Supabase database
        supabase.table("carriers").update({
            "carrier_name": legal_name,
            "entity_type": entity_type,
            "operating_status": operating_status,
            "status": "COMPLETED"
        }).eq("id", record_id).execute()

    except Exception as e:
        supabase.table("carriers").update({
            "carrier_name": "SCRAPE ERROR",
            "status": "FAILED"
        }).eq("id", record_id).execute()


# ==========================================
# 3. SIDEBAR NAVIGATION & SCRAPER CONTROLS
# ==========================================
st.sidebar.title("Logged In As:")
st.sidebar.write("👤 **tony**")

if st.sidebar.button("Log Out"):
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("FMCSA Scraper Controls")

if st.sidebar.button("🚀 Scrape Pending MC Numbers"):
    # Pull pending queue from Supabase
    pending_resp = supabase.table("carriers").select("*").eq("status", "PENDING").execute()
    pending_records = pending_resp.data

    if not pending_records:
        st.sidebar.info("No pending MC numbers found.")
    else:
        progress_bar = st.sidebar.progress(0)
        for i, item in enumerate(pending_records):
            scrape_safer_and_update(item["mc_number"], item["id"])
            progress_bar.progress((i + 1) / len(pending_records))
            time.sleep(2)  # 2s delay prevents FMCSA rate limiting
        st.sidebar.success("Finished scraping pending items!")
        st.rerun()


# ==========================================
# 4. MAIN DASHBOARD UI & DATA DISPLAY
# ==========================================
st.title("Carrier CHK Data Harvester")

@st.cache_data(ttl=5)
def fetch_master_log():
    try:
        response = supabase.table("carriers").select("*").execute()
        return response.data
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return []

records = fetch_master_log()

# Filtering Controls
col1, col2, col3, col4 = st.columns(4)
with col1:
    search_query = st.text_input("🔍 Search Name / MC:", "")
with col2:
    entity_filter = st.selectbox("🚛 Filter Entity Type:", ["ALL", "CARRIER", "BROKER"])
with col3:
    status_filter = st.selectbox("📌 Filter Status:", ["ALL", "ACTIVE", "INACTIVE"])
with col4:
    state_filter = st.selectbox("📍 Filter State:", ["ALL"])

filtered_records = records
if search_query:
    filtered_records = [
        r for r in filtered_records 
        if search_query.lower() in str(r.get("mc_number", "")).lower() 
        or search_query.lower() in str(r.get("carrier_name", "")).lower()
    ]

st.write(f"Showing **{len(filtered_records)}** of **{len(records)}** total harvested records.")

# UI Tabs
tab1, tab2, tab3 = st.tabs(["📄 Complete Master Log", "🎯 Verified Leads (Active Only)", "✉️ Raw Active Email"])

with tab1:
    if filtered_records:
        st.dataframe(filtered_records, width="stretch")
    else:
        st.info("No records available.")

with tab2:
    active_leads = [r for r in filtered_records if "AUTHORIZED" in str(r.get("operating_status", "")).upper()]
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

# Export Section
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
