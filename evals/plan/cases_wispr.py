"""**Wispr Flow as the engine** — TW1–TW21 (2026-09-28), the outline in
`evals/plan/wispr/D-state.md` §3, mapped to the findings of the four adversarial reviews
(`A-lifecycle.md` W-A*, `B-errors.md` W-B*, `C-firewall.md` W-C*, `D-state.md` W-D*).

Two kinds of case:

- **desk** — run on the host, Engine = Wispr, but Wispr's real process never hears a thing:
  the app reads a **fake `History`** (`fake_wispr_db.py`, switched in through a `WT_WISPR_DB=`
  line in `elevenlabs.env` between two `# fake-wispr:` marks, removed after every case) and
  **Wispr's chords are muted** (`POST /test/wispr-chord {"mute": true}` — only their stamped
  trailing `flagsChanged []` goes out). Rows are inserted and rewritten by the case the way Wispr
  writes them (B §1). The relay's own recorder is pointed at the Loopback (`/test/mic`) so no
  real microphone opens. Assertions read `GET /test/state` (`wisprLive`, `pasteboard`, the
  usual fields), the log and the witness tab — never a screenshot.
- **lab** (`lab_only=True`) — the real Wispr in the Tart guest, audio through BlackHole
  (`docs/vm-lab.md`, `docs/vm-wispr.md`); SKIP on the host.

Every case needs Wispr running (`needs_wispr`: a host without it SKIPs); a desk case also needs
an installed build with the hooks (`wisprLive` in `/test/state`). Verdicts: **BUG** = the
review's prediction confirmed (most of these are expected-fail today), **PASS** = the app does
what the review asks for, **FAIL** = neither."""
import glob, os, subprocess, time
from harness import *
import fake_wispr_db as fw

WISPR_EXE = "/Applications/Wispr Flow.app/Contents/MacOS/Wispr Flow"
FAKE_DB = os.path.join(WORK, "fake-wispr", "flow.sqlite")
WMARK = "# fake-wispr: written by evals/plan/cases_wispr.py, removed after each case"
CACHES = os.path.expanduser("~/Library/Caches/ro.victorrentea.wispr-relay")
KILL_OK = IN_LAB or os.environ.get("WT_ALLOW_WISPR_KILL") == "1"


# ---------------------------------------------------------------- preconditions
def wispr_pid():
    try:
        pid = (state().get("wisprLive") or {}).get("wisprPid")
        if pid is not None:
            return pid
    except Exception:
        pass
    out = subprocess.run(["pgrep", "-f", "^" + WISPR_EXE], capture_output=True, text=True).stdout.split()
    return int(out[0]) if out else 0

def needs_wispr():
    """SKIP reason when Wispr Flow's main process is not running (a host without it)."""
    return None if wispr_pid() else "Wispr Flow is not running (host without Wispr — the lab has it)"

def needs_desk():
    return needs_wispr() or (None if "wisprLive" in state() else
                             "the installed build has no Wispr test hooks (/test/state.wisprLive)")

def needs_standalone(on=True):
    def pre():
        why = needs_desk()
        if why:
            return why
        if bool(state().get("wisprStandalone")) != on:
            return "needs Q9 standalone %s (state.wisprStandalone)" % ("ON" if on else "OFF")
        return None
    return pre


# ---------------------------------------------------------------- the desk rig
def _env_block(lines):
    """Our `WT_WISPR_DB` block in `elevenlabs.env` set to `lines` (or removed); everything else
    — his key, the fake-Scribe block — byte for byte."""
    try:
        cur = open(ELEVEN_ENV, encoding="utf-8").read().splitlines()
        mode = os.stat(ELEVEN_ENV).st_mode & 0o777
    except FileNotFoundError:
        cur, mode = [], 0o600
    keep, inside = [], False
    for l in cur:
        if l.startswith(WMARK):
            inside = not l.endswith("(end)")
            continue
        if not inside:
            keep.append(l)
    if lines:
        keep += [WMARK] + lines + [WMARK + " (end)"]
    if keep == cur:
        return
    tmp = ELEVEN_ENV + ".wispr-tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(keep) + ("\n" if keep else ""))
    os.chmod(tmp, mode)
    os.replace(tmp, ELEVEN_ENV)

DESK = {"db": None}

def desk(engine_wispr=True):
    """Fresh fake History, the app reading it, Wispr's chords muted, the relay's recorder on the
    Loopback, Engine = Wispr. Returns the FakeWisprDB."""
    db = fw.FakeWisprDB(FAKE_DB).create()
    DESK["db"] = db
    _env_block(["WT_WISPR_DB=" + FAKE_DB])
    post("/test/wispr-chord", {"mute": True, "seconds": 300})
    if not wait_for(lambda: state()["wisprLive"]["db"] == FAKE_DB, 5):
        raise RuntimeError("the app did not pick up WT_WISPR_DB within 5 s")
    try:
        mic_override(LOOPBACK)
    except Exception:
        pass
    if engine_wispr and not set_engine("wispr"):
        raise RuntimeError("POST /engine wispr was not taken")
    return db

