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
st.markdown("Search by DOT Number or Company Name (MC numbers not directly supported)")

# Initialize session state
if 'captcha_image' not in st.session_state:
    st.session_state.captcha_image = None
if 'search_data' not in st.session_state:
    st.session_state.search_data = None

def get_fmcsa_session():
    """Initialize session and get initial page"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    })
    
    base_url = "https://safer.fmcsa.dot.gov/CompanySnapshot.aspx"
    response = session.get(base_url)
    time.sleep(random.uniform(1, 3))
    
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
    time.sleep(random.uniform(1, 2))
    return response

def parse_results(html_content):
    """Parse search results into DataFrame"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Try multiple table selectors
    table = None
    for selector in ['MainContent_gvSearchResult', 'datagrid', 'gridview']:
        table = soup.find('table', {'id': selector})
        if table:
            break
    
    if table:
        try:
            # Parse table into DataFrame
            df = pd.read_html(str(table))[0]
            return df
        except:
            pass
    
    # Try parsing individual rows
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
            df = pd.DataFrame(data)
            return df
    
    return None

def search_by_mc_number(mc_number):
    """
    Alternative: Use FMCSA's public API to look up MC numbers
    This bypasses the CAPTCHA issue
    """
    try:
        # Try the FMCSA API endpoint
        api_url = f"https://mobile.fmcsa.dot.gov/rest/v1/carrier/docket/{mc_number}"
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        }
        
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'content' in data and data['content']:
                return pd.DataFrame([data['content']])
        
        return None
    except:
        return None

# Sidebar for search parameters
with st.sidebar:
    st.header("Search Parameters")
    
    search_type = st.radio("Search by:", ["DOT Number", "Company Name", "MC Number (Experimental)"])
    
    dot_number = ""
    company_name = ""
    mc_number = ""
    
    if search_type == "DOT Number":
        dot_number = st.text_input("Enter DOT Number:", placeholder="123456")
        st.info("MC numbers are not directly supported. Use DOT number instead.")
    elif search_type == "Company Name":
        company_name = st.text_input("Enter Company Name:", placeholder="ABC Trucking")
        st.info("Enter the full or partial company name")
    else:  # MC Number
        mc_number = st.text_input("Enter MC Number:", placeholder="MC-123456 or 123456")
        st.warning("⚠️ MC number search is experimental and may not work")
    
    search_button = st.button("Search")

# Main content area
if search_button:
    if search_type == "MC Number (Experimental)":
        with st.spinner("Searching by MC number..."):
            try:
                # Clean MC number
                mc_number = mc_number.replace("MC-", "").replace("mc-", "").strip()
                
                # Try API first
                results = search_by_mc_number(mc_number)
                
                if results is not None and not results.empty:
                    st.success("✅ Results found!")
                    st.dataframe(results)
                    
                    # Download button
                    csv = results.to_csv(index=False)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv,
                        file_name=f"fmcsa_mc_{mc_number}_results.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("MC number search failed. Try searching by DOT number instead.")
                    st.info("Tip: You can find DOT numbers on the FMCSA website or use the company name search")
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    else:
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
st.info("""
**Important Notes:**
- MC numbers are NOT directly searchable on this website
- Use DOT number instead (they're often linked)
- Try searching by company name to find DOT numbers
- The FMCSA API may work for MC numbers in some cases
""")
