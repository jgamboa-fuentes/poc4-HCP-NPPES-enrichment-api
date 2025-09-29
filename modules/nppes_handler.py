# modules/nppes_handler.py
import requests

NPPES_BASE_URL = "https://npiregistry.cms.hhs.gov/api/"

def get_nppes_data(params: dict) -> dict | None:
    """
    Queries the NPPES API using a parameters dictionary and extracts key information.
    This replaces the VBA 'CallNppes' function.
    """
    # Add the required version parameter
    params["version"] = "2.1"
    npi = params.get("number", "N/A")

    try:
        response = requests.get(NPPES_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("result_count", 0) == 0:
            print(f"NPPES Error: No results found for NPI {npi}")
            return None
            
        result = data["results"][0]
        basic_info = result.get("basic", {})
        
        # Find the primary taxonomy
        primary_taxonomy = next((tax for tax in result.get("taxonomies", []) if tax.get("primary")), None)
        
        # Find the location address, fallback to mailing
        addresses = result.get("addresses", [])
        location_address = next((addr for addr in addresses if addr.get("address_purpose", "").upper() == "LOCATION"), None)
        if not location_address:
            location_address = next((addr for addr in addresses if addr.get("address_purpose", "").upper() == "MAILING"), None)

        # Consolidate the data into a clean dictionary
        output = {
            "first_name": basic_info.get("first_name"),
            "middle_name": basic_info.get("middle_name"),
            "last_name": basic_info.get("last_name"),
            "addr1": location_address.get("address_1") if location_address else None,
            "addr2": location_address.get("address_2") if location_address else None,
            "city": location_address.get("city") if location_address else None,
            "state": location_address.get("state") if location_address else None,
            "zip": location_address.get("postal_code", "").split('-')[0] if location_address else None,
            "taxonomy": primary_taxonomy.get("desc") if primary_taxonomy else None
        }
        return output

    except requests.exceptions.RequestException as e:
        print(f"NPPES API request failed for NPI {npi}: {e}")
        return None