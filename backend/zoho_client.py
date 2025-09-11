import os
import requests
import json
from typing import Dict, Any, Optional
from datetime import datetime

class ZohoClient:
    def __init__(self):
        self.client_id = os.getenv('ZOHO_CLIENT_ID')
        self.client_secret = os.getenv('ZOHO_CLIENT_SECRET')
        self.refresh_token = os.getenv('ZOHO_REFRESH_TOKEN')
        self.access_token = None
        self.base_url = 'https://www.zohoapis.com/crm/v2'
        self.enabled = os.getenv('ZOHO_ENABLED', 'false').lower() == 'true'
        
    def get_access_token(self) -> Optional[str]:
        """Get fresh access token using refresh token"""
        if not self.enabled:
            return None
            
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            print("Missing Zoho credentials")
            return None
            
        url = "https://accounts.zoho.com/oauth/v2/token"
        
        data = {
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token'
        }
        
        try:
            response = requests.post(url, data=data)
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                return self.access_token
            else:
                print(f"Token refresh failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return None
    
    def create_lead(self, claim_data: Dict[str, Any]) -> Optional[str]:
        """Create a lead in Zoho CRM"""
        if not self.enabled:
            print("Zoho integration disabled")
            return None

        if not self.access_token:
            self.get_access_token()

        if not self.access_token:
            return None

        # Map our canonical claim fields to Zoho API fields (adjust keys as your Zoho schema expects)
        passenger = claim_data.get('Passenger_Name') or claim_data.get('passenger_name') or ""
        first_name = passenger.split()[0] if passenger else ""
        last_name = " ".join(passenger.split()[1:]) if passenger and len(passenger.split()) > 1 else first_name

        lead_record = {
            "First_Name": first_name,
            "Last_Name": last_name,
            "Email": claim_data.get('Contact_Email') or claim_data.get('contact_email') or "",
            "Company": claim_data.get('Airline') or claim_data.get('airline') or "Flight Delay Claim",
            "Lead_Source": "Voice AI Website",
            "Description": self._format_claim_description(claim_data),
            "Lead_Status": claim_data.get('Claim_Status') or claim_data.get('claim_status') or "New",
            # Custom or mapped fields - ensure these field API names match your Zoho setup
            "Flight_Number": claim_data.get('Flight_Number') or claim_data.get('flight_number') or "",
            "Flight_Date": claim_data.get('Flight_Date') or claim_data.get('flight_date') or "",
            "Departure_Airport": claim_data.get('Departure_Airport') or claim_data.get('departure_airport') or "",
            "Departure_Time": claim_data.get('Departure_time') or claim_data.get('departure_time') or "",
            "Arrival_Airport": claim_data.get('Arrival_Airport') or claim_data.get('arrival_airport') or "",
            "Arrival_Time": claim_data.get('Arrival_time') or claim_data.get('arrival_time') or "",
            "Delay_Hours": claim_data.get('Delay_Hours') or claim_data.get('delay_hours') or 0,
            "Compensation_Amount": claim_data.get('Compensation_Amount') or claim_data.get('compensation_amount') or "",
            "Airline_Response": claim_data.get('Airline_Response') or claim_data.get('airline_response') or "",
            "Booking_Reference": claim_data.get('Booking_Reference') or claim_data.get('booking_reference') or ""
        }

        lead_data = {"data": [lead_record]}

        headers = {
            'Authorization': f'Zoho-oauthtoken {self.access_token}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(
                f'{self.base_url}/Leads',
                headers=headers,
                data=json.dumps(lead_data)
            )

            if response.status_code == 201:
                result = response.json()
                if result.get('data') and len(result['data']) > 0:
                    lead_id = result['data'][0].get('details', {}).get('id')
                    print(f"Lead created successfully: {lead_id}")
                    return lead_id
            else:
                print(f"Failed to create lead: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"Error creating lead: {e}")
            return None
    
    def update_lead(self, lead_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing lead"""
        if not self.enabled:
            return False
            
        if not self.access_token:
            self.get_access_token()
            
        if not self.access_token:
            return False
            
        update_data = {
            "data": [{
                "id": lead_id,
                **updates
            }]
        }
        
        headers = {
            'Authorization': f'Zoho-oauthtoken {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.put(
                f'{self.base_url}/Leads',
                headers=headers,
                data=json.dumps(update_data)
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"Error updating lead: {e}")
            return False
    
    def attach_file_to_lead(self, lead_id: str, file_path: str, filename: str) -> bool:
        """Attach a file to a lead"""
        if not self.enabled:
            return False
            
        if not self.access_token:
            self.get_access_token()
            
        if not self.access_token:
            return False
            
        headers = {
            'Authorization': f'Zoho-oauthtoken {self.access_token}',
        }
        
        try:
            with open(file_path, 'rb') as file:
                files = {
                    'file': (filename, file, 'application/octet-stream')
                }
                
                response = requests.post(
                    f'{self.base_url}/Leads/{lead_id}/Attachments',
                    headers=headers,
                    files=files
                )
                
                return response.status_code == 200
                
        except Exception as e:
            print(f"Error attaching file: {e}")
            return False
    
    def _format_claim_description(self, claim_data: Dict[str, Any]) -> str:
        """Format claim data into a description"""
        description_parts = ["Flight Delay Claim Details:"]
        
        if claim_data.get('flight_number'):
            description_parts.append(f"Flight: {claim_data['flight_number']}")
            
        if claim_data.get('flight_date'):
            description_parts.append(f"Date: {claim_data['flight_date']}")
            
        if claim_data.get('delay_hours'):
            description_parts.append(f"Delay: {claim_data['delay_hours']} hours")
            
        if claim_data.get('departure_airport') and claim_data.get('arrival_airport'):
            description_parts.append(f"Route: {claim_data['departure_airport']} → {claim_data['arrival_airport']}")
            
        if claim_data.get('airline_response'):
            description_parts.append(f"Airline Response: {claim_data['airline_response']}")
            
        description_parts.append(f"Submitted via Voice AI on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(description_parts)
    
    def search_existing_claim(self, email: str, flight_number: str) -> Optional[str]:
        """Search for existing claim by email and flight number"""
        if not self.enabled:
            return None
            
        if not self.access_token:
            self.get_access_token()
            
        if not self.access_token:
            return None
            
        headers = {
            'Authorization': f'Zoho-oauthtoken {self.access_token}',
        }
        
        try:
            # Search by email and flight number
            search_url = f"{self.base_url}/Leads/search"
            params = {
                'email': email,
                'criteria': f'(Email:equals:{email})and(Flight_Number:equals:{flight_number})'
            }
            
            response = requests.get(search_url, headers=headers, params=params)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('data') and len(result['data']) > 0:
                    return result['data'][0].get('id')
                    
            return None
            
        except Exception as e:
            print(f"Error searching for existing claim: {e}")
            return None

# Global instance
zoho_client = ZohoClient()