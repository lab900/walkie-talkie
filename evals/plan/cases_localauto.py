"""The auto fallback to local (p98) — TA1–TA5 (2026-09-28). Victor, 22:25: *"I don't think I will
ever have the patience to wait for 36 seconds. I will probably hit ⌘⌃X and use the local model
fallback. Plus, 10 s startup time is killing. … gate the Wispr engine to its p98 … (Auto fallback to
local model should be a checkbox in the Engine submenu.) … The goal is that ElevenLabs or Wispr Flow
should fall back to local in a few seconds in practice."*

At every close the relay logs `⏱ budget X s (p98 of N samples on <engine>, cap …)` and counts the
⌘⌃X row down (`Local in 2.1 s  ⌘⌃X`); at zero it does what ⌘⌃X does (`via: local-auto`). The
checkbox and the Wispr fakes are `POST /test/local-auto {"on", "wisprDown", "fakeLaunch"}`;
`state.localAuto {on, budget, since, fired, left, engine, samples, settled, wispr}` reads it back.

ElevenLabs cases run against the fake Scribe (`engine="eleven"`, the harness default) — no credits.
Wispr cases use `cases_wispr`'s desk (fake `History`, chords muted) — his real Wispr hears nothing.

    TA1  ElevenLabs 20 s late (fake) → local-auto within budget + 1 s; the late answer only logged
    TA2  ElevenLabs answers inside the budget (0.8 s late) → nothing fired
    TA3  Wispr row stalled `processing` (fake DB) → local-auto; the row finishing later only logged
    TA4  checkbox OFF → no budget, no fallback: the relay waits for the 8 s-late answer as before
    TA5  Wispr Flow not running at the start (faked) → the local model at the close, Wispr launched (fake)
    TA6  Wispr Flow's process 3 s old, launched by someone else (faked age) → borrowed too (batch 4, item 4)
"""
import re
import time
from harness import *
from cases_audio import pre, rig, start, stop, when, last_delivery, settle_out, on_inject, not_inject, _quiet
import cases_wispr as cw

BUDGET_LINE = r"⏱ budget ([\d.]+) s \(p98 of (\d+) samples on ([\w-]+)"
OVER_LINE = r"⏱ .+ over budget — ([\d.]+) s since the close, budget ([\d.]+) s"
LATE_ELEVEN = r"ElevenLabs answered [\d.]+ s after ⌘⌃X .* only logged"

# What these cases exercise, for `harness.py --changed-since` (evals/plan/README.md).
_COV_EL = covers("eleven", "local", "recorder", "delivery", "gesture", "chip")
_COV_W = covers("wispr", "local", "recorder", "delivery", "gesture", "chip")


def auto(**body):
    """POST /test/local-auto; answers state.localAuto."""
    return (post("/test/local-auto", body)[1] or {}).get("localAuto") or {}


_ORIG = {}

def _restore():
    """After every case: the checkbox as it was found, no Wispr fakes."""
    if "on" not in _ORIG:
        return
    _quiet(post, "/test/local-auto", {"on": _ORIG["on"], "wisprDown": False, "fakeLaunch": False, "wisprAge": None})

CLEANUPS.append(_restore)

def _remember():
    if "on" not in _ORIG:
        _ORIG["on"] = bool((state().get("localAuto") or {}).get("on", True))


def _pre_eleven():
    why = pre(("eleven",))
    if why:
        return why
    return None if "localAuto" in state() else "the installed build has no auto fallback (/test/state.localAuto)"


def _delivery(since_iso, timeout):
    t = wait_for(lambda: last_delivery(since_iso), timeout, 0.1)
    return (time.time(), t) if t else (None, None)


def _chip_has(pattern):
    return any(re.search(pattern, str(r)) for r in state().get("chip") or [])


def _budget(mark, timeout=10):
    """(wall time the budget line showed, seconds, samples, engine) or Nones."""
    t = when(mark, BUDGET_LINE, timeout, 0.05)
    if not t:
        return None, None, None, None
    m = re.search(BUDGET_LINE, log_since(mark))
    return t, float(m.group(1)), int(m.group(2)), m.group(3)


# ---------------------------------------------------------------- TA1
@case("TA1", ("audio", "gesture", "slow"), covers=_COV_EL, engine="eleven",
      expect="ElevenLabs (fake) 20 s late → the row counts down (`Local in …`), local-auto fires within budget + 1 s "
             "of the close, `over budget` flash, via local-auto; the late answer only logged; one outbox line")