def desk_off():
    """After every case (harness CLEANUPS): a capture still standing on a fake row is let go
    first (its row made terminal), then the real `flow.sqlite` and live chords are back."""
    try:
        db = DESK.get("db")
        if db:
            live = state().get("wisprLive") or {}
            if live.get("captureOpen") and live.get("newestRowId"):
                db.update(live["newestRowId"], status="dismissed")
                wait_for(lambda: not state()["wisprLive"]["captureOpen"], 8, 0.3)
        DESK["db"] = None
        _env_block(None)
        s = state()
        if (s.get("wisprLive") or {}).get("chordsMuted"):
            post("/test/wispr-chord", {"mute": False})
        if (s.get("wisprLive") or {}).get("db"):
            wait_for(lambda: state()["wisprLive"]["db"] is None, 3)
    except Exception as e:
        print(f"  (desk_off: {type(e).__name__}: {e})")

CLEANUPS.append(desk_off)

def chord(post_=None, state_=None):
    return post("/test/wispr-chord", {"post": post_ or "none", "state": state_ or "none"})[1]

def live():
    return state()["wisprLive"]

def open_sentence(db, adopt=True):
    """The relay's own Wispr gesture (no chord on the wire) and, as Wispr does at the gesture,
    a row with `status` NULL. Returns the rowid (None with `adopt=False`: no row)."""
    chord(state_="start")
    if not wait_for(lambda: state()["listening"], 3):
        raise RuntimeError("the relay did not open the sentence")
    if not adopt:
        return None
    rid = db.insert(at=time.time())
    if not wait_for(lambda: live()["captureRow"] == rid, 3):
        raise RuntimeError(f"fake row {rid} was not adopted (captureRow {live()['captureRow']})")
    return rid

def close_sentence(db, rid, text=None, status="formatted"):
    chord(state_="stop")
    db.update(rid, status="processing", speech=1.5)
    if text is not None:
        time.sleep(0.3)
        db.finish(rid, text, status=status)

def wav_count():
    return len(glob.glob(os.path.join(CACHES, "**", "wispr-*.wav"), recursive=True))


# ---------------------------------------------------------------- TW1–TW3: the held right ⌘⌥ (W-D1, W-C6)
@case("TW1", tags=("gesture", "desk"), engine="wispr", pre=needs_standalone(True),
      expect="right ⌘⌥ held 3 s on Engine=Wispr stays one sentence: no 🧼 release before the real one, listening ≥ 2.5 s")
def tw1():
    """W-D1 / W-C6a (desk). Standalone ON, Engine = Wispr: the held pair is `onCleanHold` →
    `wisprSource.start()` → `postWisprHandsFree`, whose trailing `flagsChanged []` (muted here to
    that tail alone) carries no right-hand bits — read by the PTT branch as the pair's release
    ≈ 0.25 s after the press → quiet cancel. Held with `/test/modifiers` (unstamped, device bits).
    Cancelled before the real release so nothing lands at his caret."""
    desk()
    post("/test/key-trace", {"on": True})
    mark = log_mark(); t0 = time.time()
    post("/test/modifiers", {"keys": [54, 61], "holdMs": 3000})
    seen = []
    while time.time() - t0 < 2.6:
        s = state(); seen.append((round(time.time() - t0, 2), s["listening"]))
        time.sleep(0.1)
    post("/test/cancel")
    wait_for(lambda: not state()["listening"], 3)
    time.sleep(0.8)   # the real release at 3.0 s
    post("/test/key-trace", {"on": False})
    txt = log_since(mark)
    held = "🧼 right ⌘⌥ held" in txt
    i_rel, i_cancel = txt.find("🧼 right ⌘⌥ released"), txt.find("cancelled via POST /test/cancel")
    early = i_rel >= 0 and (i_cancel < 0 or i_rel < i_cancel)
    quiet = re.search(r"dictation cancelled via (?!POST /test/cancel)([^\n]*)", txt)
    up = [t for t, l in seen if l]
    lasted = (up[-1] - up[0]) if up else 0
    note = f"held seen {held}; listening from {up[0] if up else '-'} s for {lasted:.1f} s; " \
           f"release line before the case's cancel {early}; other cancel: {quiet.group(1)[:60] if quiet else None}"
    if not held:
        return "FAIL", "the tap never saw the pair — " + note
    if early or lasted < 2.3:
        return "BUG", note
    return "PASS", note

@case("TW2", tags=("gesture", "desk", "unit"), pre=lambda: None if "wisprLive" in state() else "no Wispr hooks in this build",
      expect="a stamped flagsChanged [] under a held right ⌘⌥ is not its release")
