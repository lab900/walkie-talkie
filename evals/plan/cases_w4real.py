"""Wave 4 (2026-09-29 night, lab only): the auto fallback to local (p98) against the REAL Wispr Flow
in the guest — the desk cases TA1–TA5 fake the stall; these make it happen.

    TQ1  warm real Wispr, auto ON: 6 relay sentences — the budget line per close, whether it fired, time to words
    TQ2  Wispr SIGKILLed 3 s into a relay sentence (quit mid-sentence) → the relay's own audio, local, once
    TQ3  Wispr SIGSTOPped 0.3 s after the stop for 20 s (a stalled row) → local-auto at the budget, once;
         the row finishing after the thaw is only logged
    TQ4  Wispr not running at the start (killed) → the sentence borrows the local model, Wispr launched by
         the relay for real; then sentences at +2 s and +15 s after Wispr is up: voiced audio, words once

Every sentence logs one `SEC` line: close → words (the app's own `the words landed … N ms after the
microphone closed`), via, the budget and whether it fired — `latency` in the report is read from these.
"""
import re, time
from harness import *
import cases_wispr as cw
from cases_wispr_chaos import (_rig, _unrig, _start_relay, _stop_relay, _play_bg, _wait_end, _after, _fmt,
                               _once, PROC)
from cases_wispr_soak import ref_words, _relaunch_wispr

BUDGET = r"⏱ budget ([\d.]+) s \(p98 of (\d+) samples on ([\w-]+)"
OVER = r"⏱ .+ over budget — ([\d.]+) s since the close"
LANDED = r"the words landed: routed to .*? — (\d+) ms after the microphone closed"


def _auto_on():
    return (post("/test/local-auto", {"on": True, "wisprDown": False, "fakeLaunch": False})[1] or {}).get("localAuto") or {}


def _sec(tag, mark):
    txt = log_since(mark)
    b = re.search(BUDGET, txt)
    o = re.search(OVER, txt)
    l = re.search(LANDED, txt)
    v = re.findall(r"📦 delivery: (\S+)", txt)
    voiced = re.findall(r"([\d.]+) s voiced", txt)
    deaf = "DEAF" in txt
    line = ("SEC %s close→words %s s via %s budget %s (%s samples on %s) fired %s voiced %s%s"
            % (tag, ("%.2f" % (int(l.group(1)) / 1000.0)) if l else "-", ",".join(v) or "-",
               b.group(1) if b else "-", b.group(2) if b else "-", b.group(3) if b else "-",
               ("at %s s" % o.group(1)) if o else "no", voiced[-1] if voiced else "-", " DEAF" if deaf else ""))
    print("   " + line)
    return {"ms": int(l.group(1)) if l else None, "via": v, "budget": float(b.group(1)) if b else None,
            "fired": bool(o), "line": line, "deaf": deaf}


def _one(clip, tag, kill_at=None, stop_after=None, stop_for=20000):
    """One relay sentence on real Wispr; optional SIGKILL `kill_at` s into the clip, or SIGSTOP
    `stop_after` s after the stop chord for `stop_for` ms."""
    ctx = _rig()
    ref = ref_words(clip)[:20]
    try:
        mark = log_mark()
        if not _start_relay(mark):
            return None, "the relay never opened the sentence", None
        time.sleep(0.4)
        if kill_at is not None:
            th = _play_bg(clip, seconds=8)
            time.sleep(kill_at)
            post(PROC, {"kill": True})
            th.join(12)
        else:
            play(clip)
            time.sleep(1.0)
        if stop_after is not None:
            post(PROC, {"stop": True, "afterMs": int(stop_after * 1000), "forMs": stop_for})
        _stop_relay()
        _wait_end(mark, 75)
        time.sleep(3 if stop_after is None else stop_for / 1000.0 + 3)
        o = _after(ctx, mark, ref)
        return o, None, _sec(tag, mark)
    finally:
        _unrig(ctx)


def _wispr_up(timeout=60):
    return wait_for(lambda: cw.wispr_pid() and engine().get("ready"), timeout, 0.3)


