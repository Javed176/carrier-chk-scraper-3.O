import re
import requests
from bs4 import BeautifulSoup

def scrape_safer(search_value: str, search_type: str = "MC"):
    """
    Scrapes SAFER Company Snapshot directly from safer.fmcsa.dot.gov.
    No API token required.
    
    search_type options: 'MC' (MC/MX Number), 'USDOT' (DOT Number), 'NAME'
    """
    url = "https://safer.fmcsa.dot.gov/query.asp"

    param_map = {
        "MC": "MC_MX",
        "USDOT": "USDOT",
        "NAME": "NAME"
    }

    payload = {
        "searchtype": "ANY",
        "query_type": "queryCarrierSnapshot",
        "query_param": param_map.get(search_type.upper(), "MC_MX"),
        "query_string": str(search_value).strip()
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://safer.fmcsa.dot.gov/CompanySnapshot.aspx"
    }

    response = requests.post(url, data=payload, headers=headers, timeout=15)
    
    if response.status_code != 200:
        return {"status": "error", "message": f"HTTP {response.status_code}"}

    if "No record found" in response.text or "Record Not Found" in response.text:
        return {"status": "not_found", "message": "No carrier found"}

    soup = BeautifulSoup(response.text, "html.parser")

    def get_val(label):
        tag = soup.find(lambda t: t.name in ['td', 'th'] and label in t.text)
        if tag and tag.find_next_sibling('td'):
            raw = tag.find_next_sibling('td').get_text(separator=" ", strip=True)
            return re.sub(r'\s+', ' ', raw)
        return "N/A"

    data = {
        "mc_number": search_value,
        "legal_name": get_val("Legal Name:"),
        "dba_name": get_val("DBA Name:"),
        "usdot_number": get_val("USDOT Number:"),
        "entity_type": get_val("Entity Type:"),
        "operating_status": get_val("Operating Status:"),
        "out_of_service": get_val("Out of Service:"),
        "physical_address": get_val("Physical Address:"),
        "phone": get_val("Phone:")
    }

    return {"status": "success", "data": data}

# Test execution
if __name__ == "__main__":
    result = scrape_safer("1066434", search_type="MC")
    print(result)
