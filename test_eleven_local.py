import os, requests
API_KEY = os.environ.get("ELEVEN_API_KEY")
VOICE_ID = os.environ.get("ELEVEN_VOICE_ID")
if not API_KEY or not VOICE_ID:
    print("Missing ELEVEN_API_KEY or ELEVEN_VOICE_ID in your environment"); raise SystemExit(1)
url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream"
hdr = {"xi-api-key": API_KEY, "Accept": "audio/wav, audio/mpeg", "Content-Type": "application/json"}
payload = {"text":"Hello from test_eleven_local"}
resp = requests.post(url, headers=hdr, json=payload, timeout=30)
print("status:", resp.status_code, "content-type:", resp.headers.get("content-type"), "len:", len(resp.content))
open("eleven_direct.bin","wb").write(resp.content)