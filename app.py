import requests
from bs4 import BeautifulSoup
import streamlit as st

st.set_page_config(page_title="SAFER Carrier Scraper", page_icon="🚚")

st.title("🚚 SAFER Carrier Data Scraper")
st.write("Fetch carrier snapshot data directly from the FMCSA SAFER website.")

def scrape_safer(search_type, search_number):
    # Establish a persistent session
    session = requests.Session()
    
    # Headers to mimic a standard desktop browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://safer.fmcsa.dot.gov/CompanySnapshot.aspx",
    }
    session.headers.update(headers)

    try:
        # Step 1: Visit the home page to acquire session cookies and pass initial security checks
        session.get("https://safer.fmcsa.dot.gov/CompanySnapshot.aspx", timeout=10)

        # Step 2: Now send the query request with acquired session cookies
        url = "https://safer.fmcsa.dot.gov/query.asp"
        param_type = "MC_MX" if "MC" in search_type else "USDOT"
        params = {
            "searchtype": "ANY",
            "query_type": "queryCarrierSnapshot",
            "query_param": param_type,
            "query_string": str(search_number).strip(),
        }

        response = session.get(url, params=params, timeout=10)
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        return None, f"Network error: {e}"

    soup = BeautifulSoup(response.text, "html.parser")

    if "Record Inactive" in soup.text:
        return None, "Carrier record is inactive or not found."
    if "No records matching" in soup.text:
        return None, "No record found for the provided number."

    data = {}
    for tr in soup.find_all("tr"):
        text = tr.get_text(strip=True)
        if "Legal Name:" in text:
            tds = tr.find_all("td")
            if tds:
                data["Legal Name"] = tds[-1].get_text(strip=True)
        elif "DBA Name:" in text:
            tds = tr.find_all("td")
            if tds:
                data["DBA Name"] = tds[-1].get_text(strip=True)
        elif "Entity Type:" in text:
            tds = tr.find_all("td")
            if tds:
                data["Entity Type"] = tds[-1].get_text(strip=True)
        elif "USDOT Status:" in text:
            tds = tr.find_all("td")
            if tds:
                data["USDOT Status"] = tds[-1].get_text(strip=True)

    if not data:
        return None, "Connected successfully, but could not parse expected carrier fields."

    return data, None

# --- STREAMLIT UI ---
with st.form("scraper_form"):
    col1, col2 = st.columns([1, 2])
    with col1:
        search_type = st.selectbox("Search By", options=["MC_MX", "USDOT"])
    with col2:
        search_number = st.text_input("Enter Number", value="1066434")
    
    submit_button = st.form_submit_button("Search Carrier")

if submit_button:
    if not search_number.strip():
        st.warning("Please enter a valid number.")
    else:
        with st.spinner("Scraping SAFER..."):
            result, error = scrape_safer(search_type, search_number.strip())

        if error:
            st.error(error)
        else:
            st.success("Carrier Found!")
            st.json(result)
