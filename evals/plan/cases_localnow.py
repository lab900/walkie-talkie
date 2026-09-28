"""⌘⌃X — the local model, now (2026-09-28). Victor (dictated): *"To compensate as a backup for slow
transcriptions, I want a local fallback that I can access during the dictation, at any point, through
a key combination displayed in the tooltip … Sometimes even ElevenLabs takes a lot to transcribe and
I want this quick exit."*

The key's action is `POST /test/local-now` (the chord itself is swallowed by the tap; posting it
from here would only test CGEventPost). Real audio through the Loopback, the fake Scribe (the
harness default), the witness tab bound — the rig of `cases_audio`.

    TN1  pressed mid-recording on eleven → local-forced delivered, nothing uploaded
    TN2  pressed while Scribe is 20 s late → local-forced within ~5 s, the late answer only logged
    TN3  pressed at rest → one flash, nothing else
"""
import time
from harness import *
from cases_audio import pre, rig, start, stop, when, last_delivery, settle_out, on_inject, not_inject, _quiet

LOCAL_FORCED = r"📦 delivery:|words landed"


def _batch_uploads():
    """The fake Scribe's batch-upload count, or None with the fake off."""
    try:
        return RUN["fake"]["state"].describe()["stats"]["batch"] if RUN["fake"] else None
    except Exception:
        return None


def _cost():
    return round((state().get("elevenCost") or {}).get("total") or 0, 6)


def _forced_delivery(since_iso, timeout):
    """The first lastDelivery after `since_iso` (wall time it was seen, record) — any via."""
    t = wait_for(lambda: last_delivery(since_iso), timeout, 0.2)
    return (time.time(), t) if t else (None, None)


@case("TN1", ("audio", "gesture"), engine="eleven",
      expect="⌘⌃X mid-recording → via local-forced, no upload (fake batch count and elevenCost unchanged); no row while recording (it waits 1 s into the transcription)")
def tn1():
    """⌘⌃X while recording on ElevenLabs: the take never leaves the Mac."""
    why = pre(("eleven",))
    if why: return "SKIP", why
    with rig():
        batch0, cost0 = _batch_uploads(), _cost()
        t0 = now_iso()
        m = start()
        if not on_inject(m):
            stop(); return not_inject(m)
        time.sleep(0.4)
        play(CLIP_SPEECH)
        ln = state().get("localNow") or {}
        t_press = time.time()
        post("/test/local-now")
        t_seen, d = _forced_delivery(t0, 120)
        settle_out(60)
        row_gone = not any("Local now" in r for r in state().get("chip") or [])
        batch1, cost1 = _batch_uploads(), _cost()
        uploaded = log_has(m, r"uploading to ElevenLabs")
        skipped = log_has(m, r"not uploaded: ⌘⌃X")
        via = (d or {}).get("via")
        note = (f"while recording localNow={ln}; via {via} in {((t_seen or time.time()) - t_press):.1f} s after the press; "
                f"'uploading' {uploaded}, 'not uploaded' {skipped}; fake batch {batch0}→{batch1}, cost {cost0}→{cost1}; "
                f"row gone after {row_gone}; witness {len(witness_text())} chars")
        ok = (via == "local-forced" and not uploaded and skipped and batch0 == batch1 and cost0 == cost1
              and ln.get("available") and ln.get("row") is None and row_gone and len(witness_text()) > 20)
        return ("PASS" if ok else "FAIL"), note


@case("TN2", ("audio", "gesture", "slow"), engine="eleven",
      expect="⌘⌃X while Scribe is 20 s late → local-forced ≤ ~5 s after the press; the late answer logged, not delivered")
def tn2():
    """⌘⌃X during the settle: the wait is abandoned, the late Scribe answer only logged."""
    why = pre(("eleven",))
    if why: return "SKIP", why
    h = state().get("whisper") or {}
    with rig():
        post("/test/eleven", {"fail": "delay", "delayMs": 20000})
        t0 = now_iso()
        n0 = outbox_count()
        m = start()
        if not on_inject(m):
            stop(); return not_inject(m)
        time.sleep(0.4)
        play(CLIP_SPEECH)
        stop()
        if not when(m, r"recording stopped", 10):
            return "FAIL", "the recording never stopped"
        time.sleep(2.0)                      # the row waits 1 s into the transcription (2026-09-28)
        ln = state().get("localNow") or {}
        t_press, mp = time.time(), log_mark()
        post("/test/local-now")
        t_words = when(mp, r"transcribed on this Mac instead of .*\(⌘⌃X\)", 60, 0.05)
        t_seen, d = _forced_delivery(t0, 90)
        dt = (t_words or time.time()) - t_press
        dd = (t_seen or time.time()) - t_press
        # The delayed call answers ~20 s after the upload began; give it room, then look.
        # Answered, not failed: the fake Scribe has the WAV (read before the delay) and says something.
        late = when(m, r"ElevenLabs answered [\d.]+ s after ⌘⌃X .* \d+ chars, only logged", 40, 0.5)
        settle_out(60)
        n1 = outbox_count()
        d_last = last_delivery(t0)
        via = (d or {}).get("via")
        note = (f"at the press localNow={ln} (model ready {h.get('ready')}); words {dt:.1f} s after the press, "
                f"delivered via {via} {dd:.1f} s after it; "
                f"late answer logged {bool(late)}; lastDelivery still {(d_last or {}).get('via')}; "
                f"outbox lines +{n1 - n0}; witness {len(witness_text())} chars")
        ok = (via == "local-forced" and dt <= (8 if h.get("ready") else 15) and late
              and (d_last or {}).get("via") == "local-forced" and ln.get("available")
              and "Local now" in str(ln.get("row")) and n1 - n0 <= 1)
        return ("PASS" if ok else "FAIL"), note


@case("TN3", (), engine="eleven",
      expect="⌘⌃X at rest → one flash 'Nothing to transcribe locally', nothing recorded, nothing delivered")
def tn3():
    """⌘⌃X with nothing recording or in flight."""
    wait_idle()
    t0 = now_iso()
    m = log_mark()
    ln = state().get("localNow") or {}
    post("/test/local-now")
    flashed = wait_for(lambda: any("Nothing to transcribe locally" in r for r in state().get("chip") or []), 3, 0.1)
    time.sleep(1.5)
    s = state()
    said = log_has(m, r"💻 POST /test/local-now — nothing to hand the local model")
    note = (f"localNow at rest {ln}; flash {bool(flashed)}; log line {said}; after: listening {s['listening']}, "
            f"settling {s['settling']}, busy {s['busy']}, new delivery {bool(last_delivery(t0))}")
    ok = (flashed and said and not ln.get("available") and ln.get("row") is None
          and not s["listening"] and not s["settling"] and not last_delivery(t0))
    return ("PASS" if ok else "FAIL"), note