@case("TQ1", tags=("gesture", "audio", "wave4"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="6 warm relay sentences on real Wispr, auto ON: each delivered once via wispr-history; the budget "
             "line at every close; local-auto only if Wispr really ran over it")
def tq1():
    la = _auto_on()
    res = []
    for i in range(6):
        clip = CLIP_EN if i % 2 == 0 else CLIP_SPEECH
        o, err, s = _one(clip, "TQ1.%d" % (i + 1))
        if err:
            res.append(("ERR", err)); continue
        v, why = _once(o)
        res.append((v, "%s %s" % (s["line"], _fmt(o))))
        time.sleep(3)
    ok = sum(1 for v, _ in res if v == "PASS")
    return ("PASS" if ok == 6 else "FAIL"), "auto %s; %d/6 once; " % (la.get("on"), ok) + " | ".join(x for _, x in res)


@case("TQ2", tags=("gesture", "audio", "wave4", "chaos"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="Wispr SIGKILLed 3 s into the sentence: the relay's own audio decoded locally, delivered once, "
             "close→words a few seconds; the next start does not wait for Wispr")
def tq2():
    _auto_on()
    o, err, s = _one(CLIP_SPEECH, "TQ2", kill_at=3.0)
    if err:
        return "ERROR", err
    v, why = _once(o)
    note = "%s; %s" % (s["line"], _fmt(o))
    # the next sentence right away: Wispr is gone or launching → borrowed local (the auto fallback's launch rule)
    time.sleep(1.0)
    o2, err2, s2 = _one(CLIP_EN, "TQ2.next")
    v2 = _once(o2)[0] if o2 else "ERROR"
    note += " || next: %s; %s" % (s2["line"] if s2 else err2, _fmt(o2) if o2 else "")
    _wispr_up(60)
    return ("PASS" if v == "PASS" and v2 == "PASS" and o["n"] == 1 else ("FAIL" if v != "PASS" or v2 != "PASS" else "BUG")), \
        why + "; " + note


@case("TQ3", tags=("gesture", "audio", "wave4", "chaos"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="Wispr SIGSTOPped 0.3 s after the stop for 20 s: local-auto at the budget (≤ budget + 1 s), delivered "
             "once via local-auto; the row finishing after the thaw is only logged, no second copy")
def tq3():
    _auto_on()
    o, err, s = _one(CLIP_SPEECH, "TQ3", stop_after=0.3, stop_for=20000)
    if err:
        return "ERROR", err
    v, why = _once(o)
    note = "%s; %s" % (s["line"], _fmt(o))
    ok = v == "PASS" and o["n"] == 1 and s["fired"] and "local-auto" in s["via"]
    return ("PASS" if ok else ("FAIL" if v != "PASS" else "BUG")), why + "; " + note


@case("TQ4", tags=("gesture", "audio", "wave4", "cold"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="Wispr killed, then 🔼→: the local model borrowed at once (`Wispr Flow is starting`), delivered once, "
             "Wispr launched by the relay; sentences at +2 s and +15 s after Wispr is up voiced and delivered once")
def tq4():
    _auto_on()
    post(PROC, {"kill": True})
    wait_for(lambda: not cw.wispr_pid(), 10, 0.2)
    time.sleep(1.0)
    m0 = log_mark()
    o, err, s = _one(CLIP_EN, "TQ4.cold")
    if err:
        return "ERROR", err
    v, why = _once(o)
    txt = log_since(m0)
    borrowed = bool(re.search(r"Wispr Flow is not running|Wispr Flow is starting", txt))
    t_up = time.time()
    up = _wispr_up(90)
    up_s = time.time() - t_up
    notes = ["cold: %s; borrowed %s; %s" % (s["line"], borrowed, _fmt(o)),
             "Wispr up %s (%.0f s after the sentence)" % (bool(up), up_s)]
    vs = [v]
    for lag, tag in ((2.0, "TQ4.+2s"), (15.0, "TQ4.+15s")):
        time.sleep(lag)
        o2, err2, s2 = _one(CLIP_EN, tag)
        if err2:
            vs.append("ERROR"); notes.append("%s: %s" % (tag, err2)); continue
        vs.append(_once(o2)[0])
        notes.append("%s: %s; %s" % (tag, s2["line"], _fmt(o2)))
    ok = all(x == "PASS" for x in vs) and borrowed and up
    return ("PASS" if ok else "FAIL"), " | ".join(notes)
