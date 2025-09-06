# E261 Voice Claims Backend

## Deployment to Render

### Prerequisites
1. A Render account (https://render.com)
2. ElevenLabs API key for speech-to-text and text-to-speech
3. (Optional) Zoho CRM credentials for claim submission

### Steps to Deploy:

#### Option 1: Using Render Dashboard (Recommended)

1. **Connect Repository**:
   - Go to https://render.com/dashboard
   - Click "New" → "Web Service"
   - Connect your GitHub repository

2. **Configure Service**:
   - **Name**: `e261-voice-backend`
   - **Environment**: `Python 3`
   - **Region**: `Oregon (US West)`
   - **Branch**: `main`
   - **Root Directory**: Leave empty (root)
   - **Runtime**: `Python 3.11.9`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd backend && python -m uvicorn server_api:app --host 0.0.0.0 --port $PORT`

3. **Set Environment Variables**:
   In the Render dashboard, add these environment variables:
   ```
   ELEVEN_API_KEY=your_elevenlabs_api_key_here
   ELEVEN_VOICE_ID=your_voice_id_here
   ELEVEN_STT_MODEL=scribe_v1
   FRONTEND_URL=https://your-service-name.onrender.com
   BACKEND_URL=https://your-service-name.onrender.com
   ```

   Optional Zoho variables:
   ```
   ZOHO_CLIENT_ID=your_zoho_client_id
   ZOHO_CLIENT_SECRET=your_zoho_client_secret
   ZOHO_REFRESH_TOKEN=your_zoho_refresh_token
   ```

4. **Deploy**: Click "Create Web Service"

#### Option 2: Using render.yaml (Infrastructure as Code)

1. Push the `render.yaml` file to your repository
2. In Render dashboard, create a new "Blueprint" and select your repository
3. Render will automatically detect and deploy based on the YAML configuration

### Local Development

1. **Setup Virtual Environment**:
   ```bash
   cd backend
   python -m venv test_env
   # Windows:
   .\test_env\Scripts\Activate.ps1
   # macOS/Linux:
   source test_env/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Environment Variables**:
   Copy `.env.example` to `.env` and fill in your API keys

4. **Run Server**:
   ```bash
   python -m uvicorn server_api:app --host 0.0.0.0 --port 8000 --reload
   ```

### Troubleshooting

**Common Issues**:

1. **Import Errors**: Make sure you're using Python 3.11.9 and the exact package versions in requirements.txt

2. **Port Issues**: Render automatically sets the `PORT` environment variable. Don't hardcode port 8000

3. **Path Issues**: The start command includes `cd backend` because the Python files are in the backend directory

4. **Environment Variables**: Make sure all required environment variables are set in Render dashboard

5. **Build Failures**: Check that requirements.txt is in the root directory and contains compatible package versions

### API Endpoints

- `GET /health` - Health check
- `POST /stt` - Speech to text conversion
- `POST /tts` - Text to speech conversion
- `POST /conversation/start` - Start conversation session
- `POST /conversation/respond` - Continue conversation
- `POST /submit-claim` - Submit claim to Zoho CRM

### File Structure
```
├── README.md
├── requirements.txt          # Python dependencies
├── runtime.txt              # Python version for Render
├── Procfile                 # Alternative process file
├── start.sh                 # Startup script
├── render.yaml              # Render configuration
├── .env.example             # Environment variables template
└── backend/
    ├── server_api.py        # Main FastAPI application
    ├── helpers.py           # Helper functions
    ├── zoho_client.py       # Zoho CRM integration
    └── test_env/            # Virtual environment (local only)
```