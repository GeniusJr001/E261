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
            
        # Map claim data to Zoho lead fields
        lead_data = {
            "data": [{
                "First_Name": claim_data.get('passenger_name', '').split()[0] if claim_data.get('passenger_name') else '',
                "Last_Name": ' '.join(claim_data.get('passenger_name', '').split()[1:]) if claim_data.get('passenger_name') else '',
                "Email": claim_data.get('contact_email', ''),
                "Phone": claim_data.get('phone', ''),
                "Company": claim_data.get('airline', 'Flight Delay Claim'),
                "Lead_Source": "Voice AI Website",
                "Description": self._format_claim_description(claim_data),
                "Lead_Status": "New",
                # Custom fields for flight information
                "Flight_Number": claim_data.get('flight_number', ''),
                "Flight_Date": claim_data.get('flight_date', ''),
                "Delay_Hours": claim_data.get('delay_hours', 0),
                "Departure_Airport": claim_data.get('departure_airport', ''),
                "Arrival_Airport": claim_data.get('arrival_airport', ''),
                "Claim_Status": claim_data.get('claim_status', 'New Claim'),
                "Airline_Response": claim_data.get('airline_response', ''),
            }]
        }
        
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