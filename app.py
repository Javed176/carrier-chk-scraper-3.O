import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import io
from PIL import Image

st.set_page_config(page_title="FMCSA Company Snapshot Scraper", layout="wide")

st.title("🚛 FMCSA Company Snapshot Scraper")
st.markdown("Search by DOT Number or Company Name (MC numbers use public API)")

# Initialize session state safely
if 'captcha_image_bytes' not in st.session_state:
    st.session_state.captcha_image_bytes = None
if 'cookies' not in st.session_state:
    st.session_state.cookies = None
if 'search_data' not in st.session_state:
    st.session_state.search_data = None


def get_fmcsa_session():
    """Initialize session and get initial page"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    })
    
    base_url = "https://safer.fmcsa.dot.gov/CompanySnapshot.aspx"
    response = session.get(base_url, timeout=10)
    time.sleep(random.uniform(0.5, 1.5))
    
    return session, response


def extract_form_fields(html_content):
    """Extract ASP.NET form fields"""
    soup = BeautifulSoup(html_content, 'html.parser')
    fields = {}
    
    for field_id in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']:
        element = soup.find('input', {'id': field_id})
        fields[field_id] = element['value'] if element else ''
    
    return fields, soup


def search_fmcsa(cookies, form_fields, company_name="", dot_number="", captcha_text=""):
    """Perform search using stored cookies instead of serializing session objects"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    })
    session.cookies.update(cookies)
    
    base_url = "https://safer.fmcsa.dot.gov/CompanySnapshot.aspx"
    
    form_data = {
        '__VIEWSTATE': form_fields.get('__VIEWSTATE', ''),
        '__VIEWSTATEGENERATOR': form_fields.get('__VIEWSTATEGENERATOR', ''),
        '__EVENTVALIDATION': form_fields.get('__EVENTVALIDATION', ''),
        'ctl00$MainContent$txtName': company_name,
        'ctl00$MainContent$txtDot': dot_number,
        'ctl00$MainContent$btnSearch': 'Search',
        'ctl00$MainContent$chkAll': 'on',
        'ctl00$MainContent$captchaText': captcha_text,
    }
    
    response = session.post(base_url, data=form_data, timeout=12)
    return response


def parse_results(html_content):
    """Parse search results into DataFrame"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    table = None
    for selector in ['MainContent_gvSearchResult', 'datagrid', 'gridview']:
        table = soup.find('table', {'id': selector})
        if table:
            break
    
    if table:
        try:
            df = pd.read_html(io.StringIO(str(table)))[0]
            return df
        except Exception:
            pass
    
    rows = soup.find_all('tr', class_='gridrow')
    if not rows:
        rows = soup.find_all('tr')
    
    if rows:
        data = []
        for row in rows:
            cols = row.find_all('td')
            if cols:
                data.append([col.get_text(strip=True) for col in cols])
        
        if data:
            return pd.DataFrame(data)
    
    return None


def search_by_mc_number(mc_number):
    """Bypasses CAPTCHA by looking up MC directly via FMCSA REST API"""
    try:
        api_url = f"https://mobile.fmcsa.dot.gov/rest/v1/carrier/docket/{mc_number}"
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        }
        
        response = requests.get(api_url, headers=headers, timeout=8)
        if response.status_code == 200:
            data = response.json()
            if 'content' in data and data['content']:
                return pd.DataFrame([data['content']])
        return None
    except Exception:
        return None


# --- Sidebar ---
with st.sidebar:
    st.header("Search Parameters")
    
    search_type = st.radio("Search by:", ["DOT Number", "Company Name", "MC Number (API)"])
    
    dot_number = ""
    company_name = ""
    mc_number = ""
    
    if search_type == "DOT Number":
        dot_number = st.text_input("Enter DOT Number:", placeholder="123456")
    elif search_type == "Company Name":
        company_name = st.text_input("Enter Company Name:", placeholder="ABC Trucking")
    else:
        mc_number = st.text_input("Enter MC Number:", placeholder="123456")
    
    search_button = st.button("Search", use_container_width=True)

# --- Main Logic ---
if search_button:
    # Clear previous CAPTCHA state on new search
    st.session_state.captcha_image_bytes = None
    st.session_state.search_data = None

    if search_type == "MC Number (API)":
        with st.spinner("Searching FMCSA API by MC number..."):
            clean_mc = mc_number.lower().replace("mc-", "").replace("mc", "").strip()
            results = search_by_mc_number(clean_mc)
            
            if results is not None and not results.empty:
                st.success("✅ Results found!")
                st.dataframe(results, use_container_width=True)
                
                csv = results.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"fmcsa_mc_{clean_mc}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No records found for this MC number.")
    else:
        with st.spinner("Connecting to FMCSA..."):
            try:
                session, response = get_fmcsa_session()
                form_fields, soup = extract_form_fields(response.content)
                
                captcha_img = soup.find('img', {'id': 'MainContent_CaptchaImage'})
                
                if captcha_img and captcha_img.get('src'):
                    captcha_url = f"https://safer.fmcsa.dot.gov/{captcha_img.get('src')}"
                    captcha_resp = session.get(captcha_url, timeout=10)
                    
                    # Store serialized byte data instead of live session/image objects
                    st.session_state.captcha_image_bytes = captcha_resp.content
                    st.session_state.cookies = session.cookies.get_dict()
                    st.session_state.search_data = {
                        'form_fields': form_fields,
                        'company_name': company_name,
                        'dot_number': dot_number
                    }
                    st.warning("⚠️ CAPTCHA detected! Solve it below.")
                else:
                    # Direct search if no CAPTCHA triggered
                    resp = search_fmcsa(session.cookies.get_dict(), form_fields, company_name, dot_number)
                    results = parse_results(resp.content)
                    
                    if results is not None and not results.empty:
                        st.success("✅ Search completed!")
                        st.dataframe(results, use_container_width=True)
                    else:
                        st.error("No results found or search failed.")
            except Exception as e:
                st.error(f"Connection Error: {str(e)}")

# --- CAPTCHA Input Block ---
if st.session_state.captcha_image_bytes is not None:
    st.write("---")
    st.header("🔐 Solve CAPTCHA")
    
    img = Image.open(io.BytesIO(st.session_state.captcha_image_bytes))
    st.image(img, caption="FMCSA Security Verification")
    
    captcha_input = st.text_input("Enter CAPTCHA text:")
    
    if st.button("Submit CAPTCHA", type="primary"):
        with st.spinner("Verifying CAPTCHA..."):
            try:
                data = st.session_state.search_data
                resp = search_fmcsa(
                    st.session_state.cookies,
                    data['form_fields'],
                    data['company_name'],
                    data['dot_number'],
                    captcha_input
                )
                
                results = parse_results(resp.content)
                
                if results is not None and not results.empty:
                    st.success("✅ Search completed!")
                    st.dataframe(results, use_container_width=True)
                    
                    csv = results.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name="fmcsa_results.csv",
                        mime="text/csv"
                    )
                else:
                    st.error("Invalid CAPTCHA or no records returned.")
                    
            except Exception as e:
                st.error(f"Error submitting CAPTCHA: {str(e)}")
            finally:
                st.session_state.captcha_image_bytes = None
                st.session_state.search_data = None
