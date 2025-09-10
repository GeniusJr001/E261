import requests
import tempfile
import time
import os
import sys
import platform
import subprocess
import wave
import struct

# Prefer winsound on Windows for WAV playback (more reliable)
if platform.system() == "Windows":
    try:
        import winsound  # type: ignore
    except Exception:
        winsound = None
else:
    winsound = None

try:
    import pygame
except Exception:
    pygame = None

TTS_URL = "http://127.0.0.1:8000/tts"  # change if server is at different host/port

def _play_wav_windows(path: str):
    if winsound:
        winsound.PlaySound(path, winsound.SND_FILENAME)
    else:
        # fallback to pygame if winsound unavailable
        if not pygame:
            raise RuntimeError("No audio backend available for WAV playback")
        pygame.mixer.init()
        s = pygame.mixer.Sound(path)
        ch = s.play()
        while ch.get_busy():
            time.sleep(0.1)
        pygame.mixer.quit()

def _play_mp3_with_pygame(path: str):
    if not pygame:
        raise RuntimeError("pygame is not installed/available for MP3 playback")
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        # block until finished
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
    finally:
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        try:
            pygame.mixer.quit()
        except Exception:
            pass

def _try_external_player(path: str):
    # Try Windows default shell open (may launch external player)
    if platform.system() == "Windows":
        try:
            os.startfile(path)
            return True
        except Exception:
            pass

    # Try ffplay if available (non-blocking)
    ffplay = shutil.which("ffplay") or shutil.which("ffplay.exe")
    if ffplay:
        try:
            subprocess.Popen(
                [ffplay, "-nodisp", "-autoexit", "-loglevel", "quiet", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            pass

    # Try VLC / cvlc
    vlc = shutil.which("cvlc") or shutil.which("vlc") or shutil.which("vlc.exe")
    if vlc:
        try:
            subprocess.Popen(
                [vlc, "--play-and-exit", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            pass

    return False

def _is_wav_silent(path: str, threshold: int = 1) -> bool:
    """Return True if WAV frames are all zero (silent) or too short to hear."""
    try:
        with wave.open(path, "rb") as wf:
            nframes = wf.getnframes()
            if nframes == 0:
                return True
            frames = wf.readframes(min(nframes, 16000))  # inspect up to 1s
            sampwidth = wf.getsampwidth()
            if sampwidth == 1:
                fmt = f"{len(frames)}B"
            elif sampwidth == 2:
                fmt = f"{len(frames)//2}h"
            else:
                return False
            samples = struct.unpack(fmt, frames)
            # if any sample magnitude exceeds threshold, not silent
            return all(abs(s) <= threshold for s in samples)
    except Exception:
        return False

def play_tts(text: str):
    resp = requests.post(TTS_URL, json={"text": text}, timeout=30)
    print(f"[play_tts] http status: {resp.status_code}")
    content_type = resp.headers.get("content-type", "").lower()
    data = resp.content
    print(f"[play_tts] content-type: {content_type} length: {len(data)} bytes")

    resp.raise_for_status()

    # detect format
    is_wav = data[:4] == b"RIFF" or "wav" in content_type
    is_mp3 = data[:3] == b"ID3" or b"\xff\xfb" in data[:2] or "mpeg" in content_type or "mp3" in content_type

    suffix = ".wav" if is_wav else (".mp3" if is_mp3 else ".wav")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
        tf.write(data)
        temp_path = tf.name

    try:
        # Quick diagnostics: if WAV, check for silence
        if is_wav:
            silent = _is_wav_silent(temp_path)
            print(f"[play_tts] detected WAV; silent={silent}")
            if silent:
                print("[play_tts] Warning: audio appears silent — server likely returned fallback silent WAV. Check ELEVEN_API_KEY/ELEVEN_VOICE_ID and server logs.")
        else:
            print(f"[play_tts] detected MP3 or other ({suffix})")

        if is_wav:
            try:
                _play_wav_windows(temp_path)
                return
            except Exception as e:
                print(f"[play_tts] winsound/pygame WAV playback failed: {e}", file=sys.stderr)

        if is_mp3:
            try:
                _play_mp3_with_pygame(temp_path)
                return
            except Exception as e:
                print(f"[play_tts] pygame MP3 playback failed: {e}", file=sys.stderr)

        # final fallback: open with OS default
        try:
            if platform.system() == "Windows":
                print(f"[play_tts] opening with default app: {temp_path}")
                os.startfile(temp_path)
            else:
                opener = "xdg-open" if platform.system() == "Linux" else "open"
                subprocess.Popen([opener, temp_path])
            time.sleep(1.0)
        except Exception as e:
            print(f"[play_tts] external open failed: {e}", file=sys.stderr)
            raise

    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

if __name__ == "__main__":
    import sys
    import shutil

    if len(sys.argv) > 1:
        text = sys.argv[1]
    else:
        text = "Hello. This is a local pygame TTS test."
    play_tts(text)