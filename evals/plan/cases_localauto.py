"""Prepare local transcript (p95) — TA2, TA4–TA11 (2026-09-28 as *the auto fallback to local (p98)*,
reshaped 2026-09-29). Victor, 29 Sep morning: *"We go with p95. But by the time p95 elapses from the
start of the transcription, I must ALREADY have the local model's transcription ready … Only when the
local transcription is ready do you show the 'insert local transcription' hint in the tooltip."* Then:
*"the insertion of the local transcription must be done at the human's request, never automatically.
I only OFFER it."* And the row's words: *"Use local"*.

At every close on a cloud engine the relay logs `⏱ budget X s (p95 of N samples on <engine>, cap …)`,
starts the local model `budget − localEta` into the wait (`🔮 local transcript: decoding ahead …`),
holds its words and offers them on the chip (`💻 Use local  ⌘⌃X`, `— <engine> over budget` once the
budget has run out). **Nothing is inserted on a clock**: ⌘⌃X (`POST /test/local-now`) inserts them at
once (`via: local-forced`); the engine's words landing first take the row down and discard them. One
`📊 fallback:` line per sentence at its outcome (and `~/.walkie-talkie/fallback.jsonl`).
`POST /test/local-auto {"on", "budget", "localEta", "wisprDown", "fakeLaunch", "wisprAge"}` drives it;
`state.localAuto {on, budget, p95, expired, spec {startAt, startedAt, readyAt, phase, wasted}, trace,
forced, wispr}` reads it back.

ElevenLabs cases run against the fake Scribe (`engine="eleven"`, the harness default) — no credits —
and start/stop with `/test/gesture {"direct": true}` (no chord on the wire). Wispr cases use
`cases_wispr`'s desk (fake `History`, chords muted) — his real Wispr hears nothing.

    TA2  ElevenLabs answers inside the budget (0.8 s late) → nothing decoded ahead, no row
    TA4  checkbox OFF → no budget, no decode ahead: the row is `Local now`, the 8 s-late answer delivered
    TA5  Wispr Flow not running at the start (faked) → the local model at the close, Wispr launched (fake)
    TA6  Wispr Flow's process 3 s old, launched by someone else (faked age) → borrowed too (batch 4, item 4)
    TA7  Wispr row stalled `processing` ~20 s → local ready by the budget, `Use local` shown, nothing
         inserted at the budget, Wispr's words delivered when they land; the local decode wasted
    TA8  ElevenLabs answers at 60 % of a (forced) 6 s budget, mid-decode → wasted, no row, engine words
    TA9  `Use local` up before the budget → ⌘⌃X inserts at once (`local-forced`)
    TA10 localEta ≥ budget (forced — on his data a 60 s take is budget 11.2 s vs localEta 1.2 s) →
         the decode ahead starts at the close
    TA11 budget expired, ElevenLabs never answers (15 s late) → row stays (`over budget`), nothing
         inserted, ⌘⌃X inserts

Retired 2026-09-29: TA1 (ElevenLabs 20 s late → local-auto at the budget) and TA3 (Wispr row stalled →
local-auto) — the automatic insert they asserted is gone; TA11 and TA7 are their successors.
"""

import re
import time
from harness import *
from cases_audio import pre, rig, start, stop, when, last_delivery, settle_out, on_inject, not_inject, _quiet
import cases_wispr as cw

BUDGET_LINE = r"⏱ budget ([\d.]+) s \(p95 of (\d+) samples on ([\w-]+)"
OVER_LINE = r"⏱ .+ over budget — ([\d.]+) s since the close, budget ([\d.]+) s: nothing is inserted"
READY_LINE = r"🔮 local transcript ready \+([\d.]+) s after the close"
SPEC_LINE = r"🔮 local transcript: decoding ahead from \+([\d.]+) s after the close \(planned \+([\d.]+) s\)"
TRACE_LINE = r"📊 fallback: ([^\n]+)"
LATE_ELEVEN = r"ElevenLabs answered [\d.]+ s after ⌘⌃X .* only logged"
USE_LOCAL = r"Use local\s+⌘⌃X"

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
    _quiet(post, "/test/local-auto", {"on": _ORIG["on"], "wisprDown": False, "fakeLaunch": False, "wisprAge": None,
                                      "budget": None, "localEta": None})

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


