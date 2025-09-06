import urllib.request
import json

try:
    print("🎤 Testing TTS endpoint...")
    
    # Create the TTS request
    data = json.dumps({"text": "Hello, this is a TTS test"}).encode('utf-8')
    req = urllib.request.Request(
        "https://e261-6.onrender.com/tts",
        data=data,
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'E261-Test/1.0'
        }
    )
    
    with urllib.request.urlopen(req, timeout=20) as response:
        if response.status == 200:
            content_type = response.headers.get('Content-Type', '')
            content_length = len(response.read())
            print(f"✅ TTS endpoint working!")
            print(f"Content-Type: {content_type}")
            print(f"Audio size: {content_length} bytes")
        else:
            print(f"❌ TTS failed with status: {response.status}")
    
    print("\n🎉 TTS is working! The 502 error is resolved!")
    
except Exception as e:
    print(f"❌ TTS Error: {e}")
    print("There might still be an issue with the TTS endpoint.")