def tw2():
    """W-D1 as a unit test (GW6 → `/test/modifiers {"keys": [], "stamped": true}`): hold right
    ⌘⌥ (unstamped, device bits), post one **stamped** `flagsChanged []` 200 ms in — the tail every
    chord this app posts ends with — and read whether the PTT branch fired `.release`. Local
    engine (no Wispr needed); cancelled before the real release."""
    mic_override(LOOPBACK)
    mark = log_mark()
    post("/test/modifiers", {"keys": [54, 61], "holdMs": 1500})
    time.sleep(0.2)
    post("/test/modifiers", {"keys": [], "stamped": True})
    time.sleep(0.7)
    txt = log_since(mark)
    post("/test/cancel")
    time.sleep(1.0)
    held = "🧼 right ⌘⌥ held" in txt
    released = "🧼 right ⌘⌥ released" in txt
    if not held:
        return "FAIL", "the held pair never reached the tap (Secure Input? sessionFlags %s)" % state()["sessionFlags"]
    if released:
        return "BUG", "the stamped flagsChanged [] 0.2 s into the hold was read as the release (no stamp check in the PTT branch)"
    return "PASS", "the stamped tail was ignored; the pair stayed held"

@case("TW3", tags=("gesture", "audio"), engine="wispr", lab_only=True, pre=needs_standalone(False),
      expect="standalone OFF, right ⌘⌥ held 2 s: a Wispr row within 1 s, or a flash — never a 12 s ring")
def tw3():
    """W-D1 (standalone OFF) / W-C7: the pair goes to the Wispr PTT branch while Wispr's own
    `ptt` is elsewhere (61+60 since Q23) → no row → the ring stands 12 s (`speculativeGrace`),
    then *ignored*."""
    e = engine()
    mark = log_mark()
    post("/test/modifiers", {"keys": [54, 61], "holdMs": 2000})
    time.sleep(3.0)
    s = state()
    txt = log_since(mark)
    row = "wispr history: row" in txt
    note = f"wisprShortcuts.ptt {e.get('wisprShortcuts', {}).get('ptt')}; row {row}; ringUp at +3 s {s['ringUp']}"
    wait_for(lambda: not state()["ringUp"], 15)
    if row or not s["ringUp"]:
        return "PASS", note
    return "BUG", note


# ---------------------------------------------------------------- TW4–TW5: the cold, deaf opening (W-D2, W-A1)
@case("TW4", tags=("gesture", "audio", "cold"), engine="wispr", lab_only=True, pre=needs_wispr,
      expect="a cold Wispr: the first 3 s he says reach the witness; the chip names the warming")
def tw4():
    """W-D2 (lab): relaunch Wispr, 🔼→ within 1 s of `ready`, 12 s of speech; sample the state
    at 20 Hz — every `listening` sample while `wispr.state == warming` is a moment the chip lied."""
    post("/test/wispr-proc", {"relaunch": True})
    if not wait_for(lambda: engine()["ready"] and wispr_pid(), 30, 0.2):
        return "ERROR", "Wispr did not come back within 30 s"
    bind_witness(); witness_clear()
    mic_override(LOOPBACK)
    mark = log_mark(); gesture("forward-right")
    samples = []
    import threading
    stop = threading.Event()
    def poll():
        while not stop.is_set():
            try:
                s = state(); samples.append((s["listening"], s["wispr"]["state"], s["historyRow"], list(s["chip"])))
            except Exception:
                pass
            time.sleep(0.05)
    th = threading.Thread(target=poll, daemon=True); th.start()
    time.sleep(0.2); play(CLIP_SPEECH); time.sleep(1.0)
    gesture("forward-right")
    wait_delivered(mark, 45); stop.set(); th.join(2)
    lie = [x for x in samples if x[0] and x[1] == "warming" and x[2] is None]
    first = open(os.path.splitext(CLIP_EN_LONG)[0] + ".txt", errors="replace").read().split()[:5] \
        if os.path.exists(os.path.splitext(CLIP_EN_LONG)[0] + ".txt") else []
    got = witness_text().lower()
    head = sum(1 for w in first if re.sub(r"\W", "", w.lower()) in got)
    named = any(re.search(r"warm|waking|starting", " ".join(x[3]), re.I) for x in lie)
    note = f"{len(lie)}/{len(samples)} samples listening+warming+no row ({len(lie) * 0.05:.1f} s); first-5-words hit {head}/{len(first)}; chip named it {named}"
    return ("PASS" if head >= max(1, len(first) - 1) and (not lie or named) else "BUG"), note

@case("TW5", tags=("desk",), engine="wispr", pre=needs_desk,
      expect="while Wispr has no row and no microphone, the chip does not say Listening (or names the warming)")
def tw5():
    """W-D2 / W-A1 (desk): the relay's own gesture with the chord muted and no row — Wispr
    never heard it — polled at 20 Hz for 3 s. Documents the lie: `listening` + chip `Listening`
    + a breathing ring over `wispr.state == warming` with `historyRow == null`. Expected BUG."""
    db = desk()
    open_sentence(db, adopt=False)
    t0, lie, n, rows = time.time(), 0, 0, set()
    while time.time() - t0 < 3:
        s = state(); n += 1
        if s["listening"] and s["wispr"]["state"] == "warming" and s["historyRow"] is None:
            lie += 1
            rows.update(r for r in s["chip"] if r)
        time.sleep(0.05)
    post("/test/cancel")
    # Any row but one naming the wait is a claim of a live sentence ("Listening to …",
    # "Prompting to … →", measured 2026-09-28 09:03: the chip said *Prompting to* for 40/40).
    named = any(re.search(r"warm|waking|starting|waiting for wispr", r, re.I) for r in rows)
    note = f"{lie}/{n} samples listening while warming with no row; chip rows then: {sorted(rows)[:3]}"
    if lie and rows and not named:
        return "BUG", note
    return "PASS", note


