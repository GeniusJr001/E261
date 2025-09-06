#!/usr/bin/env python3
"""
Debug script to test TTS functionality directly
"""
import requests
import os
import json
from typing import Optional

def test_tts_endpoint():
    """Test the TTS endpoint with detailed error reporting"""
    
    # Test configuration
    base_url = "https://e261-6.onrender.com"
    tts_url = f"{base_url}/tts"
    
    # Test payload
    test_payload = {
        "text": "Hello, this is a test message for TTS functionality."
    }
    
    print("=" * 50)
    print("TTS ENDPOINT DEBUG TEST")
    print("=" * 50)
    print(f"URL: {tts_url}")
    print(f"Payload: {json.dumps(test_payload, indent=2)}")
    print()
    
    try:
        print("Making TTS request...")
        response = requests.post(
            tts_url,
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            print("✅ TTS request successful!")
            print(f"Content Type: {response.headers.get('content-type', 'Unknown')}")
            print(f"Content Length: {len(response.content)} bytes")
            
            # Save the audio file for verification
            with open("test_tts_output.mp3", "wb") as f:
                f.write(response.content)
            print("Audio saved as 'test_tts_output.mp3'")
            
        else:
            print(f"❌ TTS request failed with status {response.status_code}")
            print("Response Headers:")
            for key, value in response.headers.items():
                print(f"  {key}: {value}")
            print()
            
            print("Response Content:")
            try:
                # Try to parse as JSON first
                error_data = response.json()
                print(json.dumps(error_data, indent=2))
            except:
                # If not JSON, print as text
                print(f"Raw content: {response.text}")
                print(f"Raw bytes: {response.content}")
    
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 30 seconds")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

def test_health_endpoint():
    """Test the health endpoint to verify service is running"""
    
    health_url = "https://e261-6.onrender.com/health"
    
    print("=" * 50)
    print("HEALTH ENDPOINT TEST")
    print("=" * 50)
    print(f"URL: {health_url}")
    print()
    
    try:
        response = requests.get(health_url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Health check successful!")
            health_data = response.json()
            print("Health Data:")
            print(json.dumps(health_data, indent=2))
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    print()

if __name__ == "__main__":
    print("Starting TTS Debug Tests...")
    print()
    
    # First test health to make sure service is up
    test_health_endpoint()
    
    # Then test TTS functionality
    test_tts_endpoint()
    
    print()
    print("Debug tests completed!")
