"""latency.py RELAY_LOG SINCE [UNTIL] — per-sentence time-to-text from the guest relay.log (wave 3).
A sentence opens on 'opening the dictation on the gesture' (or a /test/wispr-chord start); its
time-to-text is the app's own 'the words landed: routed to … — N ms after the microphone closed'.
The source: 'via Wispr's History row' = wispr row; 'transcribed on this Mac instead' = local fallback (Q14).
Also the local decode time ('decode rate [whisper-local]: As audio → Bs') and the 📦 delivery via."""
import re, sys, statistics as st
since, until = sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "99")
L = [l.rstrip("\n") for l in open(sys.argv[1], errors="replace") if since <= l[:14] < until]
sents, cur = [], None
for l in L:
    t = l[:14]
    if "opening the dictation on the gesture" in l or ("wispr-chord" in l and "state: start" in l and "POST" in l and cur is None):
        kind = "desk" if "/test/wispr-chord" in l else "relay"
        cur = {"t": t, "kind": kind, "src": None, "ms": None, "decode": None, "audio": None, "via": None, "fail": None}
        sents.append(cur); continue
    if cur is None: continue
    if "via Wispr's History row" in l: cur["src"] = "wispr-row"
    if "transcribed on this Mac instead" in l: cur["src"] = "local-fallback"
    m = re.search(r"decode rate \[whisper-local\]: ([\d.]+)s audio → ([\d.]+)s", l)
    if m: cur["audio"], cur["decode"] = float(m.group(1)), float(m.group(2))
    m = re.search(r"the words landed: routed to .*? — (\d+) ms after the microphone closed", l)
    if m and cur["ms"] is None: cur["ms"] = int(m.group(1))
    m = re.search(r"the words landed: (?!routed)(.*?) — (\d+) ms", l)
    if m and cur["fail"] is None: cur["fail"] = m.group(1)[:50]
    m = re.search(r"📦 delivery: ([\w-]+)", l)
    if m and cur["via"] is None: cur["via"] = m.group(1)
rows = [s for s in sents if s["ms"] is not None]
for s in sents:
    print(s["t"], s["kind"], s["src"] or "-", s["via"] or "-", s["ms"], "decode", s["decode"], "audio", s["audio"], s["fail"] or "")
def summ(name, xs):
    if not xs: print(f"{name}: n=0"); return
    xs = sorted(xs); p = lambda q: xs[min(len(xs)-1, int(q*len(xs)))]
    print(f"{name}: n={len(xs)} min={xs[0]} p50={st.median(xs):.0f} p90={p(0.9)} max={xs[-1]} (ms after mic close)")
rel = [s for s in rows if s["kind"] == "relay"]
summ("wispr-row (relay)", [s["ms"] for s in rel if s["src"] == "wispr-row"])
summ("local-fallback (relay)", [s["ms"] for s in rel if s["src"] == "local-fallback"])
dec = [s["decode"]*1000 for s in sents if s["decode"]]
if dec: print(f"local decode alone: n={len(dec)} p50={st.median(dec):.0f} ms, max={max(dec):.0f} ms")