def _trace(mark, timeout=30):
    """The sentence's `📊 fallback:` line as {key: value} (budget's `(p95,n=…)` split off), or None."""
    if not when(mark, TRACE_LINE, timeout, 0.1):
        return None
    line = re.findall(TRACE_LINE, log_since(mark))[-1]
    kv = dict(re.findall(r"(\w+)=(\S+)", line))
    kv["_line"] = line
    return kv


def _num(kv, k):
    """A trace field as seconds, None for `never` / missing."""
    try:
        return float(str((kv or {}).get(k, "never")).split("(")[0])
    except ValueError:
        return None


def _say(kv):
    return (kv or {}).get("_line", "no 📊 line")[:230]


def _el_sentence(clip=None, seconds=None):
    """An ElevenLabs relay sentence with no chord on the wire: the direct start, the clip into the
    Loopback, the direct stop. Returns (mark, t0 iso, wall time of the stop) — or raises."""
    m, t0 = log_mark(), now_iso()
    cw._direct("forward-right")
    if not wait_for(lambda: log_has(m, r"mic: recording through"), 8):
        post("/test/cancel")
        raise RuntimeError("the microphone never opened")
    if not on_inject(m):
        post("/test/cancel")
        raise RuntimeError("the recorder is not on the Loopback")
    time.sleep(0.4)
    play(clip or CLIP_SPEECH, seconds=seconds)
    cw._direct("forward-right")
    return m, t0, time.time()


def _watch_rows(until_fn, timeout, step=0.1):
    """Every distinct chip row seen until `until_fn()` is true (or the timeout)."""
    seen, t_end = [], time.time() + timeout
    while time.time() < t_end:
        for r in state().get("chip") or []:
            if str(r) not in seen:
                seen.append(str(r))
        if until_fn():
            break
        time.sleep(step)
    return seen


# ---------------------------------------------------------------- TA2
@case("TA2", ("audio",), covers=_COV_EL, engine="eleven",
      expect="ElevenLabs (fake) answers 0.8 s late, inside the budget → `inside its … budget`, no decode ahead "
             "started (its start is budget − localEta, later than the answer), no `Use local` row; 📊 outcome=engine "
             "specStart=never wasted=false; via elevenlabs-scribe")
def ta2():
    """The ordinary sentence: the budget is armed, the decode ahead is planned and never needed."""
    why = _pre_eleven()
    if why: return "SKIP", why
    _remember()
    auto(on=True, budget=None, localEta=None)
    with rig():
        post("/test/eleven", {"fail": "delay", "delayMs": 800})
        m, t0, _ = _el_sentence()
        t_close, budget, samples, eng = _budget(m)
        rows = _watch_rows(lambda: last_delivery(t0), 30)
        t_seen, d = _delivery(t0, 5)
        tr = _trace(m, 10)
        settle_out(30)
        txt = log_since(m)
        inside = re.search(r"⏱ [\w-]+ answered ([\d.]+) s after the close — inside its ([\d.]+) s budget", txt)
        via = (d or {}).get("via")
        use_local = any(re.search(USE_LOCAL, r) for r in rows)
        note = (f"budget {budget} s ({samples} on {eng}); via {via}; inside line {bool(inside)}; "
                f"Use local seen {use_local}; {_say(tr)}")
        ok = (t_close and via == "elevenlabs-scribe" and inside and not use_local and tr
              and tr.get("outcome") == "engine" and tr.get("specStart") == "never" and tr.get("wasted") == "false")
        return ("PASS" if ok else "FAIL"), note


# ---------------------------------------------------------------- TA4
@case("TA4", ("audio",), covers=_COV_EL, engine="eleven",
      expect="checkbox OFF → no `⏱ budget`, no decode ahead, no 📊 line; the row says `Local now` (never `Use local`); "
             "nothing inserted; the 8 s-late answer is delivered via elevenlabs-scribe, as before")
