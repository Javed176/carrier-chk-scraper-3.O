import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from PIL import Image
import io

st.set_page_config(page_title="FMCSA Company Snapshot Scraper", layout="wide")

st.title("🚛 FMCSA Company Snapshot Scraper")

# Initialize session state
if 'captcha_image' not in st.session_state:
    st.session_state.captcha_image = None
if 'search_data' not in st.session_state:
    st.session_state.search_data = None

def get_fmcsa_session():
    """Initialize session and get initial page"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    base_url = "https://safer.fmcsa.dot.gov/CompanySnapshot.aspx"
    response = session.get(base_url)
    
    return session, response

def extract_form_fields(html_content):
    """Extract ASP.NET form fields"""
    soup = BeautifulSoup(html_content, 'html.parser')
    fields = {}
    
    for field_id in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']:
        element = soup.find('input', {'id': field_id})
        fields[field_id] = element['value'] if element else ''
    
    return fields, soup

def search_fmcsa(session, form_fields, company_name="", dot_number="", captcha_text=""):
    """Perform search with CAPTCHA"""
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
    
    response = session.post(base_url, data=form_data)
    return response

def parse_results(html_content):
    """Parse search results into DataFrame"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the results table - adjust selector based on actual structure
    table = soup.find('table', {'id': 'MainContent_gvSearchResult'})
    
    if not table:
        # Try alternative selectors
        table = soup.find('table', class_='datagrid')
    
    if table:
        # Parse table into DataFrame
        df = pd.read_html(str(table))[0]
        return df
    
    return None

# Sidebar for search parameters
with st.sidebar:
    st.header("Search Parameters")
    search_type = st.radio("Search by:", ["DOT Number", "Company Name"])
    
    if search_type == "DOT Number":
        dot_number = st.text_input("Enter DOT Number:", placeholder="123456")
        company_name = ""
    else:
        company_name = st.text_input("Enter Company Name:", placeholder="ABC Trucking")
        dot_number = ""
    
    search_button = st.button("Initialize Search")

# Main content area
if search_button:
    with st.spinner("Connecting to FMCSA..."):
        try:
            # Initialize session
            session, response = get_fmcsa_session()
            form_fields, soup = extract_form_fields(response.content)
            
            # Check for CAPTCHA
            captcha_img = soup.find('img', {'id': 'MainContent_CaptchaImage'})
            
            if captcha_img:
                # Extract CAPTCHA image
                captcha_src = captcha_img.get('src')
                if captcha_src:
                    captcha_url = f"https://safer.fmcsa.dot.gov/{captcha_src}"
                    captcha_response = session.get(captcha_url)
                    
                    # Display CAPTCHA
                    st.session_state.captcha_image = Image.open(io.BytesIO(captcha_response.content))
                    st.session_state.search_data = {
                        'session': session,
                        'form_fields': form_fields,
                        'company_name': company_name,
                        'dot_number': dot_number
                    }
                    
                    st.warning("⚠️ CAPTCHA detected! Please solve it manually.")
            else:
                # No CAPTCHA, try direct search
                response = search_fmcsa(session, form_fields, company_name, dot_number)
                results = parse_results(response.content)
                
                if results is not None and not results.empty:
                    st.success("✅ Search completed!")
                    st.dataframe(results)
                    
                    # Download button
                    csv = results.to_csv(index=False)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv,
                        file_name="fmcsa_results.csv",
                        mime="text/csv"
                    )
                else:
                    st.error("No results found or search failed")
                    
        except Exception as e:
            st.error(f"Error: {str(e)}")

# CAPTCHA handling section
if st.session_state.captcha_image is not None:
    st.header("🔐 CAPTCHA Required")
    
    # Display CAPTCHA image
    st.image(st.session_state.captcha_image, caption="Please enter the text shown above")
    
    captcha_input = st.text_input("Enter CAPTCHA text:")
    
    if st.button("Submit CAPTCHA"):
        with st.spinner("Processing..."):
            try:
                data = st.session_state.search_data
                response = search_fmcsa(
                    data['session'],
                    data['form_fields'],
                    data['company_name'],
                    data['dot_number'],
                    captcha_input
                )
                
                results = parse_results(response.content)
                
                if results is not None and not results.empty:
                    st.success("✅ Search completed!")
                    st.dataframe(results)
                    
                    # Download button
                    csv = results.to_csv(index=False)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv,
                        file_name="fmcsa_results.csv",
                        mime="text/csv"
                    )
                else:
                    st.error("No results found or CAPTCHA was incorrect")
                    
                # Clear CAPTCHA state
                st.session_state.captcha_image = None
                st.session_state.search_data = None
                
            except Exception as e:
                st.error(f"Error: {str(e)}")

st.markdown("---")
st.info("⚠️ **Note:** This website uses CAPTCHA. You'll need to manually enter it when prompted.")
