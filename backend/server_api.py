from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Request, Form
from fastapi.responses import StreamingResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional, List
import os, tempfile, requests, shutil, uuid
import sys, os, traceback
import mimetypes
import subprocess
import re
import datetime
import hashlib
import platform
import fastapi
import pydantic
from functools import lru_cache
try:
    from dateutil import parser as dateutil_parser
except Exception:
    dateutil_parser = None

def parse_date_from_text(text: str) -> Optional[str]:
    """
    Extract a date from free-form text and return ISO date string (YYYY-MM-DD),
    or None if no usable date found.

    Improvements:
    - Accept ordinals (23rd, 1st).
    - Accept numeric months and named months.
    - Accept years spoken as words (e.g. "twenty twenty five", "two thousand twenty five").
    - Accept day expressed as words (e.g. "twenty three").
    """
    if not text:
        return None
    t = text.strip().lower()

    # helper: convert small number words -> int (supports up to 999)
    units = {
        "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
        "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19
    }
    tens = {
        "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
        "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90
    }

    def words_to_int(s: str) -> Optional[int]:
        # normalize separators
        s = re.sub(r'[\-\,]', ' ', s).strip()
        if not s:
            return None
        parts = s.split()
        val = 0
        i = 0
        while i < len(parts):
            p = parts[i]
            if p in units:
                val += units[p]
            elif p in tens:
                # handle e.g. "twenty five"
                v = tens[p]
                # next part might be unit
                if i + 1 < len(parts) and parts[i + 1] in units:
                    val += v + units[parts[i + 1]]
                    i += 1
                else:
                    val += v
            elif p == "hundred":
                # multiply previous unit (if any) or 1
                if val == 0:
                    val = 100
                else:
                    val *= 100
            elif p == "thousand":
                if val == 0:
                    val = 1000
                else:
                    val *= 1000
            else:
                # unknown token
                try:
                    # maybe it's numeric text
                    nv = int(p)
                    val += nv
                except Exception:
                    return None
            i += 1
        return val

    def parse_year_words(s: str) -> Optional[int]:
        s = s.strip()
        # direct numeric year
        mnum = re.search(r'\b(\d{4})\b', s)
        if mnum:
            return int(mnum.group(1))
        # common pattern: "two thousand twenty five"
        if "thousand" in s or "hundred" in s:
            v = words_to_int(s)
            if v and 1900 < v < 3000:
                return v
        # pattern: "twenty twenty five" -> 2000 + 25
        m = re.findall(r'\btwenty\b|\b' + r'|'.join(re.escape(k) for k in units.keys()) + r'|\b' + r'|'.join(re.escape(k) for k in tens.keys()), s)
        # Try to parse sequence after "twenty"
        if s.startswith("twenty"):
            rest = s[len("twenty"):].strip()
            if rest:
                small = words_to_int(rest)
                if small is not None and 0 <= small < 100:
                    return 2000 + small
                # also handle "twenty twenty five"
                parts = rest.split()
                if len(parts) >= 2:
                    first = words_to_int(parts[0])
                    second = words_to_int(" ".join(parts[1:]))
                    if first is not None and second is not None:
                        return 2000 + (first * 10 + second) if first < 100 else None
        # fallback: try to convert whole string to number words
        v = words_to_int(s)
        if v and 1900 < v < 3000:
            return v
        return None

    # remove ordinal suffixes like "23rd" -> "23"
    t_nosuf = re.sub(r'(\d+)(st|nd|rd|th)\b', r'\1', t, flags=re.I)

    # Try dateutil first if present (best chance to handle wordy forms)
    if dateutil_parser:
        try:
            dt = dateutil_parser.parse(t_nosuf, fuzzy=True, dayfirst=False)
            return dt.date().isoformat()
        except Exception:
            pass

    # month map
    month_names = {
        "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
        "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
        "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12
    }

    # 1) numeric day + month name + optional year (digits)
    m = re.search(r'\b(\d{1,2})\s*(?:of\s*)?([A-Za-z]+)\s*(\d{4}|\w+(?:[\s\-]\w+)*)?\b', t_nosuf, flags=re.I)
    if m:
        day_s = m.group(1)
        mon_s = m.group(2).lower()
        year_s = (m.group(3) or "").strip()
        try:
            day = int(day_s)
        except Exception:
            # maybe day is words like "twenty three"
            d2 = words_to_int(day_s)
            if d2 is None:
                day = None
            else:
                day = d2
        mon = month_names.get(mon_s.lower()[:3]) if mon_s.lower()[:3] in month_names else month_names.get(mon_s)
        if not mon:
            # try full names
            mon = month_names.get(mon_s)
        year = None
        if year_s:
            # if year_s is digits already handled by pattern; else try parse_year_words
            ynum = None
            try:
                ynum = int(year_s) if re.match(r'^\d{4}$', year_s) else None
            except Exception:
                ynum = None
            if ynum:
                year = ynum
            else:
                # try parse words to year
                py = parse_year_words(year_s)
                if py:
                    year = py
        if day and mon:
            if year is None:
                year = datetime.date.today().year
            try:
                dt = datetime.date(year, mon, day)
                return dt.isoformat()
            except Exception:
                pass

    # 2) month name + numeric day + optional year (e.g., "may 23 2025" or "may 23rd")
    m2 = re.search(r'\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(\d{4}|\w+(?:[\s\-]\w+)*))?\b', t_nosuf, flags=re.I)
    if m2:
        mon_s = m2.group(1).lower()
        day = int(m2.group(2))
        year_s = (m2.group(3) or "").strip()
        mon = month_names.get(mon_s[:3]) if mon_s[:3] in month_names else month_names.get(mon_s)
        year = None
        if year_s:
            if re.match(r'^\d{4}$', year_s):
                year = int(year_s)
            else:
                py = parse_year_words(year_s)
                if py:
                    year = py
        if mon:
            if year is None:
                year = datetime.date.today().year
            try:
                dt = datetime.date(year, mon, day)
                return dt.isoformat()
            except Exception:
                pass

    # 3) numeric date like 24/08/2025 or 24-08-2025
    m3 = re.search(r'\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})\b', t)
    if m3:
        d = int(m3.group(1)); mth = int(m3.group(2)); y = int(m3.group(3))
        if y < 100:
            y += 2000
        try:
            dt = datetime.date(y, mth, d)
            return dt.isoformat()
        except Exception:
            pass

    # 4) try to find "on <daywords> of <month> <yearwords>"
    m4 = re.search(r'\bon\s+((?:\w+\s?)+?)\s+of\s+([A-Za-z]+)(?:\s+((?:\w+\s?)+))?', t)
    if m4:
        daywords = m4.group(1).strip()
        mon_s = m4.group(2).strip()
        yearwords = (m4.group(3) or "").strip()
        day = words_to_int(daywords) or None
        mon = month_names.get(mon_s[:3]) if mon_s[:3] in month_names else month_names.get(mon_s)
        year = None
        if yearwords:
            # if yearwords is digits already handled by pattern; else try parse_year_words
            ynum = None
            try:
                ynum = int(yearwords) if re.match(r'^\d{4}$', yearwords) else None
            except Exception:
                ynum = None
            if ynum:
                year = ynum
            else:
                # try parse words to year
                py = parse_year_words(yearwords)
                if py:
                    year = py
        if day and mon:
            if year is None:
                year = datetime.date.today().year
            try:
                dt = datetime.date(year, mon, day)
                return dt.isoformat()
            except Exception:
                pass

    return None