def ta1():
    """The case that made the checkbox: a Scribe answer that never comes in time. The fake delays the
    upload 20 s; the budget for a ~13 s sentence is a few seconds."""
    why = _pre_eleven()
    if why: return "SKIP", why
    _remember()
    auto(on=True)
    with rig():
        post("/test/eleven", {"fail": "delay", "delayMs": 20000})
        t0, n0 = now_iso(), outbox_count()
        m = start()
        if not on_inject(m):
            stop(); return not_inject(m)
        time.sleep(0.4)
        play(CLIP_SPEECH)
        stop()
        t_close, budget, samples, eng = _budget(m)
        if not t_close:
            return "FAIL", "no `⏱ budget` line at the close"
        time.sleep(max(0.0, t_close + 1.3 - time.time()))
        counting = _chip_has(r"Local in \d+\.\d s")
        la_mid = state().get("localAuto") or {}
        t_fire = when(m, OVER_LINE, budget + 8, 0.05)
        flashed = wait_for(lambda: _chip_has(r"over budget"), 3, 0.1)
        t_seen, d = _delivery(t0, 60)
        late = when(m, LATE_ELEVEN, 40, 0.5)
        settle_out(60)
        la = state().get("localAuto") or {}
        n1 = outbox_count()
        d_last = last_delivery(t0) or {}
        fired_after = (t_fire - t_close) if t_fire else None
        via = (d or {}).get("via")
        note = (f"budget {budget} s ({samples} samples on {eng}); row counting at +1.3 s {counting} "
                f"(left {la_mid.get('left')}); fired {fired_after if fired_after is None else round(fired_after, 2)} s "
                f"after the close; flash {bool(flashed)}; via {via}, words {((t_seen or 0) - t_close):.1f} s after the close; "
                f"late answer logged {bool(late)}; lastDelivery {d_last.get('via')}; outbox +{n1 - n0}; "
                f"state fired {la.get('fired')}")
        ok = (counting and t_fire and fired_after <= budget + 1 and flashed and via == "local-auto"
              and late and d_last.get("via") == "local-auto" and n1 - n0 <= 1 and la.get("fired"))
        return ("PASS" if ok else "FAIL"), note


# ---------------------------------------------------------------- TA2
@case("TA2", ("audio", "gesture"), covers=_COV_EL, engine="eleven",
      expect="ElevenLabs (fake) answers 0.8 s late, inside the budget → `inside its … budget`, nothing fired, "
             "via elevenlabs-scribe")
def ta2():
    """The ordinary sentence: the budget is armed and never reached."""
    why = _pre_eleven()
    if why: return "SKIP", why
    _remember()
    auto(on=True)
    with rig():
        post("/test/eleven", {"fail": "delay", "delayMs": 800})
        t0 = now_iso()
        m = start()
        if not on_inject(m):
            stop(); return not_inject(m)
        time.sleep(0.4)
        play(CLIP_SPEECH)
        stop()
        t_close, budget, samples, eng = _budget(m)
        t_seen, d = _delivery(t0, 30)
        settle_out(30)
        la = state().get("localAuto") or {}
        txt = log_since(m)
        inside = re.search(r"⏱ [\w-]+ answered ([\d.]+) s after the close — inside its ([\d.]+) s budget", txt)
        fired = re.search(OVER_LINE, txt) is not None
        via = (d or {}).get("via")
        note = (f"budget {budget} s ({samples} on {eng}); via {via} {((t_seen or 0) - (t_close or 0)):.1f} s after "
                f"the close; inside line {inside.group(0)[2:80] if inside else None}; over-budget line {fired}; "
                f"state fired {la.get('fired')} settled {la.get('settled')}")
        ok = t_close and via == "elevenlabs-scribe" and inside and not fired and not la.get("fired")
        return ("PASS" if ok else "FAIL"), note


# ---------------------------------------------------------------- TA3
@case("TA3", ("desk", "audio", "gesture"), covers=_COV_W, engine="wispr", pre=cw.needs_desk,
      expect="Wispr's row stalls `processing` (Q24 would wait ≤ 300 s) → local-auto at the budget; the row "
             "finishing later is only logged, never a second copy")
