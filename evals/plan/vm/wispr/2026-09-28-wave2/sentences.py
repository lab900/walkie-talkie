"""Per-sentence outcomes from the guest's relay.log (lab wave 2). A sentence opens on
'opening the dictation on the gesture'; outcome lines are matched FIFO to the open sentences
(a /test/cancel goes to the newest). Prints one row per sentence and the counts."""
import re, sys, collections
since, until = sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "99")
lines = [l.rstrip("\n") for l in open(sys.argv[1], errors="replace") if since <= l[:14] < until]
pend, done = [], []
OUT = [(r"✍️ the words landed: routed to", lambda m: "delivered"),
       (r"✍️ the words landed: (.*?) —", lambda m: "failed:" + m.group(1)[:40]),
       (r"voiced on the relay's own recording too: no speech|: no speech$", lambda m: "no-speech"),
       (r"dictation cancelled — [\d.]+s of audio kept", lambda m: "cancel(recover)"),
       (r"dictation cancelled — nothing had been recorded|🗑️ dictation cancelled$", lambda m: "cancel"),
       (r"dictation abandoned", lambda m: "abandoned"),
       (r"kept for Recover|Recover —", lambda m: "recover")]
for l in lines:
    if "opening the dictation on the gesture" in l:
        kind = "desk" if "/test/wispr-chord" in l else "plain" if "🔽 →" in l else "relay"
        pend.append({"t": l[:14], "kind": kind, "voiced": None, "q14": False, "out": None}); continue
    m = re.search(r"([\d.]+) s voiced", l)
    if m and pend: pend[0]["voiced"] = m.group(1); pend[0]["q14"] |= "Q14" in l
    for pat, f in OUT:
        m = re.search(pat, l)
        if m and pend:
            s = pend.pop(-1 if "cancel" in f(m) else 0); s["out"] = f(m); done.append(s); break
done += [dict(p, out="open/unknown") for p in pend]
done.sort(key=lambda s: s["t"])
for s in done: print(s["t"], s["kind"], s["out"], "voiced", s["voiced"], "Q14" if s["q14"] else "")
print(dict(collections.Counter((s["kind"], s["out"].split(":")[0]) for s in done)))