# ---------------------------------------------------------------- TW6–TW7: the relay's WAV on every failure (W-D3, W-B3)
def _tw6(kind):
    def fn():
        """W-D3 / W-B3 (lab, audio): the relay's own recording of the sentence on a Wispr failure —
        (a) 🔼← mid-sentence, (b) 🔼← 0.3 s after the stop, (c) Wispr killed 0.2 s after the stop,
        (d) as (c) with a shot and the witness bound (no bare screenshot message)."""
        bind_witness(); witness_clear(); mic_override(LOOPBACK)
        n0 = wav_count(); mark = log_mark()
        gesture("forward-right")
        if not wait_for(lambda: log_has(mark, r"opening the dictation"), 8):
            return "ERROR", "the sentence never opened"
        if kind == "d":
            post("/test/area", {})
        import threading
        th = threading.Thread(target=lambda: play(CLIP_SPEECH, seconds=6), daemon=True); th.start()
        time.sleep(3.0)
        if kind == "a":
            gesture("forward-left")
        th.join(10)
        if kind != "a":
            gesture("forward-right"); time.sleep(0.2 if kind in "cd" else 0.3)
            if kind == "b":
                gesture("forward-left")
            else:
                post("/test/wispr-proc", {"kill": True})
        time.sleep(3.0)
        s = state()
        txt = log_since(mark)
        n1 = wav_count()
        bare = kind == "d" and re.search(r"screenshot", witness_text(), re.I) is not None
        note = (f"recoverable {bool(s['recoverable'])}; 'nothing had been recorded' {('nothing had been recorded' in txt)}; "
                f"wispr-*.wav {n0}→{n1}; lastFailure {s['lastFailure']}" + (f"; bare screenshot message {bare}" if kind == "d" else ""))
        if kind in "cd":
            post("/test/wispr-proc", {"relaunch": True}); wait_for(lambda: wispr_pid(), 30)
        ok = s["recoverable"] and n1 == n0 and not bare
        return ("PASS" if ok else "BUG"), note
    return fn

for _k in "abcd":
    case("TW6" + _k, tags=("gesture", "audio"), engine="wispr", lab_only=True, pre=needs_wispr,
         expect="the relay's WAV reaches Recover; no orphan wispr-*.wav" + ("; no bare screenshot message" if _k == "d" else ""))(_tw6(_k))

@case("TW7", tags=("desk",), engine="wispr", pre=needs_desk,
      expect="a cancelled / abandoned Wispr sentence leaves its WAV to Recover, no orphan file, no false 'nothing recorded'")
def tw7():
    """W-D3 / W-B3 (desk): (a) cancel while listening — the relay's meter WAV is deleted and the
    log says *nothing had been recorded yet*; (b) cancel in the settle — the WAV is orphaned;
    (c) only with `WT_ALLOW_WISPR_KILL=1` or in the lab: Wispr relaunched mid-settle
    (`/test/wispr-proc {"relaunch"}`) → *the sentence is lost* while the audio is on disk."""
    db = desk()
    parts, bugs = [], 0
    # (a)
    n0, mark = wav_count(), log_mark()
    rid = open_sentence(db); time.sleep(1.5)
    post("/test/cancel"); wait_for(lambda: not state()["listening"], 3); time.sleep(1.0)
    s, txt = state(), log_since(mark)
    db.update(rid, status="dismissed")                  # Wispr's answer to the ⌃Esc: the capture lets go
    wait_for(lambda: not live()["captureOpen"], 8, 0.3)
    a_bug = not s["recoverable"] or "nothing had been recorded" in txt
    bugs += a_bug
    parts.append(f"(a) recoverable {bool(s['recoverable'])}, 'nothing had been recorded' {'nothing had been recorded' in txt}, wav {n0}→{wav_count()}")
    # (b)
    n0, mark = wav_count(), log_mark()
    rid = open_sentence(db); time.sleep(1.5)
    close_sentence(db, rid)
    wait_for(lambda: state()["settling"] or live()["captureOpen"], 2)
    post("/test/cancel"); time.sleep(0.5)
    db.update(rid, status="dismissed")
    wait_for(lambda: not live()["captureOpen"], 8, 0.3); time.sleep(0.5)
    s = state(); n1 = wav_count()
    b_bug = not s["recoverable"] or n1 > n0
    bugs += b_bug
    parts.append(f"(b) recoverable {bool(s['recoverable'])}, wav {n0}→{n1}")
    # (c)
    if KILL_OK:
        n0, mark = wav_count(), log_mark()
        rid = open_sentence(db); time.sleep(1.5)
        close_sentence(db, rid)
        post("/test/wispr-proc", {"relaunch": True})
        wait_for(lambda: log_has(mark, r"Wispr Flow quit"), 8)
        time.sleep(1.0)
        s, txt = state(), log_since(mark)
        n1 = wav_count()
        c_bug = "the sentence is lost" in txt and (not s["recoverable"] or n1 > n0)
        bugs += c_bug
        parts.append(f"(c) 'the sentence is lost' {'the sentence is lost' in txt}, recoverable {bool(s['recoverable'])}, wav {n0}→{n1}")
        wait_for(lambda: wispr_pid(), 30)
    else:
        parts.append("(c) not run — kills his Wispr: WT_ALLOW_WISPR_KILL=1 or the lab")
    return ("BUG" if bugs else "PASS"), "; ".join(parts)