def ta3():
    """Wispr's own fallback ASR finishes at 24–36 s (W12) — the 36 s Victor will not wait. Desk: a relay
    Wispr sentence (🔼→), its fake row adopted, the clip on the Loopback, the stop, the row left
    `processing`. Then, after the local words, the row is finished with words of its own."""
    db = cw.desk()
    _remember()
    auto(on=True)
    bind_witness(); witness_clear()
    m, t0, n0 = log_mark(), now_iso(), outbox_count()
    gesture("forward-right")
    if not wait_for(lambda: state()["listening"], 4):
        return "FAIL", "the sentence did not open"
    ra = db.insert(at=time.time())
    wait_for(lambda: cw.live()["captureRow"] == ra, 3)
    time.sleep(0.4)
    play(CLIP_SPEECH)
    gesture("forward-right")
    db.update(ra, status="processing", speech=1.5)
    t_close, budget, samples, eng = _budget(m)
    if not t_close:
        db.update(ra, status="dismissed")
        return "FAIL", "no `⏱ budget` line at the close"
    t_fire = when(m, OVER_LINE, budget + 8, 0.05)
    t_seen, d = _delivery(t0, 60)
    wait_for(lambda: len(witness_text().strip()) > 20, 30, 0.3)
    m2 = log_mark()
    db.finish(ra, "ta three late words from wispr")
    time.sleep(3.0)
    settle_out(30)
    got = witness_text()
    fired_after = (t_fire - t_close) if t_fire else None
    via = (d or {}).get("via")
    late_in = "late words from wispr" in got
    n1 = outbox_count()
    note = (f"budget {budget} s ({samples} on {eng}); fired "
            f"{fired_after if fired_after is None else round(fired_after, 2)} s after the close; via {via}; "
            f"witness {len(got.strip())} chars, late row in it {late_in}; outbox +{n1 - n0}; "
            f"after the row: {log_since(m2).strip().splitlines()[-1][:110] if log_since(m2).strip() else '—'}")
    ok = t_fire and fired_after <= budget + 1 and via == "local-auto" and not late_in and len(got.strip()) > 20 \
        and n1 - n0 <= 1
    return ("PASS" if ok else "FAIL"), note


# ---------------------------------------------------------------- TA4
@case("TA4", ("audio", "gesture"), covers=_COV_EL, engine="eleven",
      expect="checkbox OFF → no `⏱ budget`, the row says `Local now` (no countdown), nothing fires; the 8 s-late "
             "answer is delivered via elevenlabs-scribe, as before")
def ta4():
    """OFF is today's behaviour: the relay waits on the engine."""
    why = _pre_eleven()
    if why: return "SKIP", why
    _remember()
    la0 = auto(on=False)
    with rig():
        post("/test/eleven", {"fail": "delay", "delayMs": 8000})
        t0 = now_iso()
        m = start()
        if not on_inject(m):
            stop(); return not_inject(m)
        time.sleep(0.4)
        play(CLIP_SPEECH)
        stop()
        when(m, r"recording stopped", 10)
        time.sleep(2.5)
        rows = [str(r) for r in state().get("chip") or []]
        plain = any("Local now" in r for r in rows)
        counting = any("Local in" in r for r in rows)
        t_seen, d = _delivery(t0, 40)
        settle_out(30)
        txt = log_since(m)
        armed = re.search(BUDGET_LINE, txt) is not None
        fired = re.search(OVER_LINE, txt) is not None
        via = (d or {}).get("via")
        note = (f"on {la0.get('on')}; at +2.5 s row `Local now` {plain}, countdown {counting}; budget line {armed}; "
                f"over-budget {fired}; via {via}")
        ok = la0.get("on") is False and plain and not counting and not armed and not fired and via == "elevenlabs-scribe"
        return ("PASS" if ok else "FAIL"), note


# ---------------------------------------------------------------- TA5
@case("TA5", ("audio", "gesture"), covers=_COV_W, engine="wispr",
      expect="Engine = Wispr, Wispr read as not running (fake) → the sentence opens on the local model at once "
             "(`Wispr Flow is starting` flash), delivered via local-whisper at the close; Wispr launched "
             "(fake exec, one launch); the Engine is Wispr again after")
