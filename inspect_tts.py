from pathlib import Path
p=Path('tts_debug.bin')
if not p.exists():
    print('MISSING', p)
    raise SystemExit(2)
b=p.read_bytes()
print('size=', len(b))
print('first 64 bytes hex=', b[:64].hex())
print('first 32 bytes raw=', b[:32])
try:
    import wave, io, struct
    with io.BytesIO(b) as fh:
        try:
            w=wave.open(fh,'rb')
            print('WAV detected: channels=', w.getnchannels(), 'rate=', w.getframerate(), 'frames=', w.getnframes(), 'sampwidth=', w.getsampwidth())
            w.close()
        except wave.Error:
            print('Not a WAV or wave.Error')
except Exception:
    pass