def parse_delay_hours(text: str) -> Optional[str]:
    """
    Parse delay duration from free-form text and return normalized hours as a string.
    Accepts formats like:
      - "6 hours", "6hours", "6h", "6 hrs", "6.5 hours", "6h30"
      - word numbers like "six hours"
    Returns e.g. "6", "6.5" or None if not found.
    """
    if not text:
        return None
    t = text.lower().replace(',', '').strip()

    # pattern: "6h30" -> hours and minutes
    m = re.search(r'\b(\d{1,2})\s*h\s*(\d{1,2})\b', t)
    if m:
        hrs = int(m.group(1))
        mins = int(m.group(2))
        val = hrs + mins / 60.0
        # normalize: integer if whole number
        return str(int(val)) if val.is_integer() else str(round(val, 2))

    # pattern: numeric with units: "6", "6 hours", "6.5 hours", "6hrs"
    m2 = re.search(r'\b(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b', t)
    if m2:
        v = float(m2.group(1))
        return str(int(v)) if v.is_integer() else str(round(v, 2))

    # pattern: contiguous like "6hours" without space
    m3 = re.search(r'\b(\d+(?:\.\d+)?)hours\b', t)
    if m3:
        v = float(m3.group(1))
        return str(int(v)) if v.is_integer() else str(round(v, 2))

    # word numbers fallback for common words (one..twenty)
    words_map = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
        "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
        "nineteen": 19, "twenty": 20
    }
    for word, num in words_map.items():
        if re.search(r'\b' + re.escape(word) + r'\b', t) and re.search(r'\bhours?\b|\bhrs?\b|\bh\b', t):
            return str(num)

    return None

def sanitize_passenger_name(name: str) -> str:
    """
    Remove common lead-in phrases from a spoken/text name like:
      "Hi, I'm John Doe", "Hello my name is Jane", "I'm Alice"
    and return a cleaned, title-cased name ("John Doe").
    """
    if not name:
        return name
    s = name.strip()
    # remove common greetings at the start
    s = re.sub(r'^(?:hi|hello|hey|hiya|greetings|good morning|good afternoon)[\s,!.:-]*', '', s, flags=re.I)
    # remove leading "I'm", "I am", "Im", "I’m", "my name is", "name is", "this is"
    s = re.sub(r'^(?:i\'?m|i am|im|my name is|name is|this is|it is)[\s,:-]*', '', s, flags=re.I)
    # remove any leading "my name's" or "my name" variants
    s = re.sub(r'^(?:my name(?:\'s)?)[\s,:-]*', '', s, flags=re.I)
    # strip surrounding punctuation and whitespace
    s = s.strip(" .,!?:;\"'()[]")
    # collapse multiple spaces
    s = re.sub(r'\s+', ' ', s)
    # title-case the name but keep existing capitalization for initials (simple approach)
    parts = [p.capitalize() for p in s.split(' ') if p]
    cleaned = " ".join(parts)
    return cleaned

# new import of shared helpers
from .helpers import CLAIM_FIELDS, quick_pattern_extract

# env
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
#ELEVEN_STT_MODEL = os.getenv("ELEVEN_STT_MODEL", "large")  # adapt if needed
ELEVEN_STT_MODEL = os.getenv("ELEVEN_STT_MODEL", "scribe_v1")  # default to supported ElevenLabs STT model
# back-compat for old/legacy values
if ELEVEN_STT_MODEL and ELEVEN_STT_MODEL.lower() in ("large", "large-v1", "large_v1"):
    ELEVEN_STT_MODEL = "scribe_v1"
ELEVEN_VOICE_ID = os.getenv("ELEVEN_VOICE_ID")

ZOHO_ENABLED = bool(os.getenv("ZOHO_CLIENT_ID") and os.getenv("ZOHO_CLIENT_SECRET") and os.getenv("ZOHO_REFRESH_TOKEN"))

app = FastAPI(title="E261 voice backend API")

# Enable CORS for frontend during development
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment-aware configuration
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')
BACKEND_URL = os.getenv('BACKEND_URL', 'http://127.0.0.1:8000')

# CORS origins - includes development, production, and GitHub Pages
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://geniusjr001.github.io",
    "https://geniusjr001.github.io/E261",
    "https://github.com",
    "https://*.github.io",
    "*",  # Temporarily allow all origins for debugging
    FRONTEND_URL,  # Environment-specific URL
]