def ta4():
    """OFF: ⌘⌃X's plain row from one second into the wait, and the relay waits on the engine."""
    why = _pre_eleven()
    if why: return "SKIP", why
    _remember()
    la0 = auto(on=False, budget=None, localEta=None)
    with rig():
        post("/test/eleven", {"fail": "delay", "delayMs": 8000})
        m, t0, _ = _el_sentence()
        when(m, r"recording stopped", 10)
        rows = _watch_rows(lambda: last_delivery(t0), 40)
        t_seen, d = _delivery(t0, 5)
        settle_out(30)
        txt = log_since(m)
        plain = any("Local now" in r for r in rows)
        use_local = any(re.search(USE_LOCAL, r) for r in rows)
        armed = re.search(BUDGET_LINE, txt) is not None
        spec = re.search(SPEC_LINE, txt) is not None
        traced = re.search(TRACE_LINE, txt) is not None
        via = (d or {}).get("via")
        note = (f"on {la0.get('on')}; row `Local now` {plain}, `Use local` {use_local}; budget line {armed}; "
                f"decode ahead {spec}; 📊 {traced}; via {via}")
        ok = (la0.get("on") is False and plain and not use_local and not armed and not spec and not traced
              and via == "elevenlabs-scribe")
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


# ---------------------------------------------------------------- TA7 (2026-09-29)
@case("TA7", ("desk", "audio"), covers=_COV_W, engine="wispr", pre=cw.needs_desk,
      expect="Wispr's row stalls `processing` ~20 s → the local transcript is decoded ahead and ready by the "
             "budget (≤ budget + 0.5 s), `Use local  ⌘⌃X` shown, `over budget` added at the budget and NOTHING "
             "inserted; the row finished at ~20 s → Wispr's words delivered (witness has them, no local words); "
             "📊 outcome=engine wasted=true budgetExpired set")
def ta7():
    """The case Victor described: Wispr slow, the local words ready and offered, his choice. Desk: a
    relay Wispr sentence (direct gesture), its fake row adopted, the clip on the Loopback, the stop,
    the row left `processing` for ~20 s, then finished with words of its own."""
    db = cw.desk()
    _remember()
    auto(on=True, budget=None, localEta=None)
    cw.bind_witness(); witness_clear()
    m, t0 = log_mark(), now_iso()
    cw._direct("forward-right")
    if not wait_for(lambda: state()["listening"], 6):
        return "FAIL", "the sentence did not open"
    ra = db.insert(at=time.time())
    wait_for(lambda: cw.live()["captureRow"] == ra, 3)
    time.sleep(0.4)
    play(CLIP_SPEECH)
    cw._direct("forward-right")
    db.update(ra, status="processing", speech=1.5)
    t_close, budget, samples, eng = _budget(m)
    if not t_close:
        db.update(ra, status="dismissed")
        return "FAIL", "no `⏱ budget` line at the close"
    t_ready = when(m, READY_LINE, budget + 10, 0.05)
    rows = _watch_rows(lambda: time.time() > t_close + budget + 2.0, budget + 4)
    over = when(m, OVER_LINE, 1, 0.1)
    inserted_early = last_delivery(t0)
    over_row = any(re.search(USE_LOCAL + r" — Wispr Flow over budget", r) for r in rows)
    use_local = any(re.search(USE_LOCAL, r) for r in rows)
    # Wispr answers ~20 s after the close.
    time.sleep(max(0.0, t_close + 20 - time.time()))
    db.finish(ra, "ta seven words from wispr at last")
    t_seen, d = _delivery(t0, 20)
    tr = _trace(m, 10)
    wait_for(lambda: "ta seven" in witness_text(), 10, 0.3)
    settle_out(30)
    got = witness_text()
    ready_after = (t_ready - t_close) if t_ready else None
    via = (d or {}).get("via")
    note = (f"budget {budget} s ({samples} on {eng}); local ready {None if ready_after is None else round(ready_after, 2)} s "
            f"after the close; Use local seen {use_local}, over-budget row {over_row}, over line {bool(over)}; "
            f"delivered before Wispr {bool(inserted_early)}; via {via}; witness has Wispr's words {'ta seven' in got}; "
            f"{_say(tr)}")
    ok = (ready_after is not None and ready_after <= budget + 0.5 and use_local and over_row and over
          and not inserted_early and via and via.startswith("wispr") and "ta seven" in got and tr
          and tr.get("outcome") == "engine" and tr.get("wasted") == "true" and _num(tr, "budgetExpired") is not None)
    return ("PASS" if ok else "FAIL"), note


# ---------------------------------------------------------------- TA8
@case("TA8", ("audio",), covers=_COV_EL, engine="eleven",
      expect="budget forced 6 s, localEta 2.8 s (the decode starts at +3.2 s); ElevenLabs (fake) answers ~3.6 s — "
             "60 % of the budget, mid-decode → its words delivered (elevenlabs-scribe), no `Use local` row ever, "
             "📊 outcome=engine wasted=true specStart≈3.2 localReady=never, `discarded while decoding` logged")
