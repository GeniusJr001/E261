import requests
import json

def test_endpoints():
    base_url = "https://e261-6.onrender.com"
    
    print("=" * 50)
    print("COMPREHENSIVE TTS TESTING")
    print("=" * 50)
    
    # Test 1: Health endpoint
    print("1. Testing health endpoint...")
    try:
        resp = requests.get(f"{base_url}/health", timeout=10)
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            env = data.get('environment', {})
            print(f"   ✅ Health OK")
            print(f"   🔑 API Key: {env.get('eleven_api_configured')}")
            print(f"   🎙️ Voice ID: {env.get('eleven_voice_configured')}")
        else:
            print(f"   ❌ Health failed: {resp.text}")
    except Exception as e:
        print(f"   ❌ Health error: {e}")
    
    print()
    
    # Test 2: Debug environment endpoint
    print("2. Testing debug environment...")
    try:
        resp = requests.get(f"{base_url}/debug-env", timeout=10)
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✅ Debug OK")
            print(f"   🔑 API Key Present: {data.get('eleven_api_key_present')}")
            print(f"   🔑 API Key Length: {data.get('eleven_api_key_length')}")
            print(f"   🎙️ Voice ID Present: {data.get('eleven_voice_id_present')}")
            print(f"   🎙️ Voice ID: {data.get('eleven_voice_id_value')}")
        else:
            print(f"   ❌ Debug failed: {resp.text}")
    except Exception as e:
        print(f"   ❌ Debug error: {e}")
    
    print()
    
    # Test 3: TTS Test endpoint (dummy audio)
    print("3. Testing TTS-TEST endpoint (dummy audio)...")
    try:
        resp = requests.post(f"{base_url}/tts-test", 
                           json={"text": "Test message"}, 
                           timeout=15)
        print(f"   Status: {resp.status_code}")
        print(f"   Content-Type: {resp.headers.get('content-type')}")
        if resp.status_code == 200:
            print(f"   ✅ TTS-TEST working! Size: {len(resp.content)} bytes")
        else:
            print(f"   ❌ TTS-TEST failed: {resp.text[:200]}")
    except Exception as e:
        print(f"   ❌ TTS-TEST error: {e}")
    
    print()
    
    # Test 4: Main TTS endpoint
    print("4. Testing main TTS endpoint...")
    try:
        resp = requests.post(f"{base_url}/tts", 
                           json={"text": "Hello world test"}, 
                           timeout=30)
        print(f"   Status: {resp.status_code}")
        print(f"   Content-Type: {resp.headers.get('content-type')}")
        if resp.status_code == 200:
            print(f"   ✅ TTS working! Size: {len(resp.content)} bytes")
            # Save audio for verification
            with open("test_audio_output.mp3", "wb") as f:
                f.write(resp.content)
            print(f"   💾 Audio saved as test_audio_output.mp3")
        else:
            print(f"   ❌ TTS failed: {resp.text[:300]}")
    except Exception as e:
        print(f"   ❌ TTS error: {e}")
    
    print()
    print("=" * 50)
    print("TEST COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    test_endpoints()
