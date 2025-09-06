import urllib.request
import json
import sys

try:
    print("🔍 Quick backend test...")
    
    # Test health endpoint
    print("Testing health endpoint...")
    req = urllib.request.Request("https://e261-6.onrender.com/health")
    req.add_header('User-Agent', 'E261-Test/1.0')
    
    with urllib.request.urlopen(req, timeout=30) as response:
        if response.status == 200:
            data = json.loads(response.read().decode())
            print(f"✅ Health endpoint working!")
            print(f"FastAPI version: {data.get('fastapi_version', 'unknown')}")
            print(f"Environment configured: {data.get('environment', {}).get('eleven_api_configured', False)}")
        else:
            print(f"❌ Health failed with status: {response.status}")
    
    print("\n🎉 Backend fix appears successful!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("The service might still be redeploying. Try again in 1-2 minutes.")