# ---------------------------------------------------------------- TW8–TW11: his own sentence vs the relay's (W-D4..D7, W-C4, W-B1)
def his_ptt_keys():
    """Wispr's own push-to-talk as its config says (`/engine.wisprShortcuts.ptt`): right ⌥⇧
    `61+60` since Q23 (2026-09-28), right ⌘⇧ `54+60` before."""
    ptt = (engine().get("wisprShortcuts") or {}).get("ptt") or "61+60"
    return [int(k) for k in ptt.split("+")]

def _his_ptt(seconds, clip=None):
    """His Wispr push-to-talk held for `seconds`, optionally with a clip."""
    post("/test/modifiers", {"keys": his_ptt_keys(), "holdMs": int(seconds * 1000)})
    if clip:
        time.sleep(0.4); play(clip)
    time.sleep(max(0, seconds - (0.4 if clip else 0)) + 0.3)

@case("TW8a", tags=("gesture", "audio"), engine="wispr", lab_only=True, pre=needs_standalone(True),
      expect="his own ptt sentence 1 s after the relay's lands at the caret, not in the witness or the outbox")
def tw8a():
    """W-D4 / W-C4 (lab): inside the relay-owned window (gesture → idle + 10 s) his own Wispr ⌘V
    is dropped and rescued into the bound terminal."""
    return _tw8(1.0)

@case("TW8b", tags=("gesture", "audio"), engine="wispr", lab_only=True, pre=needs_standalone(True),
      expect="his sentence 5 s after the relay's delivery (the 10 s tail) is Wispr's paste, no 🛡️ rescue")
def tw8b():
    """W-D4 (lab): the 10 s tail after the relay's sentence went idle."""
    return _tw8(5.0, after_delivery=True)

def _tw8(delay, after_delivery=False):
    bind_witness(); witness_clear(); mic_override(LOOPBACK)
    n0 = outbox_count(); mark = log_mark()
    dictate_loopback(CLIP_EN)
    if after_delivery:
        wait_delivered(mark, 40)
    time.sleep(delay)
    m2 = log_mark()
    _his_ptt(4.5, CLIP_EN)
    time.sleep(6)
    txt = log_since(m2)
    rescued = "🛡️ ⌘V from" in txt and "dropped" in txt
    passed = "its own sentence (standalone, Q9)" in txt
    extra = outbox_count() - n0
    note = f"outbox +{extra} (the relay's sentence is 1); rescue/drop line {rescued}; Wispr's own paste passed {passed}"
    return ("PASS" if passed and not rescued and extra <= 1 else "BUG"), note

@case("TW9", tags=("gesture", "audio"), engine="wispr", lab_only=True, pre=needs_standalone(True),
      expect="🔼→ during his own Wispr sentence (his ptt held): 'one engine at a time', no chord posted")
def tw9():
    """W-D5 (lab): `startDictation`'s exclusivity check is skipped on Engine = Wispr, and under Q9
    his sentence never sets `isRecording` — the relay posts its toggle into his PTT."""
    bind_witness(); mic_override(LOOPBACK)
    post("/test/key-trace", {"on": True})
    mark = log_mark()
    post("/test/modifiers", {"keys": his_ptt_keys(), "holdMs": 5000})
    time.sleep(1.5)
    gesture("forward-right")   # 🔼→ = ⌘⌃D's path (toggleDictation)
    time.sleep(4.5)
    post("/test/key-trace", {"on": False})
    txt = log_since(mark)
    refused = re.search(r"one engine at a time|Wispr Flow is listening", txt) is not None
    opened = "opening the dictation on the gesture" in txt
    return ("PASS" if refused and not opened else "BUG"), f"refused {refused}; relay opened a sentence {opened}"

@case("TW10", tags=("gesture", "cold"), engine="wispr", lab_only=True, pre=needs_wispr,
      expect="a stop 1 s into a cold Wispr leaves no ghost dictation: no row with words, nothing delivered for 40 s")
def tw10():
    """W-D6 / W-A4 / W-B8 (lab): the toggle posted blind before a cold Wispr opened anything."""
    post("/test/wispr-proc", {"relaunch": True})
    wait_for(lambda: engine()["ready"] and wispr_pid(), 30, 0.2)
    bind_witness(); witness_clear(); mic_override(LOOPBACK)
    before = live()["newestRowId"]; last0 = state()["lastDelivery"]
    gesture("forward-click"); time.sleep(1.0); gesture("forward-click")
    time.sleep(0.5); play(CLIP_EN)
    time.sleep(40)
    s = state(); lv = live()
    ghost = lv["newestRowId"] != before and (lv["newestRowText"] or 0) > 0
    note = f"new row with words {ghost}; lastDelivery changed {s['lastDelivery'] != last0}; witness {len(witness_text())} chars"
    return ("PASS" if not ghost and s["lastDelivery"] == last0 and not witness_text().strip() else "BUG"), note

