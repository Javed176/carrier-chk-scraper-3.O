import re
import requests
from bs4 import BeautifulSoup

def query_fmcsa_safer(search_value: str, search_type: str = "MC"):
    """
    Scrapes FMCSA SAFER Company Snapshot.
    
    :param search_value: The MC Number or USDOT Number (e.g., '1066434' or '345678')
    :param search_type: 'MC' for MC/MX Number, 'USDOT' for DOT Number, or 'NAME' for Company Name
    """
    url = "https://safer.fmcsa.dot.gov/query.asp"

    # Map search types to SAFER query parameters
    query_param_map = {
        "MC": "MC_MX",
        "USDOT": "USDOT",
        "NAME": "NAME"
    }
    
    # Payload simulating form submission on query.asp
    payload = {
        "searchtype": "ANY",
        "query_type": "queryCarrierSnapshot",
        "query_param": query_param_map.get(search_type.upper(), "MC_MX"),
        "query_string": str(search_value).strip()
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://safer.fmcsa.dot.gov/CompanySnapshot.aspx",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        response = requests.post(url, data=payload, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return {"status": "error", "message": f"HTTP {response.status_code}"}

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Check if record was found
        if "No record found" in response.text or "Record Not Found" in response.text:
            return {"status": "not_found", "message": f"No carrier found for {search_value}"}

        # Parse main identification table
        carrier_info = {
            "search_query": search_value,
            "legal_name": get_table_cell_value(soup, "Legal Name:"),
            "dba_name": get_table_cell_value(soup, "DBA Name:"),
            "usdot_number": get_table_cell_value(soup, "USDOT Number:"),
            "mc_number": get_table_cell_value(soup, "MC/MX/FF Number(s):"),
            "entity_type": get_table_cell_value(soup, "Entity Type:"),
            "operating_status": get_table_cell_value(soup, "Operating Status:"),
            "out_of_service": get_table_cell_value(soup, "Out of Service:"),
            "physical_address": get_table_cell_value(soup, "Physical Address:"),
            "phone": get_table_cell_value(soup, "Phone:")
        }

        return {"status": "success", "data": carrier_info}

    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_table_cell_value(soup, label_text):
    """Helper function to extract table data following a specific label field."""
    try:
        # Find cell containing label string
        element = soup.find(lambda tag: tag.name in ['td', 'th'] and label_text in tag.text)
        if element:
            next_td = element.find_next_sibling('td')
            if next_td:
                # Clean up extracted string
                text = next_td.get_text(separator=" ", strip=True)
                return re.sub(r'\s+', ' ', text)
    except Exception:
        pass
    return "N/A"


# --- TESTING RUN ---
if __name__ == "__main__":
    test_mc = "1066434"  # Replace with MC number to test
    print(f"Fetching data for MC-{test_mc} from FMCSA SAFER...")
    
    result = query_fmcsa_safer(test_mc, search_type="MC")
    print("\nResult:")
    print(result)