# Remove duplicates and None values
origins = list(set(filter(None, origins)))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Temporarily allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prefer React build from voice-intake/dist if present, else old frontend
react_build_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "voice-intake", "dist"))
html_frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "voice_intake script", "frontend"))

# Serve React build under /app to avoid static mount capturing POST requests for API routes.
if os.path.isdir(react_build_path):
    app.mount("/app", StaticFiles(directory=react_build_path), name="react_app")
    index_file = os.path.join(react_build_path, "index.html")
    if os.path.isfile(index_file):
        @app.get("/", include_in_schema=False)
        def serve_react_index():
            # serve index for browser GETs at root, keep API routes free for POST/PUT/DELETE
            return FileResponse(index_file)
elif os.path.isdir(html_frontend_path):
    app.mount("/frontend", StaticFiles(directory=html_frontend_path), name="frontend")
    index_file = os.path.join(html_frontend_path, "voice_ui.html")
    if os.path.isfile(index_file):
        @app.get("/", include_in_schema=False)
        def serve_voice_ui():
            return FileResponse(index_file)
else:
    @app.get("/", include_in_schema=False)
    def root_placeholder():
        return {"status": "backend running - no frontend found. Put your frontend in 'voice_intake script/frontend' or build React into 'voice-intake/dist'."}

class ClaimPayload(BaseModel):
    data: Dict[str, str]

@app.get("/health")
def health():
    return {
        "status": "ok",
        "python_version": platform.python_version(),
        "fastapi_version": fastapi.__version__,
        "pydantic_version": pydantic.__version__,
        "environment": {
            "eleven_api_configured": bool(ELEVEN_API_KEY),
            "eleven_voice_configured": bool(ELEVEN_VOICE_ID),
            "eleven_api_key_length": len(ELEVEN_API_KEY) if ELEVEN_API_KEY else 0,
            "eleven_voice_id_length": len(ELEVEN_VOICE_ID) if ELEVEN_VOICE_ID else 0,
            "zoho_enabled": ZOHO_ENABLED,
            "frontend_url": FRONTEND_URL,
            "backend_url": BACKEND_URL
        }
    }

@app.get("/debug-env")
def debug_env():
    """Debug endpoint to check environment variables"""
    return {
        "eleven_api_key_present": bool(ELEVEN_API_KEY),
        "eleven_api_key_length": len(ELEVEN_API_KEY) if ELEVEN_API_KEY else 0,
        "eleven_voice_id_present": bool(ELEVEN_VOICE_ID),
        "eleven_voice_id_value": ELEVEN_VOICE_ID if ELEVEN_VOICE_ID else "None",
        "environment_vars": {
            "ELEVEN_API_KEY": "SET" if os.getenv("ELEVEN_API_KEY") else "NOT_SET",
            "ELEVEN_VOICE_ID": "SET" if os.getenv("ELEVEN_VOICE_ID") else "NOT_SET",
        }
    }