def ta8():
    """The decode ahead that loses the race: it ran, and its words are thrown away."""
    why = _pre_eleven()
    if why: return "SKIP", why
    _remember()
    auto(on=True, budget=6.0, localEta=2.8)
    with rig():
        post("/test/eleven", {"fail": "delay", "delayMs": 3400})
        m, t0, _ = _el_sentence()
        t_close, budget, samples, eng = _budget(m)
        rows = _watch_rows(lambda: last_delivery(t0), 30)
        t_seen, d = _delivery(t0, 5)
        tr = _trace(m, 10)
        settle_out(30)
        txt = log_since(m)
        disc = "local transcript discarded while decoding" in txt
        via = (d or {}).get("via")
        use_local = any(re.search(USE_LOCAL, r) for r in rows)
        ans, start_ = _num(tr, "engineAnswer"), _num(tr, "specStart")
        note = (f"budget {budget} s (forced); via {via}; engine answered {ans} s = "
                f"{None if not ans else round(ans / 6.0 * 100)} % of the budget; decode ahead from {start_} s; "
                f"Use local seen {use_local}; discarded while decoding {disc}; {_say(tr)}")
        ok = (budget == 6.0 and via == "elevenlabs-scribe" and not use_local and tr and tr.get("outcome") == "engine"
              and tr.get("wasted") == "true" and start_ is not None and ans is not None and start_ < ans
              and tr.get("localReady") == "never" and disc)
        return ("PASS" if ok else "FAIL"), note


# ---------------------------------------------------------------- TA9
@case("TA9", ("audio",), covers=_COV_EL, engine="eleven",
      expect="budget forced 8 s, localEta 8 s (decode ahead from the close); ElevenLabs (fake) 15 s late → "
             "`Use local  ⌘⌃X` before the budget; ⌘⌃X (POST /test/local-now) → words handed over ≤ 0.5 s after the press "
             "via local-forced (`decoded ahead, ready … before it was asked for`); 📊 outcome=local-forced "
             "wasted=false budgetExpired=never; nothing uploaded twice")
def ta9():
    """The offer taken: the words are already there, so the key is instant."""
    why = _pre_eleven()
    if why: return "SKIP", why
    _remember()
    auto(on=True, budget=8.0, localEta=8.0)
    with rig():
        post("/test/eleven", {"fail": "delay", "delayMs": 15000})
        m, t0, _ = _el_sentence()
        t_close, budget, samples, eng = _budget(m)
        up = wait_for(lambda: any(re.search(USE_LOCAL, str(r)) for r in state().get("chip") or []), 10, 0.05)
        t_up = time.time()
        early = last_delivery(t0)
        t_press = time.time()
        post("/test/local-now")
        t_seen, d = _delivery(t0, 10)
        tr = _trace(m, 10)
        late = when(m, LATE_ELEVEN, 20, 0.5)
        settle_out(30)
        txt = log_since(m)
        reused = re.search(r"decoded ahead, ready ([\d.]+) s before it was asked for", txt)
        via = (d or {}).get("via")
        # **Instant = the words handed to delivery at the press** — the 📊 line's toWords against the
        # press, both from the close. `lastDelivery` is stamped after the terminal has echoed the typing
        # (~2 s for this clip whatever the engine), so it measures the typing, not the wait.
        typed = (t_seen - t_press) if t_seen else None
        tw = _num(tr, "toWords")
        lag = (tw - (t_press - t_close)) if (tw is not None and t_close) else None
        note = (f"Use local up {bool(up)} at +{round(t_up - (t_close or t_up), 2)} s (budget {budget}); delivered before "
                f"the press {bool(early)}; press → words handed over {None if lag is None else round(lag, 2)} s "
                f"(typed and echoed {None if typed is None else round(typed, 2)} s), via {via}; "
                f"reused {reused.group(0) if reused else None}; late Scribe logged {bool(late)}; {_say(tr)}")
        ok = (up and not early and lag is not None and lag <= 0.5 and via == "local-forced" and reused and tr
              and tr.get("outcome") == "local-forced" and tr.get("wasted") == "false"
              and tr.get("budgetExpired") == "never")
        return ("PASS" if ok else "FAIL"), note


