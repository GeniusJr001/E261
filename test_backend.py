import requests
import json
import time

def test_backend():
    base_url = "https://e261-6.onrender.com"
    
    print("🔍 Testing E261 Backend...")
    print("=" * 40)
    
    # Test health endpoint
    try:
        print("1️⃣ Testing health endpoint...")
        resp = requests.get(f"{base_url}/health", timeout=15)
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✅ Health check passed!")
            print(f"   📊 FastAPI: {data.get('fastapi_version', 'unknown')}")
            print(f"   🐍 Python: {data.get('python_version', 'unknown')}")
            env = data.get('environment', {})
            print(f"   🔑 ElevenLabs: {env.get('eleven_api_configured', False)}")
            print(f"   🎙️ Voice ID: {env.get('eleven_voice_configured', False)}")
        else:
            print(f"   ❌ Health failed: {resp.text[:100]}")
            return False
    except Exception as e:
        print(f"   ❌ Health error: {e}")
        return False
    
    # Test TTS endpoint
    try:
        print("\n2️⃣ Testing TTS endpoint...")
        test_text = "Hello world test"
        resp = requests.post(f"{base_url}/tts", 
                           json={"text": test_text}, 
                           timeout=25)
        print(f"   Status: {resp.status_code}")
        print(f"   Content-Type: {resp.headers.get('content-type', 'unknown')}")
        
        if resp.status_code == 200:
            print(f"   ✅ TTS working!")
            print(f"   📦 Audio size: {len(resp.content)} bytes")
            if len(resp.content) > 0:
                print(f"   🎵 Audio data received successfully")
            else:
                print(f"   ⚠️ Warning: Empty audio response")
        else:
            print(f"   ❌ TTS failed with status {resp.status_code}")
            print(f"   📝 Error response: {resp.text[:300]}")
            return False
    except Exception as e:
        print(f"   ❌ TTS error: {e}")
        return False
    
    print(f"\n🎉 All tests passed! Backend is working correctly.")
    return True

if __name__ == "__main__":
    success = test_backend()
    if not success:
        print("\n🚨 Some tests failed.")
        print("📋 Troubleshooting steps:")
        print("   1. Check Render dashboard: https://dashboard.render.com")
        print("   2. Look for deployment errors in logs")
        print("   3. Verify environment variables are set")
        print("   4. Try redeploying the service")