@case("TW11", tags=("gesture", "audio"), engine="wispr", lab_only=True, pre=needs_standalone(False),
      expect="two overlapping Wispr sentences: A with its own shot in the witness, B delivered or held, never lost")
def tw11():
    """W-D7 / W-B1 (lab, standalone OFF): his own chord 0.3 s after the relay's stop."""
    bind_witness(); witness_clear(); mic_override(LOOPBACK)
    mark = log_mark(); n0 = outbox_count()
    gesture("forward-right"); time.sleep(0.5)
    post("/test/area", {}); play(CLIP_SPEECH, seconds=8)
    gesture("forward-right"); time.sleep(0.3)
    post("/test/wispr-handsfree", {"hand": True}); play(CLIP_EN, seconds=1.5)
    post("/test/wispr-handsfree", {"hand": True})
    time.sleep(40)
    txt = log_since(mark)
    lost = "No words came back" in txt
    n = outbox_count() - n0
    return ("PASS" if n >= 2 and not lost else "BUG"), f"outbox +{n}; 'No words came back' {lost}"


@case("TW12", tags=("desk",), engine="wispr", pre=needs_desk,
      expect="two Wispr sentences overlapping on an ungated path: both delivered, in spoken order")
def tw12():
    """W-D7 / W-B1 / W-A5 (desk): sentence A in the settle (row `processing`), a second sentence
    opened on an ungated path (the relay's own gesture straight into the source — what a mic
    edge or his chord does with standalone off), row B `formatted` **before** A. D predicts the
    new sentence keeps A's capture, B's row is never adopted and B is lost after 30 s."""
    db = desk()
    bind_witness(); witness_clear()
    ra = open_sentence(db); time.sleep(0.8)
    close_sentence(db, ra)
    time.sleep(0.5)
    mark = log_mark()
    chord(state_="start")                               # B, ungated
    wait_for(lambda: state()["listening"], 3)
    rb = db.insert(at=time.time()); time.sleep(1.0)
    chord(state_="stop")
    db.finish(rb, "tw twelve sentence bee")
    time.sleep(1.0)
    db.finish(ra, "tw twelve sentence ay")
    wait_for(lambda: "sentence bee" in witness_text() and "sentence ay" in witness_text(), 36, 0.5)
    got = witness_text()
    ia, ib = got.find("sentence ay"), got.find("sentence bee")
    txt = log_since(mark)
    note = f"A at {ia}, B at {ib} in the witness; 'No words came back' {'No words came back' in txt}"
    if ia >= 0 and ib >= 0 and ia < ib:
        return "PASS", note
    return "BUG", note


# ---------------------------------------------------------------- TW13–TW16: panel, refusals, not running (W-D8..D10)
@case("TW13", tags=("desk",), engine="wispr", pre=needs_desk,
      expect="a Wispr sentence does not force-send a held panel being edited; A then B, in order")
def tw13():
    """W-D8 / W-C11 (desk): Autosend off, panel A held (`/test/dictation`) and opened for
    editing; a Wispr sentence B lands — `showSentPrompt` → `resolvePrompt(send: true)` sends A
    as it stands (F4: Wispr's answers skip `runAnswer`'s panel rule)."""
    db = desk()
    bind_witness(); witness_clear()
    autosend0 = bool(state().get("autosend"))
    post("/test/autosend", {"on": False})
    try:
        post("/test/dictation", {"text": "tw thirteen panel ay"})
        if not wait_for(lambda: (state().get("prompt") or {}).get("held"), 8):
            return "ERROR", "panel A never held"
        post("/test/prompt", {"do": "edit"})
        rb = open_sentence(db); time.sleep(0.8)
        close_sentence(db, rb, "tw thirteen wispr bee")
        time.sleep(3.0)
        s = state(); got = witness_text()
        a_sent = "panel ay" in got
        held = (s.get("prompt") or {}).get("held")
        note = f"A in the witness before its send {a_sent}; panel held {held}; prompt text {str((s.get('prompt') or {}).get('text'))[:40]!r}"
        verdict = "BUG" if a_sent else "PASS"
        if held:
            post("/test/prompt", {"do": "send"}); time.sleep(2.0)
            post("/test/prompt", {"do": "send"}); time.sleep(1.0)
        return verdict, note
    finally:
        post("/test/autosend", {"on": autosend0})
        if (state().get("prompt") or {}).get("held"):
            post("/test/prompt", {"do": "cancel"})

@case("TW14", tags=("desk", "gesture"), engine="wispr", pre=needs_desk,
      expect="🔼→ during Wispr's settle is refused on the chip (the wait named), not only in the log")
