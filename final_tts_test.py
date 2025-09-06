import requests

print("Testing TTS endpoint now...")
try:
    response = requests.post(
        "https://e261-6.onrender.com/tts",
        json={"text": "Hello test"},
        timeout=15
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"✅ TTS working! Size: {len(response.content)} bytes")
    else:
        print(f"❌ Error: {response.text[:200]}")
except Exception as e:
    print(f"Exception: {e}")
