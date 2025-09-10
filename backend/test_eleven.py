import os, requests, sys
API_KEY = os.getenv("ELEVEN_API_KEY")
VOICE_ID = os.getenv("ELEVEN_VOICE_ID")
if not API_KEY or not VOICE_ID:
    print("ELEVEN_API_KEY or ELEVEN_VOICE_ID not set")
    sys.exit(1)
url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream"
headers = {"xi-api-key": API_KEY, "Accept": "audio/wav", "Content-Type": "application/json"}
body = {"text": "Connectivity test from local script", "voice_settings": {"stability":0.5, "similarity_boost":0.75}}
try:
    r = requests.post(url, headers=headers, json=body, timeout=30)
    print("status:", r.status_code)
    print("content-type:", r.headers.get("content-type"))
    data = r.content
    print("length:", len(data))
    print("first4:", data[:4])
    open("eleven_direct_test.wav", "wb").write(data)
    print("saved eleven_direct_test.wav")
except Exception as e:
    print("exception:", e)