def tw14():
    """W-D9 (desk): Engine = Wispr does not queue (F3) — a start in the settle is refused with a
    log line and nothing on the chip; ElevenLabs would open a queued sentence."""
    db = desk()
    bind_witness()
    rid = open_sentence(db); time.sleep(0.8)
    close_sentence(db, rid)
    wait_for(lambda: state()["settling"], 3)
    mark = log_mark()
    gesture("forward-right")
    rows = set()
    t0 = time.time()
    while time.time() - t0 < 1.5:
        rows.update(r for r in state()["chip"] if r); time.sleep(0.1)
    txt = log_since(mark)
    db.finish(rid, "tw fourteen")
    wait_for(lambda: not state()["busy"], 10)
    second = "opening the dictation on the gesture" in txt
    named = any(re.search(r"in flight|one sentence at a time|still (coming|transcribing)|wait", r, re.I) for r in rows)
    note = f"second sentence opened {second}; chip named the wait {named}; refusal logged {'refused' in txt or 'in flight' in txt}"
    if second:
        return "FAIL", note
    return ("PASS" if named else "BUG"), note

@case("TW15", tags=("gesture",), engine="wispr", pre=lambda: needs_wispr() or (None if KILL_OK else "stops his Wispr: WT_ALLOW_WISPR_KILL=1 or the lab"),
      expect="with Wispr quit, 🔼↑ leaves no spawnPending and no folder menu; ⌘⌃D flashes 'not running'")
def tw15():
    """W-D10 (lab, or the desk with `WT_ALLOW_WISPR_KILL=1`): `startDictation` sets the spawn /
    paste flags and opens the folder menu **before** `source.start()` refuses."""
    post("/test/wispr-proc", {"kill": True})
    wait_for(lambda: not wispr_pid(), 5)
    try:
        mark = log_mark()
        gesture("forward-up"); time.sleep(0.8)
        s = state()
        gesture("forward-left")   # close whatever opened
        txt = log_since(mark)
        note = f"spawnPending {s['spawnPending']}; 'not running' {'not running' in txt}"
        return ("BUG" if s["spawnPending"] else "PASS"), note
    finally:
        post("/test/wispr-proc", {"relaunch": True}); wait_for(lambda: wispr_pid(), 30)

@case("TW16", tags=("gesture",), engine="wispr", lab_only=True, pre=needs_wispr,
      expect="only Wispr's helper alive: ⌘⌃D says 'not running', never 'the sentence is lost'")
def tw16():
    """W-D10 (lab): `isReady` matches the bundle-id prefix (the helper too) while death is judged
    on the anchored main executable."""
    post("/test/wispr-proc", {"kill": True})
    wait_for(lambda: not wispr_pid(), 5)
    helper = subprocess.run(["pgrep", "-f", "swift-helper-app-dist/Wispr Flow.app"], capture_output=True, text=True).stdout.split()
    try:
        if not helper:
            return "SKIP", "no helper survived the main process"
        mark = log_mark(); gesture("forward-right"); time.sleep(1.5)
        txt = log_since(mark)
        return ("BUG" if "the sentence is lost" in txt else "PASS"), f"'not running' {'not running' in txt}; 'lost' {'the sentence is lost' in txt}"
    finally:
        post("/test/wispr-proc", {"relaunch": True}); wait_for(lambda: wispr_pid(), 30)


# ---------------------------------------------------------------- TW17–TW21
@case("TW17", tags=("gesture", "audio"), engine="wispr", lab_only=True, pre=needs_wispr,
      expect="a Wispr corpus row is written only when Wispr's micDevice is the relay's device")
def tw17():
    """W-D11 (lab): the corpus pairs the relay meter's WAV with Wispr's text from another mic."""
    corpus = os.path.join(HOME, "voice-corpus", "corpus.jsonl")
    n0 = sum(1 for _ in open(corpus)) if os.path.exists(corpus) else 0
    bind_witness(); mic_override("Built-in")   # the relay on another input than Wispr's BlackHole
    mark = log_mark(); dictate_loopback(CLIP_EN); wait_delivered(mark, 40)
    time.sleep(2)
    rows = open(corpus).read().splitlines()[n0:] if os.path.exists(corpus) else []
    wis = [json.loads(r) for r in rows if '"wispr"' in r]
    s = state()
    note = f"new wispr corpus rows {len(wis)}; micOpened {s['micOpened']}; Wispr's mic {rows and wis and wis[-1].get('device')}"
    return ("BUG" if wis else "PASS"), note

@case("TW18", tags=("desk",), pre=needs_desk,
      expect="after a pick away from Wispr the Engine list still offers Wispr")
def tw18():
    """W-D12 (host, Codex): the Engine submenu lists Wispr only while it is the engine. No route
    reads the menu's rows (only `micRowsForTest`), so this stays a Codex check (S1)."""
    return "SKIP", "no route reads the Engine menu's rows — a Codex menu check (D-state S1)"

@case("TW19", tags=("desk",), pre=needs_desk,
      expect="/engine refused while listening / settling; accepted in state X with the swallow standing and nothing delivered")
