"""takeprofile.py WAV — peak per 0.5 s window of a kept take (were the seconds after an event zeros?)."""
import sys, wave, numpy as np
w = wave.open(sys.argv[1]); sr = w.getframerate(); ch = w.getnchannels()
a = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, ch)[:, 0]
n = int(sr * 0.5)
print(sys.argv[1].split("/")[-1], "%.1f s" % (len(a) / sr), " ".join("%d" % np.abs(a[i:i + n]).max() for i in range(0, len(a), n)))
