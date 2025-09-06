import re
from typing import Dict, Any, Optional

# Define the claim fields that need to be collected
CLAIM_FIELDS = [
    "Passenger Name",
    "Contact Email", 
    "Flight Number",
    "Flight Date",
    "Airline",
    "Departure Airport",
    "Arrival Airport", 
    "Delay Hours",
    "Airline Response",
    "Claim Status"
]

def quick_pattern_extract(text: str) -> Dict[str, Any]:
    """
    Extract information from user text using regex patterns.
    Returns a dictionary with extracted data.
    """
    collected = {}
    text = text.strip()
    
    # Passenger Name
    if collected.get("Passenger Name") is None:
        # First try "my name is" pattern
        m = re.search(r"\bmy name is\s+([A-Za-z ]{2,50})", text, re.I)
        if m:
            collected["Passenger Name"] = m.group(1).strip()
        else:
            # Try other name introduction patterns
            m2 = re.search(r"\b(?:i am|name is|it is|this is)\s+([A-Za-z ]{2,50})", text, re.I)
            if m2:
                collected["Passenger Name"] = m2.group(1).strip()
            else:
                # Try to detect two or more capitalized words at start of text
                first_line = text.splitlines()[0].strip()
                # Remove common prefixes
                first_line = re.sub(r'^\s*(?:my name is|i am|name is|it is|this is)\s+', '', first_line, flags=re.I)
                parts = first_line.split()
                
                # Accept if we have 2+ words that could be a name
                if len(parts) >= 2:
                    # Check if they contain only letters, spaces, hyphens, apostrophes
                    name_candidate = " ".join(parts[:3])  # Take first 3 words max
                    if re.match(r'^[A-Za-z\s\-\']+$', name_candidate):
                        collected["Passenger Name"] = name_candidate.strip()

    # Contact Email
    if collected.get("Contact Email") is None:
        m = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if m:
            collected["Contact Email"] = m.group(0)

    # Flight Number
    if collected.get("Flight Number") is None:
        # Try pattern: letters followed by numbers (allowing more digits)
        m = re.search(r'\b([A-Za-z]{1,3}(?:\s+[A-Za-z]{1,3})*)\s*(\d{1,10})\b', text)
        if m:
            letters = re.sub(r'\s+', '', m.group(1)).upper()
            numbers = m.group(2)
            fn = letters + numbers
            if re.match(r'^[A-Z]{1,4}\d+$', fn):
                collected["Flight Number"] = fn
        else:
            # Try pattern: "flight" followed by letters and numbers
            m2 = re.search(r'\bflight\b[^A-Za-z0-9]*([A-Za-z]+)\s*(\d+)\b', text, re.I)
            if m2:
                letters = re.sub(r'\s+', '', m2.group(1)).upper()
                numbers = m2.group(2)
                fn = letters + numbers
                if re.match(r'^[A-Z]{1,4}\d+$', fn):
                    collected["Flight Number"] = fn

    # Flight Date
    if collected.get("Flight Date") is None:
        # Try various date formats
        date_patterns = [
            r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b',  # YYYY-MM-DD
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b',  # MM/DD/YYYY or DD/MM/YYYY
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2})\b',  # MM/DD/YY or DD/MM/YY
        ]
        
        for pattern in date_patterns:
            m = re.search(pattern, text)
            if m:
                if len(m.group(1)) == 4:  # YYYY-MM-DD format
                    collected["Flight Date"] = f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
                else:  # MM/DD/YYYY or similar
                    year = m.group(3)
                    if len(year) == 2:
                        year = "20" + year
                    collected["Flight Date"] = f"{year}-{m.group(1).zfill(2)}-{m.group(2).zfill(2)}"
                break

    # Airline
    if collected.get("Airline") is None:
        # Common airline names
        airlines = [
            "american", "delta", "united", "southwest", "jetblue", "alaska", 
            "spirit", "frontier", "allegiant", "british airways", "lufthansa",
            "air france", "klm", "emirates", "qatar", "etihad", "turkish",
            "virgin", "ryanair", "easyjet", "wizz air"
        ]
        
        for airline in airlines:
            if airline.lower() in text.lower():
                collected["Airline"] = airline.title()
                break

    # Delay Hours
    if collected.get("Delay Hours") is None:
        # Look for delay patterns
        delay_patterns = [
            r'(\d+(?:\.\d+)?)\s*hours?\s*delay',
            r'delay(?:ed)?\s*(?:for|by)?\s*(\d+(?:\.\d+)?)\s*hours?',
            r'(\d+(?:\.\d+)?)\s*hour\s*delay',
        ]
        
        for pattern in delay_patterns:
            m = re.search(pattern, text, re.I)
            if m:
                collected["Delay Hours"] = float(m.group(1))
                break

    # Departure Airport
    if collected.get("Departure Airport") is None:
        # Look for "from" patterns
        m = re.search(r'\bfrom\s+([A-Za-z\s]{3,30}?)(?:\s+to|\s+airport|$)', text, re.I)
        if m:
            collected["Departure Airport"] = m.group(1).strip()

    # Arrival Airport
    if collected.get("Arrival Airport") is None:
        # Look for "to" patterns
        m = re.search(r'\bto\s+([A-Za-z\s]{3,30}?)(?:\s+airport|$)', text, re.I)
        if m:
            collected["Arrival Airport"] = m.group(1).strip()

    return collected

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_flight_number(flight_number: str) -> bool:
    """Validate flight number format"""
    pattern = r'^[A-Z]{1,4}\d{1,10}$'
    return re.match(pattern, flight_number.upper()) is not None

def validate_date(date_str: str) -> bool:
    """Validate date format (YYYY-MM-DD)"""
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    return re.match(pattern, date_str) is not None

def format_claim_data(collected_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format collected data for final submission"""
    formatted = {}
    
    # Map and clean the data
    field_mapping = {
        "Passenger Name": "passenger_name",
        "Contact Email": "contact_email", 
        "Flight Number": "flight_number",
        "Flight Date": "flight_date",
        "Airline": "airline",
        "Delay Hours": "delay_hours",
        "Departure Airport": "departure_airport",
        "Arrival Airport": "arrival_airport",
        "Airline Response": "airline_response",
        "Claim Status": "claim_status"
    }
    
    for original_key, new_key in field_mapping.items():
        if original_key in collected_data and collected_data[original_key] is not None:
            formatted[new_key] = collected_data[original_key]
    
    return formatted

def estimate_compensation(delay_hours: float, airline: str = None) -> Optional[float]:
    """Estimate potential compensation based on delay hours"""
    if delay_hours < 3:
        return 0
    elif delay_hours < 6:
        return 250
    elif delay_hours < 12:
        return 400
    else:
        return 600