# ---------------------------------------------------------------- TA10
@case("TA10", ("audio",), covers=_COV_EL, engine="eleven",
      expect="localEta forced 99 s ≥ the budget → planned start +0.00 s: the decode ahead starts at the close "
             "(≤ 0.6 s, once the WAV is closed); ElevenLabs (fake) 2.5 s late answers → engine words, 📊 specStart ≤ 0.6")
def ta10():
    """`max(0, budget − localEta)`: a take whose local decode is slower than the budget starts at once.
    Forced, because it does not happen naturally on his data: a 60 s take is budget 11.2 s (ElevenLabs
    p95) against localEta 1.2 s — the local model is the faster of the two at every length."""
    why = _pre_eleven()
    if why: return "SKIP", why
    _remember()
    auto(on=True, budget=None, localEta=99.0)
    with rig():
        post("/test/eleven", {"fail": "delay", "delayMs": 2500})
        m, t0, _ = _el_sentence()
        t_close, budget, samples, eng = _budget(m)
        t_spec = when(m, SPEC_LINE, 5, 0.05)
        sm = re.search(SPEC_LINE, log_since(m))
        t_seen, d = _delivery(t0, 30)
        tr = _trace(m, 10)
        settle_out(30)
        via = (d or {}).get("via")
        st, planned = (float(sm.group(1)), float(sm.group(2))) if sm else (None, None)
        note = f"budget {budget} s ({samples} on {eng}); decode ahead from +{st} s (planned +{planned}); via {via}; {_say(tr)}"
        ok = (planned == 0.0 and st is not None and st <= 0.6 and via == "elevenlabs-scribe" and tr
              and _num(tr, "specStart") is not None and _num(tr, "specStart") <= 0.6)
        return ("PASS" if ok else "FAIL"), note


# ---------------------------------------------------------------- TA11
@case("TA11", ("audio",), covers=_COV_EL, engine="eleven",
      expect="budget forced 3 s, ElevenLabs (fake) 15 s late → at +4 s nothing delivered, `⏱ … over budget … nothing "
             "is inserted`, the row reads `Use local  ⌘⌃X — ElevenLabs over budget` and stays (still at +7 s); ⌘⌃X → "
             "words handed over ≤ 0.5 s after the press via local-forced; 📊 budgetExpired≈3 outcome=local-forced wasted=false")
def ta11():
    """The engine that never comes: the relay does not choose for him — the offer stands until he takes it."""
    why = _pre_eleven()
    if why: return "SKIP", why
    _remember()
    auto(on=True, budget=3.0, localEta=None)
    with rig():
        post("/test/eleven", {"fail": "delay", "delayMs": 15000})
        m, t0, _ = _el_sentence()
        t_close, budget, samples, eng = _budget(m)
        if not t_close:
            return "FAIL", "no `⏱ budget` line at the close"
        time.sleep(max(0.0, t_close + 4.0 - time.time()))
        rows4 = [str(r) for r in state().get("chip") or []]
        early4 = last_delivery(t0)
        time.sleep(max(0.0, t_close + 7.0 - time.time()))
        rows7 = [str(r) for r in state().get("chip") or []]
        early7 = last_delivery(t0)
        over = re.search(OVER_LINE, log_since(m))
        t_press = time.time()
        post("/test/local-now")
        t_seen, d = _delivery(t0, 10)
        tr = _trace(m, 10)
        settle_out(40)
        via = (d or {}).get("via")
        typed = (t_seen - t_press) if t_seen else None
        tw = _num(tr, "toWords")
        lag = (tw - (t_press - t_close)) if tw is not None else None   # see TA9: toWords against the press
        row_over = lambda rows: any(re.search(USE_LOCAL + r" — ElevenLabs over budget", r) for r in rows)
        note = (f"budget {budget} (forced); +4 s: delivered {bool(early4)}, row {row_over(rows4)}; +7 s: delivered "
                f"{bool(early7)}, row {row_over(rows7)}; over line {bool(over)}; press → words handed over "
                f"{None if lag is None else round(lag, 2)} s (typed and echoed {None if typed is None else round(typed, 2)} s) "
                f"via {via}; {_say(tr)}")
        be = _num(tr, "budgetExpired")
        ok = (budget == 3.0 and not early4 and not early7 and row_over(rows4) and row_over(rows7) and over
              and lag is not None and lag <= 0.5 and via == "local-forced" and tr and be is not None
              and 3.0 <= be <= 3.5 and tr.get("outcome") == "local-forced" and tr.get("wasted") == "false")
        return ("PASS" if ok else "FAIL"), note
