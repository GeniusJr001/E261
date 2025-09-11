import wave, sys, struct, math
path = sys.argv[1] if len(sys.argv)>1 else "eleven_direct_test.wav"
with wave.open(path,"rb") as wf:
    nframes = wf.getnframes()
    fr = wf.getframerate()
    nch = wf.getnchannels()
    sampw = wf.getsampwidth()
    duration = nframes / fr
    print("path:", path)
    print("frames:", nframes, "rate:", fr, "channels:", nch, "sampwidth:", sampw, "duration(s):", duration)
    # read a chunk to compute peak
    wf.rewind()
    frames = wf.readframes(min(nframes, fr*5))  # inspect up to 5s
    if sampw==2:
        vals = struct.unpack("<" + "h"*(len(frames)//2), frames)
    elif sampw==1:
        vals = struct.unpack("<" + "B"*(len(frames)), frames)
    else:
        vals = []
    peak = max((abs(x) for x in vals), default=0)
    rms = math.sqrt(sum((x*x for x in vals), 0)/len(vals)) if vals else 0
    print("peak:", peak, "rms:", rms)