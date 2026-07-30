import os
import re
import time
import requests
from bs4 import BeautifulSoup
import streamlit as st
from supabase import create_client, Client

# ==============================================================================
# 1. SETUP, CONFIGURATION & SUPABASE BACKEND
# ==============================================================================
st.set_page_config(
    page_title="Carrier Harvester & Lead Engine",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Glassmorphism CSS Theme
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
    }
    .stMetric {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 10px;
        backdrop-filter: blur(10px);
    }
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# Supabase Client Initialization
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

@st.cache_resource
def get_supabase_client() -> Client:
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            return create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            st.error(f"Supabase connection error: {e}")
    return None

supabase = get_supabase_client()

# Session State Initialization - AUTH BYPASSED DIRECTLY HERE
if "authenticated" not in st.session_state:
    st.session_state.authenticated = True  # Automatically set to True
if "user_role" not in st.session_state:
    st.session_state.user_role = "super_admin"  # Automatically set as Admin
if "harvesting" not in st.session_state:
    st.session_state.harvesting = False
if "harvested_records" not in st.session_state:
    st.session_state.harvested_records = []
if "current_mc" not in st.session_state:
    st.session_state.current_mc = 1006435

# ==============================================================================
# 2. DIRECT FMCSA SAFER SCRAPING ENGINE
# ==============================================================================
def fetch_safer_carrier_data(mc_number: str) -> dict:
    """
    Directly queries FMCSA SAFER via HTML parsing using BeautifulSoup.
    """
    url = "https://safer.fmcsa.dot.gov/query.asp"
    payload = {
        "searchtype": "ANY",
        "query_type": "queryCarrierDetail",
        "query_param": "MC_MX",
        "query_string": str(mc_number)
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        response = requests.post(url, data=payload, headers=headers, timeout=12)
        if response.status_code != 200:
            return {"error": f"SAFER returned status code {response.status_code}"}

        soup = BeautifulSoup(response.text, "html.parser")
        raw_text = soup.get_text()

        if "Record Inactive" in raw_text or "No records matching" in raw_text:
            return {
                "MC Number": mc_number,
                "Legal Name": "NOT FOUND / INACTIVE",
                "DBA Name": "",
                "Entity Type": "UNKNOWN",
                "USDOT Status": "INACTIVE",
                "Operating Status": "INACTIVE",
                "Classification": "UNKNOWN",
                "Emails": []
            }

        # Data extraction dict matching prior schema
        data = {
            "MC Number": mc_number,
            "Legal Name": "",
            "DBA Name": "",
            "Entity Type": "UNKNOWN",
            "USDOT Status": "UNKNOWN",
            "Operating Status": "UNKNOWN",
            "Classification": "UNKNOWN",
            "Emails": []
        }

        # Table Parsing for core SAFER fields
        for row in soup.find_all("tr"):
            row_text = row.get_text()
            cols = row.find_all("td")
            
            if "Legal Name:" in row_text and len(cols) > 1:
                data["Legal Name"] = cols[1].get_text(strip=True)
            elif "DBA Name:" in row_text and len(cols) > 1:
                data["DBA Name"] = cols[1].get_text(strip=True)
            elif "Entity Type:" in row_text and len(cols) > 1:
                data["Entity Type"] = cols[1].get_text(strip=True).upper()
            elif "Operating Status:" in row_text and len(cols) > 1:
                data["Operating Status"] = cols[1].get_text(strip=True).upper()
            elif "USDOT Status:" in row_text and len(cols) > 1:
                data["USDOT Status"] = cols[1].get_text(strip=True).upper()

        # Classification rules (Carrier vs Broker vs 3PL)
        entity = data["Entity Type"]
        if "CARRIER" in entity:
            data["Classification"] = "CARRIER"
        elif "BROKER" in entity or any(k in raw_text.upper() for k in ["3PL", "FREIGHT FORWARDER", "COYOTE", "TQL"]):
            data["Classification"] = "BROKER"
        else:
            data["Classification"] = "OTHER"

        # Regex email extraction from page text
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', response.text)
        data["Emails"] = list(set(emails))

        return data

    except Exception as e:
        return {"error": f"Scraping exception: {str(e)}"}

# ==============================================================================
# 3. SIDEBAR CONTROLS
# ==============================================================================
st.sidebar.title("🎛️ Control Panel")
st.sidebar.write(f"**User Role:** `{st.session_state.user_role}`")

delay_ms = st.sidebar.slider("Harvesting Delay (ms)", min_value=100, max_value=3000, value=500, step=100)
start_mc_input = st.sidebar.number_input("Target MC Number", value=st.session_state.current_mc, step=1)

col_h1, col_h2 = st.sidebar.columns(2)
if col_h1.button("Start Harvester"):
    st.session_state.harvesting = True
    st.session_state.current_mc = start_mc_input

if col_h2.button("Stop"):
    st.session_state.harvesting = False

# ==============================================================================
# 4. CONTINUOUS HARVESTING ENGINE (LOOP)
# ==============================================================================
st.title("🚚 SAFER Carrier Data Scraper")

if st.session_state.harvesting:
    st.markdown("""
        <div style="padding:10px; background-color:rgba(16, 185, 129, 0.2); border:1px solid #10b981; border-radius:8px; margin-bottom:15px;">
            ⚡ <b>Live Continuous Harvesting Active</b> — Processing MC: <code>{}</code>
        </div>
    """.format(st.session_state.current_mc), unsafe_allow_html=True)

    result = fetch_safer_carrier_data(str(st.session_state.current_mc))

    if "error" not in result:
        st.session_state.harvested_records.append(result)
        
        # Save to Supabase table if database connection is active
        if supabase:
            try:
                supabase.table("carrier_leads").insert(result).execute()
            except Exception:
                pass

    st.session_state.current_mc += 1
    time.sleep(delay_ms / 1000.0)
    st.rerun()

# ==============================================================================
# 5. SINGLE LOOKUP FORM & ANALYTICS DASHBOARD
# ==============================================================================
st.markdown("### 🔎 Single Carrier Lookup")
with st.form("single_lookup"):
    c1, c2 = st.columns([1, 3])
    search_by = c1.selectbox("Search By", ["MC_MX", "USDOT"])
    mc_query = c2.text_input("Enter Number", value=str(st.session_state.current_mc))
    lookup_submit = st.form_submit_button("Search Carrier")

if lookup_submit:
    with st.spinner("Scraping SAFER..."):
        single_res = fetch_safer_carrier_data(mc_query)
        if "error" in single_res:
            st.error(single_res["error"])
        else:
            st.success("Carrier Found!")
            st.json(single_res)

# Multi-Tab Analytics Display
st.markdown("---")
tab1, tab2, tab3 = st.tabs(["📋 Master Log", "✅ Verified Active Leads", "📧 Extracted Emails"])

with tab1:
    st.subheader("All Extracted Records")
    st.dataframe(st.session_state.harvested_records, use_container_width=True)

with tab2:
    st.subheader("Authorized & Active Entities")
    filtered = [r for r in st.session_state.harvested_records if "AUTHORIZED" in r.get("Operating Status", "") or r.get("Classification") == "CARRIER"]
    st.dataframe(filtered, use_container_width=True)

with tab3:
    st.subheader("Harvested Email Contacts")
    extracted_emails = []
    for r in st.session_state.harvested_records:
        extracted_emails.extend(r.get("Emails", []))
    st.write(list(set(extracted_emails)))
