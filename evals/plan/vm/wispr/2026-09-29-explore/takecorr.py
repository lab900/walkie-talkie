"""takecorr.py TAKE SOURCE — does the kept take carry the source clip after an event? Envelope (20 ms RMS)
correlation of the take's 1 s windows against the source at the best lag found on the take's first 3 s."""
import sys, wave, numpy as np
from scipy.signal import resample_poly
def rd(p):
    w = wave.open(p); sr = w.getframerate(); ch = w.getnchannels()
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, ch)[:, 0].astype(np.float32)
    return (resample_poly(a, 16000, sr) if sr != 16000 else a)
def env(a, hop=320): return np.array([np.sqrt((a[i:i+hop]**2).mean()) for i in range(0, len(a) - hop, hop)])
t, s = env(rd(sys.argv[1])), env(rd(sys.argv[2]))
best = max(range(-100, 150), key=lambda L: np.corrcoef(t[max(0,L):max(0,L)+150], s[max(0,-L):max(0,-L)+150][:len(t[max(0,L):max(0,L)+150])])[0,1] if L < len(t) - 150 else -1)
out = []
for k in range(0, len(t) // 50):
    a = t[k*50:(k+1)*50]; i = k*50 - best
    if i < 0 or i + 50 > len(s): out.append("-"); continue
    b = s[i:i+50]
    out.append("%.2f" % (np.corrcoef(a, b)[0, 1] if a.std() > 0 and b.std() > 0 else 0))
print("lag %d frames (%.2f s); per-second corr:" % (best, best * 0.02), " ".join(out))
