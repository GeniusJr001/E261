import requests
import json

def test_backend():
    base_url = "https://e261-6.onrender.com"
    
    # Test health endpoint
    try:
        print("Testing health endpoint...")
        resp = requests.get(f"{base_url}/health", timeout=10)
        print(f"Health Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"Health Response: {resp.json()}")
        else:
            print(f"Health Error: {resp.text}")
    except Exception as e:
        print(f"Health endpoint failed: {e}")
    
    # Test TTS endpoint
    try:
        print("\nTesting TTS endpoint...")
        resp = requests.post(f"{base_url}/tts", json={"text": "Hello world"}, timeout=15)
        print(f"TTS Status: {resp.status_code}")
        print(f"TTS Content-Type: {resp.headers.get('content-type')}")
        if resp.status_code != 200:
            print(f"TTS Error: {resp.text}")
    except Exception as e:
        print(f"TTS endpoint failed: {e}")

if __name__ == "__main__":
    test_backend()