def _maybe_transcode_to_wav(src_path):
    """
    If src_path is not WAV, try to transcode to WAV using ffmpeg.
    Returns path_to_send (may be src_path if no transcode), and a flag whether we should remove it after send.
    """
    ext = os.path.splitext(src_path)[1].lower()
    if ext in ('.wav', '.pcm'):
        return src_path, False
    # preferred output WAV path
    out = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    out_path = out.name
    out.close()
    try:
        # Use ffmpeg to convert to 16k mono WAV (ElevenLabs likes WAV)
        subprocess.run([
            'ffmpeg', '-y', '-i', src_path,
            '-ar', '16000', '-ac', '1', out_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out_path, True
    except Exception as e:
        # ffmpeg not available or conversion failed; fall back to original file
        try:
            if os.path.exists(out_path):
                os.unlink(out_path)
        except Exception:
            pass
        print("Warning: ffmpeg transcode failed or not available:", e)
        return src_path, False

# ---- patch /stt handler ----
@app.post("/stt")
def stt(file: UploadFile = File(...)):
    """
    Accept multipart file, forward to ElevenLabs STT, return {"text": "..."}
    """
    if not ELEVEN_API_KEY:
        raise HTTPException(status_code=500, detail="ELEVEN_API_KEY not set")

    suffix = os.path.splitext(file.filename)[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    send_path = tmp_path
    remove_send = False
    try:
        # try transcode if needed (webm/ogg/mp4/m4a etc.)
        send_path, remove_send = _maybe_transcode_to_wav(tmp_path)

        url = "https://api.elevenlabs.io/v1/speech-to-text"
        headers = {"xi-api-key": ELEVEN_API_KEY, "Accept": "application/json"}
        with open(send_path, "rb") as fh:
            # set content-type according to file ext
            ctype = mimetypes.guess_type(send_path)[0] or "application/octet-stream"
            files = {"file": (os.path.basename(send_path), fh, ctype)}
            data = {"model_id": ELEVEN_STT_MODEL}
            resp = requests.post(url, headers=headers, files=files, data=data, timeout=30)

        if resp.status_code >= 400:
            # log body for debugging
            print("ElevenLabs STT error:", resp.status_code, resp.text)
            raise HTTPException(status_code=502, detail={"eleven_error": resp.text, "status": resp.status_code})

        body = resp.json()
        text = (
            body.get("text")
            or body.get("transcript")
            or body.get("transcription")
            or (body.get("results") and body["results"][0].get("text"))
            or ""
        )
        return {"text": text.strip()}
    finally:
        # cleanup temps
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception:
            pass
        try:
            if remove_send and send_path and os.path.exists(send_path):
                os.unlink(send_path)
        except Exception:
            pass

# Simple in-memory cache for TTS audio
TTS_CACHE = {}

def cached_tts(text: str) -> bytes:
    """
    TTS with simple caching. Returns audio bytes.
    Cache key is MD5 hash of text.
    """
    print(f"[cached_tts] Starting TTS for text: {text[:50]}...")  # Debug logging
    try:
        # Create cache key
        text_hash = hashlib.md5(text.encode()).hexdigest()
        print(f"[cached_tts] Text hash: {text_hash}")  # Debug logging
        
        # Check cache first
        if text_hash in TTS_CACHE:
            print(f"[cached_tts] Cache hit! Returning cached audio")  # Debug logging
            return TTS_CACHE[text_hash]
        
        # Check environment variables
        if not ELEVEN_API_KEY or not ELEVEN_VOICE_ID:
            print(f"[cached_tts] Missing env vars - API Key: {bool(ELEVEN_API_KEY)}, Voice ID: {bool(ELEVEN_VOICE_ID)}")
            raise HTTPException(status_code=500, detail="ELEVEN_API_KEY or ELEVEN_VOICE_ID not set")
        
        print(f"[cached_tts] Making API call to ElevenLabs...")  # Debug logging
        
        # Make API call to ElevenLabs
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}/stream"
        headers = {
            "xi-api-key": ELEVEN_API_KEY,
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
        }
        body = {"text": text, "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
        
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        
        print(f"[cached_tts] ElevenLabs response: {resp.status_code}")  # Debug logging
        
        if resp.status_code != 200:
            print(f"[cached_tts] ElevenLabs error: {resp.text}")  # Debug logging
            error_detail = {
                "eleven_error": resp.text,
                "status_code": resp.status_code,
                "url": url
            }
            raise HTTPException(status_code=502, detail=error_detail)
        
        audio_bytes = resp.content
        print(f"[cached_tts] Received audio: {len(audio_bytes)} bytes")  # Debug logging
        
        # Cache the result (simple cache, consider size limits in production)
        TTS_CACHE[text_hash] = audio_bytes
        
        return audio_bytes
        
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        print(f"[cached_tts] Unexpected error: {str(e)}")  # Debug logging
        # Catch any other unexpected errors
        import traceback
        error_detail = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        raise HTTPException(status_code=500, detail=error_detail)

@app.post("/tts")
def tts(payload: dict):
    """
    Text-to-speech endpoint.
    Expects JSON: {"text": "your text here"}
    Returns: audio/mpeg stream
    """
    print(f"[TTS] Endpoint called with payload: {payload}")  # Debug logging
    try:
        text = payload.get("text", "").strip()
        if not text:
            print("[TTS] Error: Empty text provided")
            raise HTTPException(status_code=400, detail="missing text")
        
        print(f"[TTS] Processing text: {text[:50]}...")  # Debug logging
        
        # Call cached TTS function
        audio_bytes = cached_tts(text)
        
        print(f"[TTS] Successfully generated audio: {len(audio_bytes)} bytes")  # Debug logging
        
        return StreamingResponse(iter([audio_bytes]), media_type="audio/mpeg")
        
    except HTTPException as he:
        print(f"[TTS] HTTPException: {he.detail}")  # Debug logging
        # Re-raise HTTPExceptions from cached_tts
        raise
    except Exception as e:
        print(f"[TTS] Unexpected error: {str(e)}")  # Debug logging
        # Catch any other unexpected errors
        import traceback
        error_detail = {
            "error": f"TTS endpoint error: {str(e)}",
            "traceback": traceback.format_exc()
        }
        raise HTTPException(status_code=500, detail=error_detail)

@app.post("/submit-claim")
def submit_claim(payload: ClaimPayload):
    """
    Receive structured claim data: payload.data (mapping of field API names or friendly names).
    Creates/updates contact and creates claim. Returns ids.
    """
    if not ZOHO_ENABLED:
        raise HTTPException(status_code=500, detail="Zoho env vars not set")

    # lazy import so server still starts without Zoho env set
    from .zoho_client import ZohoCRM

    zoho = ZohoCRM()
    data = payload.data

    # map to Zoho contact fields if available
    contact_payload = {}
    if email := data.get("Contact Email"):
        contact_payload["Email"] = email
        # first/last heuristics
        name = data.get("Passenger Name", "").strip()
        if name:
            parts = name.split()
            contact_payload["First_Name"] = parts[0]
            contact_payload["Last_Name"] = parts[-1] if len(parts) > 1 else parts[0]

    try:
        contact_id = zoho.create_or_update_contact(contact_payload) if contact_payload else None
        # prepare claim data - keys must match Zoho field API names; assume frontend uses API names
        claim_api_payload = {k: v for k, v in data.items() if v is not None}
        if contact_id:
            claim_api_payload["Contact_Name"] = contact_id
        claim_id = zoho.create_claim(claim_api_payload, module_name=data.get("module_name", "Claims"))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"contact_id": contact_id, "claim_id": claim_id}

# simple in-memory sessions: session_id -> collected dict
_sessions: Dict[str, Dict[str, Optional[str]]] = {}

# allow importing prompts from scripts safely (optional)
main_convo = None
scripts_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if os.path.exists(scripts_path):
    sys.path.insert(0, scripts_path)

try:
    from . import main_convo
except ImportError as e:
    print(f"Warning: main_convo module not found: {e}")
    main_convo = None
except Exception as e:
    print(f"Error importing main_convo: {e}")
    main_convo = None

@app.post("/conversation/start")
def conversation_start():
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {k: None for k in CLAIM_FIELDS}
    _sessions[session_id]["claim_status_step"] = 0

    # Use main_convo if available, otherwise fallback to hardcoded
    if main_convo:
        initial_prompt = main_convo.get_initial_prompt()
        timeout = main_convo.get_timeout("open_ended")
    else:
        # Fallback to hardcoded values
        intro_line = (
        "Hi, welcome to 261 Claims. I understand how frustrating flight delays can be, "
        "and I’m here to help you resolve it. Let’s get started."
        )
        open_ended = (
        "Can you explain what really happened? You can include as many details as you want, "
        "such as your name, flight number, airline, and the delay duration."
        )
        initial_prompt = f"{intro_line} {open_ended}"
        timeout = 10000

    return {"session_id": session_id, "prompt": initial_prompt, "silence_timeout": timeout}

@app.post("/conversation/respond")
async def conversation_respond(session_id: str, request: Request, file: UploadFile | None = File(None), payload: dict | str | None = Body(None)):
    try:
        if session_id not in _sessions:
            raise HTTPException(status_code=400, detail="invalid session_id")

        try:
            print(f"DEBUG /conversation/respond called session_id={session_id} file_present={bool(file)} payload_type={type(payload).__name__}")
        except Exception:
            pass

        # Normalize incoming text (payload dict/string, JSON body, or raw body)
        user_text = None
        if payload is not None:
            if isinstance(payload, dict):
                user_text = (payload.get("text") or "").strip()
            elif isinstance(payload, str):
                user_text = payload.strip()

        if user_text is None:
            try:
                j = await request.json()
                if isinstance(j, dict) and "text" in j:
                    user_text = (j.get("text") or "").strip()
                elif isinstance(j, str):
                    user_text = j.strip()
            except Exception:
                try:
                    raw = (await request.body()).decode("utf-8", errors="ignore").strip()
                    if raw:
                        try:
                            import json
                            parsed = json.loads(raw)
                            if isinstance(parsed, dict) and "text" in parsed:
                                user_text = (parsed.get("text") or "").strip()
                            elif isinstance(parsed, str):
                                user_text = parsed.strip()
                        except Exception:
                            user_text = raw
                except Exception:
                    user_text = None

        # --- NEW: normalize common noisy transcripts before extraction ---
        if user_text:
            # collapse immediate duplicated words: "my my" -> "my"
            user_text = re.sub(r'\b(\w+)(?:\s+\1\b)+', r'\1', user_text, flags=re.I)

            # collapse sequences of single letters separated by spaces into contiguous letters:
            # e.g. "b a" -> "ba", "b a 5 6" -> "ba56", "5 6 5 7" -> "5657"
            def _collapse_spaced_sequences(s: str) -> str:
                # letter groups of 2+ single-letter tokens -> join
                s = re.sub(r'\b(?:(?:[A-Za-z])\s+){1,}[A-ZaZ]\b',
                           lambda m: m.group(0).replace(' ', ''), s)
                # letter group followed by digits: "b a 123" -> "ba123"
                s = re.sub(r'\b((?:[A-ZaZ]\s+)+[A-ZaZ])\s+(\d+)\b',
                           lambda m: m.group(1).replace(' ', '') + m.group(2), s)
                # sequences of spaced digits -> join "5 6 5 7" -> "5657"
                s = re.sub(r'\b(\d(?:\s+\d){1,})\b', lambda m: m.group(0).replace(' ', ''), s)
                return s

            user_text = _collapse_spaced_sequences(user_text)
            # trim extra whitespace
            user_text = re.sub(r'\s+', ' ', user_text).strip()
        # If no text and file present, run STT (ElevenLabs)
        if user_text is None and file is not None:
            if not ELEVEN_API_KEY:
                raise HTTPException(status_code=500, detail="ELEVEN_API_KEY not set")
            suffix = os.path.splitext(file.filename)[1] or ".wav"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name

            send_path = tmp_path
            remove_send = False
            try:
                send_path, remove_send = _maybe_transcode_to_wav(tmp_path)
                url = "https://api.elevenlabs.io/v1/speech-to-text"
                headers = {"xi-api-key": ELEVEN_API_KEY, "Accept": "application/json"}
                with open(send_path, "rb") as fh:
                    ctype = mimetypes.guess_type(send_path)[0] or "application/octet-stream"
                    files = {"file": (os.path.basename(send_path), fh, ctype)}
                    data = {"model_id": ELEVEN_STT_MODEL}
                    resp = requests.post(url, headers=headers, files=files, data=data, timeout=30)
                if resp.status_code >= 400:
                    print("ElevenLabs STT error (respond):", resp.status_code, resp.text)
                    raise HTTPException(status_code=502, detail={"eleven_error": resp.text, "status": resp.status_code})
                body = resp.json()
                user_text = (body.get("text") or body.get("transcript") or "").strip()
            finally:
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                except Exception:
                    pass
                try:
                    if remove_send and send_path and os.path.exists(send_path):
                        os.unlink(send_path)
                except Exception:
                    pass

        collected = _sessions[session_id]
        prev_collected = dict(collected)

        # If still no text, ask user to repeat (short-circuit)
        if not user_text:
            hint = "I didn't catch that — could you repeat your response? You also can use the text bar."
            next_field = next((k for k, v in collected.items() if v is None), None)
            if next_field:
                next_prompt = f"{hint} (I'm asking for: {next_field})"
            else:
                next_prompt = hint
            return {"session_id": session_id, "next_prompt": next_prompt, "collected": collected, "done": False, "silence_timeout": 2500}

        # --- Extraction logic ---

        # Passenger Name
        if not collected.get("Passenger Name"):
            m = re.search(r'\b(?:my name is|name is|i am|i\'m|im)\s+([A-Za-z][A-ZaZ\s\'\-]{0,80})', user_text, re.I)
            if m:
                name = sanitize_passenger_name(m.group(1))
                if name:
                    collected["Passenger Name"] = name

        # Contact Email
        if not collected.get("Contact Email"):
            m = re.search(r'([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})', user_text)
            if m:
                candidate = m.group(1).strip().strip('.,;:!?)("\'')
                collected["Contact Email"] = candidate

        # Flight Number
        if not collected.get("Flight Number"):
            m = re.search(r'\b([A-Za-z]{1,3}(?:\s+[A-Za-z]{1,3})*)\s*(\d{1,6})\b', user_text)
            if m:
                letters = re.sub(r'\s+', '', m.group(1)).upper()
                numbers = m.group(2)
                fn = letters + numbers
                if re.match(r'^[A-Z]{1,4}\d+$', fn):
                    collected["Flight Number"] = fn
            else:
                m2 = re.search(r'\bflight\b[^A-Za-z0-9]*([A-Za-z]+)\s*(\d+)\b', user_text, re.I)
                if m2:
                    letters = re.sub(r'\s+', '', m2.group(1)).upper()
                    numbers = m2.group(2)
                    fn = letters + numbers
                    if re.match(r'^[A-Z]{1,4}\d+$', fn):
                        collected["Flight Number"] = fn

        # Flight Date
        if not collected.get("Flight Date"):
            date_str = parse_date_from_text(user_text)
            if date_str:
                collected["Flight Date"] = date_str

        # Airline
        if not collected.get("Airline"):
            m = re.search(r'\b(?:flying with|airline|on)\s+([A-Za-z][A-ZaZ\s]{0,80})', user_text, re.I)
            if m:
                airline = m.group(1).strip()
                collected["Airline"] = airline.title()
        if not collected.get("Airline") and user_text:
            s = user_text.strip()

            # ignore pure filler/noise
            filler = {"", "um", "uh", "yeah", "no", "always", "airline", "i don't know", "dont know", "i dunno"}
            if s.lower() not in filler:
                # remove common lead-in prepositions/phrases ("to", "on", "with", etc.)
                s = re.sub(r'^\s*(?:to|on|with|the|i was flying with|i flew with|flying with|flight with)\s+', '', s, flags=re.I)

                # trim punctuation/extra whitespace
                s = s.strip(" .,!?:;\"'()[]")
                s = re.sub(r'\s+', ' ', s).strip()

                # collapse duplicated words ("British British Airways")
                s = re.sub(r'\b(\w+)(?:\s+\1\b)+', r'\1', s, flags=re.I)

                # Title-case tokens
                parts = [p.capitalize() for p in s.split() if p]
                normalized = " ".join(parts)

                # Require the airline string to include either "airways" or "airline" (accept "airlines")
                if re.search(r'\b(?:airways|airline|airlines|always)\b', normalized, flags=re.I):
                    collected["Airline"] = normalized
                    newly_filled = True
                    next_field = next((k for k, v in collected.items() if v is None), None)

        # Departure Airport
        if not collected.get("Departure Airport"):
            m_air = re.search(r'\b([A-Za-z][A-ZaZ \-]{1,80}?)\s+airport\b', user_text, re.I)
            if m_air:
                name = m_air.group(1).strip()
                parts = [p.capitalize() for p in re.sub(r'[\-]+', ' ', name).split() if p]
                collected["Departure Airport"] = " ".join(parts) + " Airport"
            else:
                m_from = re.search(r'\b(?:from|depart(?:ed)?\s+from)\s+([A-Za-z][A-ZaZ \-]{1,80}?)\b', user_text, re.I)
                if m_from:
                    name = m_from.group(1).strip()
                    parts = [p.capitalize() for p in re.sub(r'[\-]+', ' ', name).split() if p]
                    collected["Departure Airport"] = " ".join(parts) + " Airport"
                else:
                    m_iata = re.search(r'\b(?:from|depart(?:ed)?\s+from)\s+([A-Za-z]{3})\b', user_text, re.I)
                    if m_iata:
                        collected["Departure Airport"] = m_iata.group(1).upper()

        # Arrival Airport
        if not collected.get("Arrival Airport"):
            m_air = re.search(r'\b([A-Za-z][A-ZaZ \-]{1,80}?)\s+airport\b', user_text, re.I)
            if m_air:
                name = m_air.group(1).strip()
                parts = [p.capitalize() for p in re.sub(r'[\-]+', ' ', name).split() if p]
                collected["Arrival Airport"] = " ".join(parts) + " Airport"
            else:
                m_to = re.search(r'\b(?:to|arriv(?:ed|ing)?\s+(?:at|in))\s+([A-Za-z][A-ZaZ \-]{1,80}?)\b', user_text, re.I)
                if m_to:
                    name = m_to.group(1).strip()
                    parts = [p.capitalize() for p in re.sub(r'[\-]+', ' ', name).split() if p]
                    collected["Arrival Airport"] = " ".join(parts) + " Airport"
                else:
                    m_iata = re.search(r'\b(?:to|arriv(?:ed|ing)?\s+(?:at|in))\s+([A-Za-z]{3})\b', user_text, re.I)
                    if m_iata:
                        collected["Arrival Airport"] = m_iata.group(1).upper()

        # Delay Hours
        if not collected.get("Delay Hours"):
            delay_str = parse_delay_hours(user_text)
            if delay_str:
                collected["Delay Hours"] = delay_str

        # Airline Response
        if not collected.get("Airline Response"):
            m = re.search(r'\b(?:airline|they)\s+(?:said|responded|offered)\s+(.{10,200})', user_text, re.I)
            if m:
                resp = m.group(1).strip()
                collected["Airline Response"] = resp

        # Email validation
        email_invalid = False
        if collected.get("Contact Email") and not re.match(r'^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$', collected["Contact Email"]):
            email_invalid = True
            collected["Contact Email"] = None

        # Determine newly filled and next field
        newly_filled = any(collected.get(k) != prev_collected.get(k) for k in CLAIM_FIELDS)
        next_field = next((k for k, v in collected.items() if v is None), None)

        # If we are asking "What did the airline say about your claim?",
        # accept any user sentence as the Airline Response (no regex required).
        if next_field == "Airline Response" and user_text:
            collected["Airline Response"] = user_text.strip()
            newly_filled = True
            # advance next_field to the next missing item
            next_field = next((k for k, v in collected.items() if v is None), None)

        # If we are asking for the flight number, accept many noisy spoken forms:
        # - contiguous tokens with letters+digits (e.g. "BA123")
        # - separated letters and digits ("b a 1 2 3" or "ba 123")
        # - spaced digits collapsed ("5 7 5 7 5 7 2")
        if next_field == "Flight Number" and user_text:
            s = re.sub(r'[^\w\s]', ' ', user_text)        # remove punctuation
            s = re.sub(r'\s+', ' ', s).strip()

            # 1) token containing both letters and digits (best match)
            tokens = re.findall(r'\b(?=\w*[A-Za-z])(?=\w*\d)\w+\b', s, flags=re.I)
            found_fn = None
            for t in tokens:
                letters = re.sub(r'[^A-Za-z]', '', t).upper()
                digits = re.sub(r'[^0-9]', '', t)
                if letters and digits:
                    candidate = letters + digits
                    # basic sanity: letters 1-4, digits 1-6
                    if 1 <= len(letters) <= 4 and 1 <= len(digits) <= 6:
                        found_fn = candidate
                        break

            # 2) letter token followed by digit token e.g. "ba 5657"
            if not found_fn:
                m = re.search(r'\b([A-Za-z]{1,4})\b\s+(\d{1,6})\b', s, flags=re.I)
                if m:
                    found_fn = re.sub(r'\s+', '', (m.group(1) + m.group(2))).upper()

            # 3) collapse all spaces and try e.g. "b a 1 2 3" -> "ba123"
            if not found_fn:
                collapsed = re.sub(r'\s+', '', s)
                if re.match(r'^[A-Za-z]{1,4}\d{1,6}$', collapsed, flags=re.I):
                    found_fn = collapsed.upper()

            if found_fn:
                collected["Flight Number"] = found_fn
                newly_filled = True
                next_field = next((k for k, v in collected.items() if v is None), None)

        # Get prompts from main_convo if available, otherwise use hardcoded
        if main_convo:
            prompts = main_convo.FIELD_PROMPTS
        else:
            # Fallback to hardcoded prompts
            prompts = {
                "Passenger Name": "What's your full name as it appears on your ticket?",
                "Contact Email": "It's quite unfair you had to go through all of that, please type in your email address into the text bar, We'll use it to contact you about your claim.",
                "Flight Number": "What's your flight number? It usually looks like BA123.",
                "Flight Date": "When was your flight?",
                "Airline": "Which airline were you flying with?",
                "Departure Airport": "Which airport did you depart from?",
                "Arrival Airport": "Which airport were you supposed to arrive at?",
                "Delay Hours": "About how many hours was your flight delayed?",
                "Airline Response": "What did the airline say about your claim?",
                "Claim Status": "What's the current status of the claim?"
            }

        # Decide next prompt and timeout
        if next_field is None:
            done = True
            if main_convo:
                next_prompt = main_convo.get_completion_message()
                silence_timeout = main_convo.get_timeout("completion")
            else:
                next_prompt = "Thank you. I have all the details. Please wait while I prepare your claim review..."
                silence_timeout = 2500
            return {
                "session_id": session_id, 
                "next_prompt": next_prompt, 
                "collected": collected, 
                "done": done, 
                "silence_timeout": silence_timeout,
                "redirect_url": f"{FRONTEND_URL}/claim-review.html?session_id={session_id}"
            }
        else:
            done = False
            silence_timeout = 2500
            if email_invalid:
                if main_convo:
                    next_prompt = main_convo.get_invalid_email_message()
                else:
                    next_prompt = "That doesn't look like a valid email address. Please provide a valid email (for example: name@example.com)."
            elif next_field == "Claim Status":
                step = collected.get("claim_status_step", 0)
                if main_convo:
                    prompt_result = main_convo.get_claim_status_prompt(step, user_text)
                    if len(prompt_result) == 3:  # completion case
                        next_prompt, new_step, status = prompt_result
                        collected["Claim Status"] = status
                        done = True
                    else:  # continue case
                        next_prompt, new_step = prompt_result
                        if new_step is not None:
                            collected["claim_status_step"] = new_step
                else:
                    # Fallback to hardcoded logic
                    if step == 0:
                        next_prompt = "Have you submitted a claim before?"
                        collected["claim_status_step"] = 1
                    elif step == 1:
                        if "yes" in user_text.lower():
                            next_prompt = "Have you received compensation?"
                            collected["claim_status_step"] = 2
                        elif "no" in user_text.lower():
                            collected["Claim Status"] = "New Claim"
                            done = True
                            next_prompt = "Thank you. I have all the details."
                        else:
                            next_prompt = "Please answer yes or no. Have you submitted a claim before?"
                    elif step == 2:
                        if "yes" in user_text.lower():
                            collected["Claim Status"] = "Resolved"
                            done = True
                            next_prompt = "Thank you. I have all the details."
                        elif "no" in user_text.lower():
                            collected["Claim Status"] = "Pending"
                            done = True
                            next_prompt = "Thank you. I have all the details."
                        else:
                            next_prompt = "Please answer yes or no. Have you received compensation?"
            else:
                if main_convo:
                    next_prompt = main_convo.get_field_prompt(next_field, newly_filled)
                else:
                    # Fallback to hardcoded logic
                    if newly_filled:
                        next_prompt = prompts.get(next_field, f"Could you tell me your {next_field.lower()}?")
                    else:
                        examples = {
                            "Passenger Name": "Please provide your full name as it appears on your ticket (e.g., John Doe).",
                            "Contact Email": "Please provide your email address (for example: name@example.com).",
                            "Flight Number": "Please provide your flight number (for example: BA123).",
                            "Flight Date": "Please provide the date of the flight (Year, Month & Date , an example is., 2023, July 15th).",
                            "Airline": "Please provide the airline name (for example: British Airways).",
                            "Departure Airport": "Please provide the departure airport (for example: London Heathrow).",
                            "Arrival Airport": "Please provide the arrival airport (for example: Amsterdam Schiphol).",
                            "Delay Hours": "Please tell me the delay duration in hours (for example: 3).",
                            "Airline Response": "Please describe how the airline responded (for example: they offered meal vouchers)."
                        }
                        specific = examples.get(next_field)
                        if specific:
                            next_prompt = f"Sorry, I didn't catch that. {specific} You also can use the text bar."
                        else:
                            next_prompt = f"Could you please provide your {next_field.lower()}?"

        # Set timeout if not already set
        if 'silence_timeout' not in locals():
            if main_convo:
                silence_timeout = main_convo.get_timeout("standard")
            else:
                silence_timeout = 2500

        # persist session
        _sessions[session_id] = collected

        return {"session_id": session_id, "next_prompt": next_prompt, "collected": collected, "done": done, "silence_timeout": silence_timeout}

    except Exception as e:
        print(f"Error in conversation_respond: {e}")
        traceback.print_exc()
        if main_convo:
            error_message = main_convo.get_error_message()
            timeout = main_convo.get_timeout("standard")
        else:
            error_message = "An error occurred. Please try again."
            timeout = 2500
        return {"error": str(e), "session_id": session_id, "next_prompt": error_message, "collected": {}, "done": False, "silence_timeout": timeout}

@app.get("/claim-review/{session_id}")
def get_claim_review(session_id: str):
    """
    Retrieve collected data for the claim review page
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    collected = _sessions[session_id]
    # Remove internal tracking fields
    clean_data = {k: v for k, v in collected.items() if not k.startswith('claim_status_step')}
    
    return {
        "session_id": session_id,
        "collected_data": clean_data,
        "status": "ready_for_review"
    }

@app.post("/upload-document/{session_id}")
async def upload_document(
    session_id: str,
    file: UploadFile = File(...),
    document_type: str = Form(...)
):
    """
    Handle document uploads (passport, tickets, etc.)
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Validate file type
    allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.gif'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: PDF, JPG, PNG, GIF")
    
    # Validate file size (10MB limit)
    max_size = 10 * 1024 * 1024  # 10MB
    file_content = await file.read()
    if len(file_content) > max_size:
        raise HTTPException(status_code=400, detail="File too large. Maximum size: 10MB")
    
    # Create uploads directory if it doesn't exist
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads", session_id)
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{document_type}_{timestamp}{file_ext}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # Store file info in session
    if 'uploaded_documents' not in _sessions[session_id]:
        _sessions[session_id]['uploaded_documents'] = []
    
    _sessions[session_id]['uploaded_documents'].append({
        "filename": safe_filename,
        "original_name": file.filename,
        "document_type": document_type,
        "file_path": file_path,
        "upload_time": timestamp,
        "file_size": len(file_content)
    })
    
    return {
        "message": "File uploaded successfully",
        "filename": safe_filename,
        "document_type": document_type
    }

@app.get("/documents/{session_id}")
def get_uploaded_documents(session_id: str):
    """
    Get list of uploaded documents for a session
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    documents = _sessions[session_id].get('uploaded_documents', [])
    return {"documents": documents}

@app.delete("/document/{session_id}/{filename}")
def delete_document(session_id: str, filename: str):
    """
    Delete an uploaded document
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    documents = _sessions[session_id].get('uploaded_documents', [])
    doc_to_remove = None
    
    for doc in documents:
        if doc['filename'] == filename:
            doc_to_remove = doc
            break
    
    if not doc_to_remove:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Remove file from filesystem
    try:
        if os.path.exists(doc_to_remove['file_path']):
            os.unlink(doc_to_remove['file_path'])
    except Exception as e:
        print(f"Error deleting file: {e}")
    
    # Remove from session
    documents.remove(doc_to_remove)
    
    return {"message": "Document deleted successfully"}

@app.post("/claim-submit-final")
async def submit_final_claim(request: Request):
    """
    Accept final claim data with documents and send to Zoro CRM
    """
    try:
        data = await request.json()
        session_id = data.get("session_id")
        
        if not session_id or session_id not in _sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get collected data and any updates from form
        session_data = _sessions[session_id]
        updated_data = data.get("claim_data", {})
        
        # Merge session data with form updates
        final_data = {**session_data, **updated_data}
        
        # Remove internal fields
        clean_data = {k: v for k, v in final_data.items() 
                     if not k.startswith('claim_status_step') and k != 'uploaded_documents'}
        
        # Get uploaded documents
        documents = session_data.get('uploaded_documents', [])
        
        if not ZOHO_ENABLED:
            # For testing without Zoho, just return success
            return {
                "success": True,
                "message": "Claim submitted successfully (test mode)",
                "claim_id": f"TEST_{session_id[:8]}",
                "documents_count": len(documents)
            }
        
        # Submit to Zoro CRM
        from .zoho_client import ZohoCRM
        zoho = ZohoCRM()
        
        # Create contact
        contact_payload = {}
        if email := clean_data.get("Contact Email"):
            contact_payload["Email"] = email
            name = clean_data.get("Passenger Name", "").strip()
            if name:
                parts = name.split()
                contact_payload["First_Name"] = parts[0]
                contact_payload["Last_Name"] = parts[-1] if len(parts) > 1 else parts[0]
        
        contact_id = zoho.create_or_update_contact(contact_payload) if contact_payload else None
        
        # Create claim
        claim_payload = {k: v for k, v in clean_data.items() if v is not None}
        if contact_id:
            claim_payload["Contact_Name"] = contact_id
        
        claim_id = zoho.create_claim(claim_payload)
        
        # TODO: Upload documents to Zoho (if API supports it)
        # For now, documents are stored locally
        
        # Clean up session
        del _sessions[session_id]
        
        return {
            "success": True,
            "message": "Claim submitted successfully",
            "claim_id": claim_id,
            "contact_id": contact_id,
            "documents_count": len(documents)
        }
        
    except Exception as e:
        print(f"Error submitting final claim: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
