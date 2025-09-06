import time
import requests

def wake_up_service():
    """Try to wake up the Render service by making multiple requests"""
    base_url = "https://e261-6.onrender.com"
    
    print("Attempting to wake up Render service...")
    
    for i in range(5):
        try:
            print(f"Attempt {i+1}/5...")
            resp = requests.get(f"{base_url}/health", timeout=30)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print("✅ Service is awake!")
                print(f"Response: {resp.json()}")
                return True
            else:
                print(f"Response: {resp.text[:200]}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
        
        if i < 4:  # Don't wait after the last attempt
            print("Waiting 10 seconds before next attempt...")
            time.sleep(10)
    
    print("❌ Failed to wake up service after 5 attempts")
    return False

if __name__ == "__main__":
    success = wake_up_service()
    
    if success:
        print("\n🔄 Testing TTS endpoint...")
        try:
            resp = requests.post("https://e261-6.onrender.com/tts", 
                               json={"text": "test"}, 
                               timeout=15)
            print(f"TTS Status: {resp.status_code}")
        except Exception as e:
            print(f"TTS Error: {e}")
    else:
        print("\n🚨 Service appears to be down. Check Render dashboard!")