def ta5():
    """*"10 s startup time is killing"* — a Wispr sentence never waits for Wispr Flow. `wisprDown` makes
    the relay read Wispr as not running at the start; `fakeLaunch` logs the launch instead of running it,
    so his real Wispr is untouched. Chords muted for the case all the same."""
    why = pre(None)
    if why: return "SKIP", why
    if "localAuto" not in state():
        return "SKIP", "the installed build has no auto fallback (/test/state.localAuto)"
    _remember()
    la0 = auto(on=True, wisprDown=True, fakeLaunch=True)
    launches0 = (la0.get("wispr") or {}).get("launches", 0)
    post("/test/wispr-chord", {"mute": True, "seconds": 120})
    try:
        with rig():
            t0 = now_iso()
            m = log_mark()
            gesture("forward-right")
            opened = wait_for(lambda: log_has(m, r"mic: recording through"), 8)
            flashed = wait_for(lambda: _chip_has(r"Wispr Flow is starting"), 3, 0.1)
            s_mid = state()
            if not opened:
                post("/test/cancel")
                return "FAIL", "the microphone never opened"
            time.sleep(0.4)
            play(CLIP_EN)
            stop()
            t_seen, d = _delivery(t0, 60)
            settle_out(30)
            back = wait_for(lambda: engine().get("engine") == "wispr" and state().get("borrowedFrom") is None, 5, 0.25)
            la = state().get("localAuto") or {}
            txt = log_since(m)
            borrowed = re.search(r"🔁 .*Wispr Flow is not running[^\n]*", txt)
            launched = "Wispr Flow would be launched in the background" in txt
            via = (d or {}).get("via")
            note = (f"borrow {borrowed.group(0)[:100] if borrowed else None}; flash {bool(flashed)}; "
                    f"borrowedFrom mid {s_mid.get('borrowedFrom')}; via {via}; launch logged {launched}, launches "
                    f"{launches0}→{(la.get('wispr') or {}).get('launches')}; back on Wispr {bool(back)}; "
                    f"witness {len(witness_text().strip())} chars")
            ok = (borrowed and flashed and via == "local-whisper" and launched
                  and (la.get("wispr") or {}).get("launches") == launches0 + 1 and back
                  and len(witness_text().strip()) > 10)
            return ("PASS" if ok else "FAIL"), note
    finally:
        _quiet(post, "/test/wispr-chord", {"mute": False})


# ---------------------------------------------------------------- TA6 (batch 4, item 4)
@case("TA6", ("audio", "desk"), covers=_COV_W, engine="wispr", pre=cw.needs_desk,
      expect="Wispr Flow's process 3 s old (faked age; the relay did not launch it) → a start on Engine = Wispr borrows "
             "the local model (`its process is 3.0 s old`), delivered via local-whisper into the witness; with the real "
             "(old) age the next start is Wispr's, not borrowed")
def ta6():
    """Item 4 (lab wave 4, TX9): the borrow covered only a Wispr the relay launched itself; relaunched from
    outside and dictated 1 s later, three sentences paid Q14's 4.3–6.3 s. The criterion is now the process's
    own age (`ProcessClock.age`, < 12 s). `POST /test/local-auto {"wisprAge": 3}` fakes the age, so his
    real Wispr is untouched; keyless starts (`/test/gesture {"direct"}`), chords muted (the desk)."""
    _remember()
    db = cw.desk()
    cw.bind_witness(); witness_clear()
    auto(on=True, wisprDown=False, fakeLaunch=True, wisprAge=3)
    try:
        m = log_mark()
        cw._direct("forward-right")
        if not wait_for(lambda: state()["listening"], 6):
            return "FAIL", "the sentence did not open"
        flashed = wait_for(lambda: _chip_has(r"Wispr Flow is starting"), 3, 0.1)
        time.sleep(0.4)
        play(CLIP_EN)
        time.sleep(0.6)
        cw._direct("forward-right")
        got = wait_for(lambda: witness_text().strip(), 40, 0.3)
        wait_for(lambda: log_has(m, r"📦 delivery: "), 10, 0.3)
        txt = log_since(m)
        borrowed = re.search(r"🔁 [^\n]*its process is 3\.0 s old[^\n]*", txt)
        d = re.search(r"📦 delivery: (\S+) → (\S+)", txt)
        wait_for(lambda: not state()["listening"] and not state()["settling"], 20, 0.3)
        time.sleep(1.5)
        # the real age (his Wispr, long up): not borrowed
        # `fakeLaunch: false` also forgets the (fake) launch the first start recorded — it would
        # otherwise read as "launched by the relay 10 s ago" and borrow again, rightly.
        auto(wisprAge=None, fakeLaunch=False)
        m2 = log_mark()
        cw._direct("forward-right")
        opened2 = wait_for(lambda: state()["listening"], 6)
        time.sleep(0.8)
        s2 = state()
        post("/test/cancel")
        txt2 = log_since(m2)
        not_borrowed = "auto fallback" not in txt2 and s2.get("borrowedFrom") is None
        note = (f"borrow {borrowed.group(0)[:110] if borrowed else None}; flash {bool(flashed)}; delivery {d.groups() if d else None}; "
                f"witness {len(witness_text().strip())} chars; real age: opened {bool(opened2)}, not borrowed {not_borrowed} "
                f"(processAge {((state().get('localAuto') or {}).get('wispr') or {}).get('processAge')})")
        ok = borrowed and flashed and got and d and d.group(1) == "local-whisper" and opened2 and not_borrowed
        return ("PASS" if ok else "FAIL"), note
    finally:
        _quiet(post, "/test/local-auto", {"wisprAge": None, "fakeLaunch": False})
