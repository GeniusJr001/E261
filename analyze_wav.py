import sys, wave, struct, math, os
if len(sys.argv) < 2:
    print("Usage: python analyze_wav.py <file.wav>")
    sys.exit(1)
fn = sys.argv[1]
if not os.path.exists(fn):
    print("File not found:", fn); sys.exit(2)
with wave.open(fn, 'rb') as wf:
    n = wf.getnframes()
    fr = wf.getframerate()
    ch = wf.getnchannels()
    sw = wf.getsampwidth()
    dur = n / fr if fr else 0.0
    data = wf.readframes(n)
fmt = {1:'B', 2:'h', 4:'i'}.get(sw)
if not fmt:
    print("Unsupported sample width:", sw); sys.exit(3)
vals = struct.unpack("<" + fmt*(len(data)//sw), data)
if ch > 1:
    mono = [sum(vals[i:i+ch])//ch for i in range(0, len(vals), ch)]
else:
    mono = vals
peak = max((abs(x) for x in mono), default=0)
rms = math.sqrt(sum((x*x for x in mono), 0) / len(mono)) if mono else 0.0
print("file:", fn)
print(f"duration_s: {dur:.3f} frames: {n} rate: {fr} channels: {ch} sampwidth: {sw}")
print(f"peak: {peak} rms: {rms:.3f}")