def tw19():
    """Engine switch × Wispr state (desk, D §1 row `POST /engine`): mid `listening` and in the
    settle the switch is refused and `source` stays Wispr; after a cancel in the settle (state X,
    a discarding capture) it is accepted, the capture keeps swallowing and the late row delivers
    nothing."""
    db = desk()
    bind_witness(); witness_clear()
    parts, bad = [], []
    rid = open_sentence(db)
    _, r = post("/engine", {"id": "whisper"}); s = state()
    parts.append(f"L: engine→{r.get('engine')}, source {s['source']}")
    if r.get("engine") == "whisper":
        bad.append("L")
    close_sentence(db, rid)
    wait_for(lambda: state()["settling"], 3)
    _, r = post("/engine", {"id": "whisper"}); s = state()
    parts.append(f"S: engine→{r.get('engine')}, source {s['source']}")
    if r.get("engine") == "whisper":
        bad.append("S")
    post("/test/cancel"); time.sleep(0.5)
    ok = set_engine("whisper", 5)
    lv = live(); n0 = outbox_count(); last0 = state()["lastDelivery"]
    parts.append(f"X: switched {ok}, capture still open {lv['captureOpen']} (discarding {lv['discarding']})")
    db.finish(rid, "tw nineteen must not arrive")
    time.sleep(6)
    arrived = "nineteen" in witness_text() or state()["lastDelivery"] != last0 or outbox_count() != n0
    parts.append(f"late row delivered {arrived}")
    if not ok or arrived:
        bad.append("X")
    return ("PASS" if not bad else "FAIL"), "; ".join(parts)

@case("TW20", tags=("gesture", "audio"), engine="wispr", lab_only=True, pre=needs_wispr,
      expect="Wispr killed mid-sentence: listening/settling down within 0.6 s, a flash; the next 🔼→ delivers")
def tw20():
    """Wispr quit mid-sentence (lab; D TW20, W-B3 row *quit*)."""
    bind_witness(); witness_clear(); mic_override(LOOPBACK)
    mark = log_mark(); gesture("forward-right")
    time.sleep(0.5)
    import threading
    th = threading.Thread(target=lambda: play(CLIP_SPEECH, seconds=5), daemon=True); th.start()
    time.sleep(2.0)
    post("/test/wispr-proc", {"kill": True}); t0 = time.time()
    down = wait_for(lambda: not state()["listening"] and not state()["settling"], 5, 0.05)
    dt = time.time() - t0
    th.join(10)
    post("/test/wispr-proc", {"relaunch": True})
    wait_for(lambda: engine()["ready"] and wispr_pid(), 30)
    time.sleep(3)
    witness_clear(); m2 = log_mark()
    dictate_loopback(CLIP_EN); wait_delivered(m2, 40)
    ok2 = bool(witness_text().strip())
    note = f"down in {dt:.2f} s ({bool(down)}); next sentence delivered {ok2}; capture {live()['captureOpen']}"
    return ("PASS" if down and dt <= 0.6 and ok2 else "BUG"), note

@case("TW21", tags=("gesture", "audio"), engine="eleven", pre=lambda: None if "wisprLive" in state() else "no hooks",
      expect="after /test/dictation/start {clock} + cancel, a real sentence's marker cue is on the recorder's ruler")
def tw21():
    """D §W-D13 note (desk, Engine ElevenLabs → the fake Scribe): `/test/dictation/start
    {"clock": true}` swaps `markerClock` for the wall clock and nothing puts it back until the
    next `wireDictationSource` — a real sentence after it files its shot at the wall clock's
    offset, not the recorder's (off by the microphone's open latency)."""
    post("/test/dictation/start", {"clock": True}); time.sleep(0.5)
    post("/test/cancel"); wait_for(lambda: not state()["listening"], 5); time.sleep(1.0)
    mic_override(LOOPBACK)
    mark = log_mark()
    gesture("forward-right")
    t_mic = wait_for(lambda: log_has(mark, r"mic: recording through") and time.time(), 8, 0.02)
    started = state().get("dictationStartedAt")
    if not t_mic or not started:
        post("/test/cancel")
        return "ERROR", "the recorder never opened"
    time.sleep(1.2)
    t_shot = time.time()
    post("/test/area", {})
    play(CLIP_EN)
    gesture("forward-right")
    wait_delivered(mark, 40)
    m = re.search(r"⏱️ marker cue: \S+ \d+ at ([\d.]+)s", log_since(mark))
    if not m:
        return "FAIL", "no marker cue line"
    cue = float(m.group(1))
    st = datetime.datetime.fromisoformat(started.replace("Z", "+00:00")).timestamp()
    wall, rec = t_shot - st, t_shot - t_mic
    note = f"cue {cue:.2f} s; wall-clock offset {wall:.2f} s; recorder offset ≈ {rec:.2f} s (±0.1)"
    if abs(wall - rec) < 0.15:
        return "SKIP", note + " — the mic opened within 0.15 s of the gesture; the two rulers cannot be told apart"
    if abs(cue - rec) <= 0.15:
        return "PASS", note
    if abs(cue - wall) <= 0.15:
        return "BUG", note
    return "FAIL", note
