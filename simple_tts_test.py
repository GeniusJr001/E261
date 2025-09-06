import requests

print("Testing TTS endpoint...")
try:
    resp = requests.post(
        "https://e261-6.onrender.com/tts", 
        json={"text": "Test"}, 
        timeout=15
    )
    print(f"Status: {resp.status_code}")
    print(f"Content-Type: {resp.headers.get('content-type')}")
    if resp.status_code == 200:
        print(f"✅ TTS working! Audio size: {len(resp.content)} bytes")
    else:
        print(f"❌ Error: {resp.text[:200]}")
except Exception as e:
    print(f"❌ Exception: {e}")
