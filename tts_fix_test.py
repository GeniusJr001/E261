import urllib.request
import json

# Test the TTS endpoint after fix
try:
    print("Testing TTS endpoint after fix...")
    
    data = json.dumps({"text": "Test message"}).encode('utf-8')
    req = urllib.request.Request(
        "https://e261-6.onrender.com/tts",
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    
    with urllib.request.urlopen(req, timeout=30) as response:
        print(f"Status: {response.status}")
        if response.status == 200:
            audio_size = len(response.read())
            print(f"✅ TTS fixed! Audio size: {audio_size} bytes")
        else:
            print(f"❌ Still failing: {response.status}")
            
except Exception as e:
    print(f"Error: {e}")
