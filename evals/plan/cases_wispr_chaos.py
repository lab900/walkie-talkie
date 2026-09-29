"""**Wispr chaos** — TX1–TX13 (2026-09-28): the adversarial suite. Where `cases_wispr.py` (TW)
asserts one path and `cases_wispr_soak.py` (TS) counts rates, these break something on purpose
at the worst moment — Wispr frozen mid-upload, killed mid-sentence, its network cut, its History
DB locked, the relay itself restarted with a row in flight, chords doubled, cancels at every
offset — and assert the relay's promises still hold: **a sentence is delivered once or loudly
not at all** (Recover / a failure / a refusal), **never twice, never into the next sentence,
never stuck** (`listening`, `isRecording`, a capture) and **no ghost microphone afterwards**.

Engine = Wispr for every case. All but TX12d are `lab_only`: the real Wispr Flow in the Tart
guest on BlackHole 2ch (`docs/vm-lab.md`, `docs/vm-wispr.md`), where Wispr may be frozen, killed
and relaunched and the network cut. **TX12d is the one desk variant**: the History lock needs no
real Wispr, the fake `flow.sqlite` (`fake_wispr_db.py`, rollback journal) is locked instead.

Each docstring names the finding it attacks (`evals/plan/wispr/README.md` W1–W23; the lab report
`evals/plan/vm/wispr/report-lab-2026-09-28.md` findings 1–4; the journal's Q14–Q24).

**The hooks** (`.claude/rules/desk-testing.md`): `/test/wispr-proc` (stop / cont / kill /
relaunch), `/test/wispr-chord` (chord and belief decoupled), `/test/modifiers` (his `61+60`),
`/test/state.wisprLive` and `.pasteboard`, `WT_WISPR_DB`. Every case's `pre` asks for Wispr
running and the hooks it uses; a build without one SKIPs with the hook's name.

**The network cut** (`net_cut`): an anchor `com.apple/wt-chaos` with `block drop out quick proto
{tcp udp} to any port 443` (QUIC too), pf enabled by reference (`pfctl -E` token), the 443
states already open killed so a keep-alive cannot ride past the rule, and a curl probe that must
fail — else the case ERRORs rather than claiming a cut that never was. The rule is lifted by
(1) a timer at `seconds`, (2) the case's `finally`, (3) `CLEANUPS` after every case, and (4) a
detached **root dead-man** (`sudo sh -c 'sleep N+10; pfctl … -F rules'`) that survives a SIGKILLed
harness (the phase cap is `rc=137`) — disarmed by deleting its nonce file on a normal restore.
Refuses to run outside the guest. Needs passwordless `sudo` (the guest has it).

Freezing Wispr for longer than the route's 60 s ceiling (TX13) uses `os.kill(SIGSTOP)` with a
detached `sleep N; kill -CONT` dead-man the same way; `CLEANUPS` thaws it too.

Verdicts: **PASS** = the promise held · **BUG** = a finding predicted open reproduced (W11's cold
losses, the ghost microphone, W4's overlap) · **FAIL** = a promise broken that nothing predicted
(a double, a stray delivery, a stuck flag) · **ERROR** = the rig did not do what it claimed.
Wispr-side losses the relay covered (Q14 fallback, Recover) are PASS with the loss counted in
the evidence. Finding 1 (`typed keys never showed … do script, which presses Return` into the
`cat` witness) is annotated wherever a witness count is judged, since it can double a copy."""
import os, re, signal, sqlite3, subprocess, threading, time, wave
from harness import *
from cases_wispr import (needs_wispr, needs_desk, wispr_pid, his_ptt_keys, KILL_OK, desk, open_sentence,
                         chord, live, FAKE_DB)
from cases_wispr_soak import (_tokens, recall, ref_words, doubled, _really_busy, _quiet, _unstick, _mic_open,
                              _relaunch_wispr, _clear_ghost, _seconds, te_open, te_front, te_text, te_clear,
                              te_close)
import fake_wispr_db as fw

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHAOS = {"touched": False, "frozen": None, "db_release": []}
DEVNULL = subprocess.DEVNULL
# Lines that say a sentence ended without words (Q14 / Recover / refusals), for `_ended`.
FAIL_RE = (r"No words came back|No speech|no speech|sentence is lost|kept for Recover|dictation abandoned|"
           r"nothing had been recorded|dictation cancelled|🗑️ dictation cancelled")
REFUSE_RE = r"dictate gesture refused|start refused|one engine at a time|already open|one sentence at a time"
RETURN_FALLBACK = "typed keys never showed"      # lab finding 1


# ---------------------------------------------------------------- preconditions
HOOKS = {}

def _route_there(path):
    """400 = the route is there and refused the empty body; 404 = not in this build. Probed with
    `{}`: `/test/wispr-proc` and `/test/modifiers` answer 400 to it and do nothing."""
    if path not in HOOKS:
        code, _ = post(path, {}, timeout=5)
        HOOKS[path] = code != 404
    return HOOKS[path]

def _sudo(args, stdin=None, timeout=15):
    try:
        r = subprocess.run(["sudo", "-n"] + list(args), input=stdin, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return 1, "%s: %s" % (type(e).__name__, e)

def needs(*routes, **kw):
    """A `pre`: Wispr running, `wisprLive` + `pasteboard` in `/test/state`, each route present;
    `pf=True`: passwordless sudo + pfctl; `restart=True`: `relay-restart.sh` beside the plan;
    `db=True`: Wispr's real `flow.sqlite`."""
    def pre():
        why = needs_wispr()
        if why:
            return why
        s = state()
        for k in ("wisprLive", "pasteboard"):
            if k not in s:
                return "hook missing: /test/state.%s (a build older than 2026-09-28)" % k
        for r in routes:
            if not _route_there(r):
                return "hook missing: POST %s answers 404 in this build" % r
        if kw.get("pf"):
            if not os.path.exists("/sbin/pfctl"):
                return "no /sbin/pfctl"
            rc, out = _sudo(["true"], timeout=5)
            if rc:
                return "the network cut needs passwordless sudo (the guest has it): %s" % out.strip()[:80]
        if kw.get("restart") and not os.path.exists(os.path.join(REPO, "relay-restart.sh")):
            return "no relay-restart.sh at %s (refresh the ~/wt-lab mirror)" % REPO
        if kw.get("db") and not os.path.exists(fw.REAL):
            return "no Wispr flow.sqlite at %s" % fw.REAL
        return None
    return pre

PROC = "/test/wispr-proc"
MODS = "/test/modifiers"
CHORD = "/test/wispr-chord"


# ---------------------------------------------------------------- the network cut (pf, guest only)
PF_ANCHOR = "com.apple/wt-chaos"
PF_RULE = "block drop out quick proto { tcp udp } from any to any port 443\n"
NET = {"on": False, "token": None, "nonce": None, "timer": None, "since": None, "probe": None, "events": []}
NET_LOCK = threading.RLock()

def _kill_443_states():
    """Established 443 flows ride their pf state past a new rule: kill those host pairs."""
    rc, ss = _sudo(["pfctl", "-ss"])
    pairs = set()
    for ln in ss.splitlines():
        m = (re.search(r"(\d+\.\d+\.\d+\.\d+):(\d+)\s+(?:->|<-)\s+(\d+\.\d+\.\d+\.\d+):(\d+)", ln)
             or re.search(r"([0-9a-f:]+)\[(\d+)\]\s+(?:->|<-)\s+([0-9a-f:]+)\[(\d+)\]", ln))
        if m and "443" in (m.group(2), m.group(4)):
            pairs.add((m.group(1), m.group(3)))
    for a, b in pairs:
        _sudo(["pfctl", "-k", a, "-k", b])
    return len(pairs)

def net_probe():
    """True when HTTPS gets out (the cut did NOT take)."""
    try:
        return subprocess.run(["curl", "-sS", "-m", "4", "-o", "/dev/null", "https://www.apple.com"],
                              capture_output=True, timeout=8).returncode == 0
    except Exception:
        return False

def net_cut(seconds=20.0, probe=True):
    """Block outbound 443 (tcp + udp) for `seconds`, then lift it on its own. Idempotent while on.
    Raises (after restoring) when pf would not take the rule or the probe still gets out."""
    if not IN_LAB:
        raise RuntimeError("net_cut refuses to run outside the Tart guest")
    with NET_LOCK:
        if NET["on"]:
            return NET
        rc, sr = _sudo(["pfctl", "-sr"])
        if 'anchor "com.apple/*"' not in sr:
            # the main ruleset must reference the com.apple anchors — macOS's own /etc/pf.conf does
            _sudo(["pfctl", "-f", "/etc/pf.conf"])
        rc, out = _sudo(["pfctl", "-a", PF_ANCHOR, "-f", "-"], stdin=PF_RULE)
        if rc:
            raise RuntimeError("pfctl did not load the rule: " + out.strip()[:200])
        NET["on"], NET["since"] = True, time.time()
        rc, out = _sudo(["pfctl", "-E"])
        m = re.search(r"[Tt]oken\s*:\s*(\d+)", out)
        NET["token"] = m.group(1) if m else None
        killed = _kill_443_states()
        nonce = os.path.join(WORK, "wt-chaos-pf.%d.%d" % (os.getpid(), int(time.time() * 1000)))
        open(nonce, "w").close()
        NET["nonce"] = nonce
        undo = "pfctl -a %s -F rules" % PF_ANCHOR + ("; pfctl -X %s" % NET["token"] if NET["token"] else "")
        subprocess.Popen(["sudo", "-n", "sh", "-c", 'sleep %d; if [ -e "%s" ]; then %s; rm -f "%s"; fi'
                          % (int(seconds) + 10, nonce, undo, nonce)],
                         stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL, start_new_session=True)
        t = threading.Timer(seconds, net_restore)
        t.daemon = True
        t.start()
        NET["timer"] = t
        NET["events"].append("cut %s (%d 443 state pair(s) killed, token %s)" % (now_iso(), killed, NET["token"]))
    if probe:
        got_out = net_probe()
        NET["probe"] = "OPEN" if got_out else "blocked"
        if got_out:
            net_restore()
            raise RuntimeError("the pf cut did not take: https://www.apple.com still answered")
    return NET

def net_restore():
    """Lift the cut. Idempotent; safe from the timer thread, a `finally` and `CLEANUPS`."""
    with NET_LOCK:
        if not NET["on"]:
            return
        t = NET.get("timer")
        if t is not None and t is not threading.current_thread():
            t.cancel()
        rc, out = _sudo(["pfctl", "-a", PF_ANCHOR, "-F", "rules"])
        if rc:
            print("  ⚠️ net_restore: pfctl -F rules failed (%s) — the root dead-man lifts it" % out.strip()[:120])
            return
        if NET["token"]:
            _sudo(["pfctl", "-X", NET["token"]])
        try:
            os.remove(NET["nonce"])          # disarms the dead-man
        except (OSError, TypeError):
            pass
        NET["events"].append("lifted %s after %.1f s" % (now_iso(), time.time() - (NET["since"] or time.time())))
        NET.update(on=False, token=None, nonce=None, timer=None)

def _net_note():
    ev = NET["events"][-2:]
    return ("net: %s; probe %s" % (" · ".join(ev), NET["probe"])) if ev else "net: untouched"


# ---------------------------------------------------------------- Wispr frozen longer than the route allows
def wispr_freeze(seconds):
    """SIGSTOP Wispr's main process directly, with a detached SIGCONT dead-man after `seconds`."""
    pid = wispr_pid()
    if not pid:
        raise RuntimeError("Wispr is not running")
    os.kill(pid, signal.SIGSTOP)
    CHAOS["frozen"] = pid
    subprocess.Popen(["sh", "-c", "sleep %d; kill -CONT %d 2>/dev/null" % (int(seconds), pid)],
                     stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL, start_new_session=True)
    return pid

def wispr_thaw():
    pid = CHAOS.get("frozen")
    CHAOS["frozen"] = None
    if pid:
        try:
            os.kill(pid, signal.SIGCONT)
        except (ProcessLookupError, PermissionError):
            pass


# ---------------------------------------------------------------- restore after every case (harness CLEANUPS)
def chaos_cleanup():
    """The network back, Wispr thawed, any History lock released, TextEdit's document closed;
    after a case that touched Wispr (lab / KILL_OK): Wispr running and no ghost microphone."""
    net_restore()
    wispr_thaw()
    while CHAOS["db_release"]:
        try:
            CHAOS["db_release"].pop()()
        except Exception:
            pass
    te_close()
    if not CHAOS["touched"]:
        return
    CHAOS["touched"] = False
    if not KILL_OK:
        return
    if not wispr_pid():
        post(PROC, {"relaunch": True})
        wait_for(lambda: wispr_pid() and engine().get("ready"), 45, 0.5)
        print("  (chaos cleanup: Wispr was down — relaunched)")
    s = state()
    lv = s.get("wisprLive") or {}
    if lv.get("micOpen") and not lv.get("captureOpen") and not s.get("listening"):
        print("  (chaos cleanup: %s)" % _clear_ghost())

CLEANUPS.append(chaos_cleanup)


# ---------------------------------------------------------------- sampling
class Sampler(object):
    """`/test/state` at `hz` on a thread: listening, the chip, Wispr's mic, the capture, and how
    long each GET took (finding 4: main-thread stalls after a relaunch show as slow answers)."""
    def __init__(self, hz=4.0):
        self.hz, self.rows, self.ev, self.th, self.t0 = hz, [], threading.Event(), None, None

    def start(self):
        self.t0 = time.time()
        def run():
            while not self.ev.is_set():
                t = time.time()
                try:
                    s = state()
                    lv = s.get("wisprLive") or {}
                    self.rows.append({"t": t - self.t0, "lat": time.time() - t, "listening": bool(s.get("listening")),
                                      "chip": " | ".join(str(r) for r in (s.get("chip") or []) if r),
                                      "mic": bool(lv.get("micOpen")), "cap": bool(lv.get("captureOpen")),
                                      "rec": bool(s.get("isRecording"))})
                except Exception as e:
                    self.rows.append({"t": t - self.t0, "lat": time.time() - t, "err": type(e).__name__})
                time.sleep(max(0.0, 1.0 / self.hz - (time.time() - t)))
        self.th = threading.Thread(target=run, daemon=True)
        self.th.start()
        return self

    def stop(self):
        self.ev.set()
        if self.th:
            self.th.join(8)
        return self

    def longest(self, pred):
        best, since = 0.0, None
        for r in self.rows:
            if "err" not in r and pred(r):
                since = r["t"] if since is None else since
                best = max(best, r["t"] - since)
            elif "err" not in r:
                since = None
        return best

    def stalls(self, over=2.5):
        return [r["lat"] for r in self.rows if r["lat"] > over]

def _listening_row(r):
    return r.get("listening") or "Listening" in r.get("chip", "")


# ---------------------------------------------------------------- one relay sentence, broken open
def _rig(te=False):
    """Bound witness (cleared), the relay's recorder on the Loopback, Autosend on for the run
    (a held panel would read as a stuck sentence); TextEdit as the caret when `te`. Returns the
    context `_after` and the `finally` need."""
    CHAOS["touched"] = True
    bind_witness()
    witness_clear()
    mic_override(LOOPBACK)
    s = state()
    ctx = {"autosend0": s.get("autosend"), "pid": s.get("pid"), "t_iso": now_iso(),
           "cc0": (s.get("pasteboard") or {}).get("changeCount") or 0,
           "row0": (s.get("wisprLive") or {}).get("newestRowId")}
    post("/test/autosend", {"on": True})
    if te:
        te_open()
    return ctx

def _unrig(ctx):
    """The case's own `finally`: the open sentence let go, Recover drained into the witness (a
    staged file holds `busy` for five minutes — every later case would wait it out), Autosend back."""
    try:
        s = state()
        if s.get("listening") or s.get("settling"):
            post("/test/cancel")
            time.sleep(0.5)
        _quiet(30)
        if state().get("recoverable") and state().get("bound"):
            m = log_mark()
            post("/test/recover")
            wait_for(lambda: log_has(m, r"📦 delivery:|No speech|no speech|No words"), 45, 0.5)
            _quiet(20)
    except Exception as e:
        print("  (unrig: %s: %s)" % (type(e).__name__, e))
    finally:
        if ctx.get("autosend0") is not None:
            post("/test/autosend", {"on": bool(ctx["autosend0"])})
        te_close()

def _opened(mark, timeout=8):
    return wait_for(lambda: state()["listening"] or log_has(mark, r"opening the dictation|mic: recording through"),
                    timeout, 0.05)

def _start_relay(mark):
    """🔼→ at the bound witness; True once the sentence is open (a refused start is False)."""
    gesture("forward-right")
    return bool(_opened(mark))

def _stop_relay():
    """🔼→ again — only while the relay is still listening (TW4: a stop sent to a relay that gave
    up opens a stray sentence)."""
    if state()["listening"]:
        gesture("forward-right")
        return True
    return False

def _play_bg(wav, seconds=None):
    th = threading.Thread(target=lambda: play(wav, seconds=seconds), daemon=True)
    th.start()
    return th

def _deliveries(mark):
    return re.findall(r"📦 delivery: (\S+) → (\S+)", log_since(mark))

def _ended(mark):
    txt = log_since(mark)
    return "📦 delivery: " in txt or re.search(FAIL_RE, txt) is not None

def _still_up(s=None):
    s = s or state()
    lv = s.get("wisprLive") or {}
    return [k for k, v in (("listening", s.get("listening")), ("settling", s.get("settling")),
                           ("isRecording", s.get("isRecording")), ("captureOpen", lv.get("captureOpen")),
                           # A `done` sentence stays in the ledger until the next one opens
                           # (`describeSentences` = parked + live) — not stuck (lab wave 2, 2026-09-28).
                           ("sentences", any(x.get("state") != "done" for x in s.get("sentences") or []))) if v]

def _wait_end(mark, timeout=60):
    """Until the sentence ended (a delivery or a failure line) and the relay let go of it."""
    return bool(wait_for(lambda: _ended(mark) and not _still_up(), timeout, 0.3))

def _variants(w):
    """The word and its plural/singular: Wispr wrote *assumption* for the corpus's *assumptions*
    (lab wave 4, TX8b/TX10 marked PASS by hand) — the marker counts either."""
    return {w, w[:-1]} if w.endswith("s") and len(w) > 4 else {w, w + "s"}

def _marker(ref, avoid=()):
    """The clip's most telling word: long, rare in the clip, absent from `avoid` (in either
    number) — its count in a destination is the number of copies that landed there."""
    av = set().union(*[_variants(a) for a in avoid]) if avoid else set()
    cand = [w for w in ref if len(w) >= 5 and not (_variants(w) & av)] or [w for w in ref if w not in av] or ref
    if not cand:
        return None, 1
    w = sorted(cand, key=lambda x: (ref.count(x), -len(x)))[0]
    return w, max(1, ref.count(w))

def copies(text, ref, avoid=()):
    w, per = _marker(ref, avoid)
    if not w:
        return 0
    vs = _variants(w)
    return sum(1 for t in _tokens(text) if t in vs) / float(per)

def _pb_walkie(cc0):
    ev = (state().get("pasteboard") or {}).get("events") or []
    return sum(1 for e in ev if e.get("writer") == "walkie" and (e.get("changeCount") or 0) > cc0)

def _after(ctx, mark, ref, dest_text=None):
    """Everything a verdict reads, in one dict."""
    s = state()
    lv = s.get("wisprLive") or {}
    txt = log_since(mark)
    wt = witness_text() if dest_text is None else dest_text
    lf = s.get("lastFailure") or {}
    dels = _deliveries(mark)
    return {"n": len(dels), "vias": [d[0] for d in dels], "tos": [d[1] for d in dels],
            "copies": copies(wt, ref) if ref else None, "recall": recall(ref, wt) if ref and wt.strip() else 0.0,
            "doubled": doubled(wt), "chars": len(wt.strip()),
            "fallback": "stands in (Q14)" in txt, "late": "never a second delivery" in txt,
            "waitQ2": "waiting on (Q2)" in txt, "returnFallback": RETURN_FALLBACK in txt,
            "voiced": re.findall(r"([\d.]+) s voiced", txt)[-1:] or None,
            "recoverable": bool(s.get("recoverable")),
            "failure": lf.get("why") if (lf.get("at") or "") >= ctx["t_iso"] else None,
            "refused": bool(re.search(REFUSE_RE, txt)), "up": _still_up(s),
            "pb": _pb_walkie(ctx["cc0"]), "pidSame": s.get("pid") == ctx["pid"],
            "rows": (lv.get("newestRowId") or 0) - (ctx["row0"] or 0), "rowStatus": lv.get("newestRowStatus"),
            "micOpen": bool(lv.get("micOpen"))}

def _fmt(o):
    parts = ["📦×%d %s" % (o["n"], ",".join(o["vias"]) or "-")]
    if o["copies"] is not None:
        parts.append("copies %.1f recall %.2f" % (o["copies"], o["recall"] or 0.0))
    parts.append("rows +%d (%s)" % (o["rows"], o["rowStatus"]))
    for k, label in (("fallback", "Q14 fallback"), ("late", "late row logged only"), ("waitQ2", "Q24 wait"),
                     ("recoverable", "Recover staged"), ("refused", "refusal"), ("doubled", "doubled text")):
        if o[k]:
            parts.append(label)
    if o["voiced"]:
        parts.append("%s s voiced" % o["voiced"][0])
    if o["failure"]:
        parts.append("failure: %s" % str(o["failure"])[:60])
    parts.append("clipboard writes %d" % o["pb"])
    if o["up"]:
        parts.append("STILL UP %s" % o["up"])
    if not o["pidSame"]:
        parts.append("APP PID CHANGED (crash?)")
    if o["returnFallback"]:
        parts.append("witness Return fallback (finding 1)")
    return "; ".join(parts)

def _once(o, min_recall=0.3):
    """Delivered exactly once with the clip's words, or ended loudly with nothing; never both."""
    if not o["pidSame"]:
        return "FAIL", "the app died"
    if o["up"]:
        return "FAIL", "stuck: %s" % o["up"]
    if o["n"] > 1 or (o["copies"] or 0) > 1.4:
        return "FAIL", "delivered twice" + (" (the witness Return fallback may double it — finding 1)"
                                            if o["n"] <= 1 and o["returnFallback"] else "")
    if o["n"] == 1:
        return ("PASS", "delivered once") if o["recall"] >= min_recall else ("FAIL", "delivered, but not these words")
    if o["recoverable"] or o["failure"] or o["refused"]:
        return "PASS", "nothing delivered, said so (Recover / failure / refusal)"
    return "FAIL", "silently lost"


# ---------------------------------------------------------------- TX1: frozen during the upload (W12, Q24)
@case("TX1", tags=("gesture", "audio", "chaos"), engine="wispr", lab_only=True, pre=needs(PROC),
      expect="Wispr SIGSTOPped 0.3 s after the stop for 8 s: the late row is waited for (Q24) and delivered once — "
             "one 📦, one copy, never a Q14 fallback beside it")
def tx1():
    """W12 / Q24 (and W13's double): the stop chord, 0.3 s, Wispr's main process SIGSTOPped for
    8 s (`/test/wispr-proc {"stop", "forMs": 8000}` — it resumes by itself), so its upload and its
    terminal write land ~8 s late. Q24: the relay waits while the row is being worked on; the
    words arrive once. A Q14 fallback *and* the late row = the double Q14 promises cannot happen."""
    ctx = _rig()
    ref = ref_words(CLIP_SPEECH)[:18]
    try:
        mark = log_mark()
        if not _start_relay(mark):
            return "ERROR", "the relay never opened the sentence"
        time.sleep(0.4)
        play(CLIP_SPEECH, seconds=6)
        time.sleep(0.6)
        _stop_relay()
        time.sleep(0.3)
        code, r = post(PROC, {"stop": True, "forMs": 8000})
        if code != 200:
            return "ERROR", "wispr-proc stop → %s %s" % (code, r)
        _wait_end(mark, 70)
        time.sleep(8)                 # a second copy would come here (the late row after a fallback)
        o = _after(ctx, mark, ref)
        v, why = _once(o)
        if v == "PASS" and o["n"] == 1 and o["fallback"] and not o["late"]:
            why += " — by the fallback, and no line says the late row was only logged"
        return v, "%s: %s" % (why, _fmt(o))
    finally:
        post(PROC, {"cont": True})
        _unrig(ctx)


# ---------------------------------------------------------------- TX2: killed mid-sentence, relaunched (W3/Q14, W6)
@case("TX2", tags=("gesture", "audio", "chaos"), engine="wispr", lab_only=True, pre=needs(PROC),
      expect="Wispr killed 5 s into an 8 s sentence: Q14 delivers the relay's own recording once; relaunched, "
             "Wispr's mic stays closed for 30 s with no capture (no ghost)")
def tx2():
    """W3 / Q14, then W6 (lab finding 2, the ghost microphone): Wispr SIGKILLed 5 s into the
    sentence (over the 1.5 s voiced floor), the relay ends it itself and the local model stands
    in. The case relaunches Wispr and watches `wisprLive.micOpen` for 30 s with no capture."""
    ctx = _rig()
    ref = ref_words(CLIP_SPEECH)[:20]
    try:
        mark = log_mark()
        if not _start_relay(mark):
            return "ERROR", "the relay never opened the sentence"
        th = _play_bg(CLIP_SPEECH, seconds=8)
        time.sleep(5.0)
        post(PROC, {"kill": True})
        t_kill = time.time()
        down = wait_for(lambda: not state()["listening"], 5, 0.05)
        dt = time.time() - t_kill
        th.join(12)
        _stop_relay()                 # only if it is somehow still open
        _wait_end(mark, 60)
        time.sleep(3)
        o = _after(ctx, mark, ref)
        post(PROC, {"relaunch": True})
        if not wait_for(lambda: wispr_pid() and engine().get("ready"), 45, 0.3):
            return "ERROR", "Wispr did not come back within 45 s; " + _fmt(o)
        t_rel = time.time()
        opened_at = None
        while time.time() - t_rel < 30:
            # Lab wave 2: `/test/state` answered once without `wisprLive` mid-relaunch.
            lv = state().get("wisprLive") or {}
            if lv.get("micOpen") and not lv.get("captureOpen") and opened_at is None:
                opened_at = time.time() - t_rel
            time.sleep(1.0)
        ghost = _mic_open()
        v, why = _once(o)
        note = ("listening down %.2f s after the kill (%s); %s; mic after 30 s %s%s"
                % (dt, bool(down), _fmt(o), "OPEN" if ghost else "closed",
                   "" if opened_at is None else " (first open at +%.0f s)" % opened_at))
        if v != "PASS":
            return v, why + ": " + note
        if o["n"] == 1 and not o["fallback"]:
            note += " — delivered, but not by the Q14 line"
        if ghost:
            return "BUG", "ghost microphone after the relaunch (finding 2 / W6): " + note
        return "PASS", note
    finally:
        _unrig(ctx)


# ---------------------------------------------------------------- TX3: the ghost microphone, first class (W6)
@case("TX3", tags=("gesture", "audio", "chaos", "cold"), engine="wispr", lab_only=True, pre=needs(PROC),
      expect="relaunch Wispr, 🔼→ at once, stop: 30 s later wisprLive.micOpen is false with no capture; no "
             "/test/state answer slower than 2.5 s")
def tx3():
    """W6 — lab finding 2 as its own case: after a relaunch the relay's first chord reaches a cold
    Wispr late, and 10–20 s later Wispr opens its microphone by itself and holds it (07:53 and
    07:55 on 2026-09-28), refusing every relay start (*microphone is already open*). Recipe from
    the report: relaunch, 🔼→ at once, stop, `micOpen` must be false 30 s later. Also samples
    `/test/state` at 4 Hz from the relaunch (finding 4: 3–12 s main-thread stalls after it)."""
    ctx = _rig()
    smp = Sampler(4).start()
    try:
        took = _relaunch_wispr(settle=0.0)
        if took is None:
            return "ERROR", "Wispr did not come back within 45 s"
        mark = log_mark()
        opened = _start_relay(mark)
        if opened:
            time.sleep(0.4)
            play(CLIP_EN)
            time.sleep(0.8)
            _stop_relay()
        t_stop = time.time()
        _wait_end(mark, 45)
        timeline = []
        while time.time() - t_stop < 30:
            lv = live()
            timeline.append((round(time.time() - t_stop), bool(lv.get("micOpen")), bool(lv.get("captureOpen"))))
            time.sleep(1.0)
        s = state()
        lv = s.get("wisprLive") or {}
        ghost = bool(lv.get("micOpen")) and not lv.get("captureOpen") and not s.get("listening")
        first = next((t for t, m, c in timeline if m and not c), None)
        refused = None
        if ghost:                     # what the ghost costs: the next relay start
            m2 = log_mark()
            gesture("forward-right")
            time.sleep(1.5)
            refused = log_has(m2, REFUSE_RE)
            if state()["listening"]:
                post("/test/cancel")
        smp.stop()
        st = smp.stalls(2.5)
        o = _after(ctx, mark, ref_words(CLIP_EN))
        note = ("relaunch %.1f s; first sentence opened %s, %s; mic with no capture first at %s, at +30 s %s%s; "
                "state answers > 2.5 s: %d (max %.1f s)"
                % (took, opened, _fmt(o), "never" if first is None else "+%d s" % first,
                   "OPEN" if ghost else "closed",
                   "" if refused is None else "; next 🔼→ refused %s" % refused, len(st), max(st) if st else 0.0))
        if ghost:
            return "BUG", note
        if st:
            return "FAIL", "main-thread stalls after the relaunch (finding 4): " + note
        return "PASS", note
    finally:
        smp.stop()
        _unrig(ctx)


# ---------------------------------------------------------------- TX4: no network for the whole sentence (W3, W12)
@case("TX4", tags=("gesture", "audio", "chaos", "net"), engine="wispr", lab_only=True, pre=needs(PROC, pf=True),
      expect="443 cut before the gesture until 45 s after: Q14 fallback or Recover, once; the chip never says "
             "Listening > 35 s; nothing stuck")
def tx4():
    """W3 / W12 / Q14: Wispr's network gone for the whole sentence (pf, outbound 443, 45 s) —
    it errors (~33 s, W12) or never writes a row. The relay must end it: the local model on its
    own recording (≥ 1.5 s voiced) or Recover, never a chip frozen on *Listening*."""
    ctx = _rig()
    ref = ref_words(CLIP_SPEECH)[:20]
    smp = Sampler(4)
    try:
        net_cut(45)
        smp.start()
        mark = log_mark()
        if not _start_relay(mark):
            loud = log_has(mark, REFUSE_RE)
            return ("PASS" if loud else "FAIL"), "start refused with no network, said so %s; %s" % (loud, _net_note())
        time.sleep(0.4)
        play(CLIP_SPEECH, seconds=8)
        time.sleep(0.6)
        _stop_relay()
        t_stop = time.time()
        down = wait_for(lambda: not state()["listening"], 5, 0.1)
        _wait_end(mark, 75)
        time.sleep(4)
        smp.stop()
        o = _after(ctx, mark, ref)
        lst = smp.longest(_listening_row)
        note = "%s; listening down after the stop %s (%.1f s); longest Listening %.1f s; %s" % (
            _fmt(o), bool(down), time.time() - t_stop if not down else 0.0, lst, _net_note())
        v, why = _once(o)
        if v != "PASS":
            return v, why + ": " + note
        if lst > 35:
            return "FAIL", "the chip said Listening for %.0f s: %s" % (lst, note)
        return "PASS", why + ": " + note
    finally:
        smp.stop()
        net_restore()
        _unrig(ctx)


# ---------------------------------------------------------------- TX5: no network for the upload only (W12, Q14/Q24)
@case("TX5", tags=("gesture", "audio", "chaos", "net"), engine="wispr", lab_only=True, pre=needs(PROC, pf=True),
      expect="443 cut at the stop, back after 25 s: the late row is honoured or the fallback delivers — once, never both")
def tx5():
    """W12 + Q14/Q24 (W13's double): the sentence heard with the network up, cut at the stop and
    restored 25 s later — Wispr's upload stalls, retries, maybe falls back to its own ASR. The
    relay either waits (Q24, row `processing`) and delivers the late row, or falls back (Q14) and
    only *logs* the late row. One 📦, one copy, one clipboard write."""
    ctx = _rig()
    ref = ref_words(CLIP_SPEECH)[:18]
    try:
        mark = log_mark()
        if not _start_relay(mark):
            return "ERROR", "the relay never opened the sentence"
        time.sleep(0.4)
        play(CLIP_SPEECH, seconds=6)
        time.sleep(0.6)
        _stop_relay()
        net_cut(25, probe=False)          # at the stop: the probe (≤ 4 s) runs after, not before
        NET["probe"] = "OPEN" if net_probe() else "blocked"
        if NET["probe"] == "OPEN":
            return "ERROR", "the pf cut did not take; " + _net_note()
        _wait_end(mark, 90)
        wait_for(lambda: not NET["on"], 30, 0.5)
        time.sleep(15)                    # the late row after the network came back
        o = _after(ctx, mark, ref)
        v, why = _once(o)
        if v == "PASS" and o["n"] == 1 and o["pb"] > 1:
            v, why = "FAIL", "one delivery but %d clipboard writes (Q17: one per sentence)" % o["pb"]
        return v, "%s: %s; %s" % (why, _fmt(o), _net_note())
    finally:
        net_restore()
        _unrig(ctx)


# ---------------------------------------------------------------- TX6: the double chord (W6)
@case("TX6a", tags=("gesture", "audio", "chaos"), engine="wispr", lab_only=True, pre=needs(),
      expect="🔼→, 🔼→ 0.4 s later, 🔼→ 0.2 s after that, 4 s of speech, 🔼→: the words delivered once, nothing stuck, "
             "Wispr's mic closed 10 s later")
def tx6a():
    """W6 through the gestures: a start/stop/start triple inside the 2 s stop dwell and the 0.6 s
    re-trigger window — the tap should absorb the two extra flicks (*too young to stop*) and leave
    one sentence; if either reaches Wispr as a toggle, the relay and Wispr disagree (ghost)."""
    return _tx6(raw=False)

@case("TX6b", tags=("gesture", "audio", "chaos"), engine="wispr", lab_only=True, pre=needs(CHORD),
      expect="raw chords start/stop 0.4 s/start 0.2 s, 4 s speech, stop (state + wire): the second sentence's "
             "words delivered once, the first ends quietly, no stuck isRecording, no ghost mic")
def tx6b():
    """W6 below the gesture guards: `/test/wispr-chord {"post": "on", "state": "start"}` etc. —
    each toggle on the wire *and* in the relay's belief, 0.4 s and 0.2 s apart, the way a
    double-fired Options+ flick or a hung-then-released Wispr replays them. The first micro
    sentence must end with nothing (no delivery), the second must carry the speech."""
    return _tx6(raw=True)

def _tx6(raw):
    ctx = _rig()
    ref = ref_words(CLIP_EN)
    try:
        mark = log_mark()
        if raw:
            chord("on", "start")
            time.sleep(0.4)
            chord("off", "stop")
            time.sleep(0.2)
            chord("on", "start")
            _opened(mark, 5)
        else:
            gesture("forward-right")
            time.sleep(0.4)
            gesture("forward-right")
            time.sleep(0.2)
            gesture("forward-right")
            _opened(mark, 5)
        time.sleep(0.3)
        play(CLIP_EN)
        time.sleep(0.8)
        if raw:
            if state()["listening"]:
                chord("off", "stop")
        else:
            _stop_relay()
        _wait_end(mark, 60)
        time.sleep(10)
        o = _after(ctx, mark, ref)
        txt = log_since(mark)
        young = len(re.findall(r"too young to stop|only \d+ms old", txt))
        note = "%s; dwell-guard swallows %d; Wispr mic 10 s after %s" % (_fmt(o), young, "OPEN" if o["micOpen"] else "closed")
        v, why = _once(o)
        if v == "PASS" and o["n"] == 0:
            v, why = "FAIL", "the speech after the double chord was not delivered (said so, but lost)"
        if v != "PASS":
            return v, why + ": " + note
        if o["micOpen"] and not o["up"]:
            return "BUG", "Wispr's microphone left open by the toggle desync (W6): " + note
        return "PASS", why + ": " + note
    finally:
        _unrig(ctx)


# ---------------------------------------------------------------- TX7: one minute (W12)
def _en6x_wav():
    """CLIP_EN six times, each padded with silence to 10 s: a 60 s sentence."""
    out = os.path.join(WORK, "chaos-en6x-60s.wav")
    if os.path.exists(out):
        return out
    r = wave.open(CLIP_EN)
    p = r.getparams()
    frames = r.readframes(r.getnframes())
    r.close()
    per = p.sampwidth * p.nchannels
    pad = max(0, int(p.framerate * 10) - len(frames) // per)
    w = wave.open(out, "wb")
    w.setparams(p)
    for _ in range(6):
        w.writeframes(frames + b"\x00" * (pad * per))
    w.close()
    return out

@case("TX7", tags=("gesture", "audio", "chaos", "long"), engine="wispr", lab_only=True, pre=needs(),
      expect="a 60 s sentence (CLIP_EN ×6): one Wispr row, one delivery, ≥ 5 of 6 repetitions in the witness, "
             "no ceiling / 30 s cap line")
def tx7():
    """W12 (and the 30 s budget in general): one sentence six times as long as usual — Wispr's
    upload and formatting run long, the relay must not cap it, split it, or deliver half."""
    ctx = _rig()
    ref = ref_words(CLIP_EN)
    try:
        wav = _en6x_wav()
        mark = log_mark()
        if not _start_relay(mark):
            return "ERROR", "the relay never opened the sentence"
        time.sleep(0.4)
        play(wav)
        time.sleep(0.6)
        _stop_relay()
        t_stop = time.time()
        _wait_end(mark, 120)
        dt = time.time() - t_stop
        time.sleep(5)
        o = _after(ctx, mark, ref)
        reps = o["copies"] or 0.0
        # Lab wave 2: a bare `ceiling` matched the decode-rate line (`ceiling × 1.19`). The cap
        # lines are the relay giving up on the row: the capture timeout, the NULL-no-mic ceiling.
        cap = re.search(r"nothing came back within|Wispr Flow returned no words|never opened its microphone"
                        r"|the NULL-no-mic ceiling|captureTimeout", log_since(mark))
        note = "%s; stop→end %.1f s; repetitions %.1f/6; cap line %s" % (_fmt(o), dt, reps, bool(cap))
        if o["up"] or not o["pidSame"]:
            return "FAIL", note
        if o["n"] != 1:
            return "FAIL", ("not delivered" if o["n"] == 0 else "delivered in %d pieces" % o["n"]) + ": " + note
        if o["rows"] > 1:
            return "FAIL", "Wispr split it into %d rows: %s" % (o["rows"], note)
        if reps < 5 or cap:
            return "FAIL", "incomplete: " + note
        return "PASS", note
    finally:
        _unrig(ctx)


# ---------------------------------------------------------------- TX8: his own ptt against the relay (W4, W6, Q19)
@case("TX8a", tags=("gesture", "audio", "chaos"), engine="wispr", lab_only=True, pre=needs(MODS),
      expect="his 61+60 held 6 s over speech, 🔼→ at +1.5 s: the relay refuses (or runs its own sentence to the "
             "witness); his words land in TextEdit once, never in the witness")
def tx8a():
    """W6 (the start over his running Wispr sentence) / Q21's exclusivity: his own push-to-talk
    (`/engine.wisprShortcuts.ptt`, 61+60) held with speech, TextEdit in front, and the relay's
    🔼→ in the middle. Nothing lost silently: his sentence at the caret, the relay's start
    refused visibly — a toggle posted into his sentence would cut it."""
    ctx = _rig(te=True)
    ref = ref_words(CLIP_SPEECH)[:14]
    try:
        te_front()
        te_clear()
        time.sleep(0.3)
        mark = log_mark()
        post(MODS, {"keys": his_ptt_keys(), "holdMs": 6500})
        th = _play_bg(CLIP_SPEECH, seconds=5.5)
        time.sleep(1.5)
        gesture("forward-right")
        # his own sentence may raise `listening` (the ring): only the relay's own open line counts
        relay_opened = bool(wait_for(lambda: log_has(mark, r"opening the dictation"), 1.5, 0.05)) \
            and not log_has(mark, REFUSE_RE)
        th.join(10)
        time.sleep(1.5)
        if relay_opened:
            _stop_relay()
        _wait_end(mark, 45)
        wait_for(lambda: te_text().strip(), 30, 0.5)
        time.sleep(3)
        te = te_text()
        o = _after(ctx, mark, ref)
        at_caret, in_witness = copies(te, ref), copies(witness_text(), ref)
        note = ("relay opened %s, refused %s; his words: TextEdit %.1f (recall %.2f), witness %.1f; %s"
                % (relay_opened, o["refused"], at_caret, recall(ref, te) or 0.0, in_witness, _fmt(o)))
        if in_witness > 0 and not relay_opened:
            return "FAIL", "his words went to the terminal: " + note
        if o["up"] or not o["pidSame"]:
            return "FAIL", note
        if at_caret < 0.5:
            return "BUG", "his sentence lost (W4/W6; Wispr-side if no ⌘V drop line): " + note
        if at_caret > 1.4:
            return "FAIL", "his sentence pasted twice: " + note
        if not relay_opened and not o["refused"]:
            return "FAIL", "the relay's start vanished without a refusal: " + note
        return "PASS", note
    finally:
        _unrig(ctx)

@case("TX8b", tags=("gesture", "audio", "chaos"), engine="wispr", lab_only=True, pre=needs(MODS),
      expect="relay sentence, then his 61+60 sentence 0.3 s after its stop: relay's in the witness once, his at the "
             "caret once (Q19), nothing crossed")
def tx8b():
    """W4 / Q19: his own sentence that ends while the relay's row is still in flight is pasted at
    the caret by the relay (Q19), never swallowed, never rescued into the bound terminal. TW8a
    lost it 2/2 on Wispr's side (lab report finding 3) — this one counts both sides at once."""
    ctx = _rig(te=True)
    ref_r = ref_words(CLIP_EN)
    ref_h = [w for w in ref_words(CLIP_SPEECH)[:14] if w not in ref_r]
    try:
        te_front()
        te_clear()
        time.sleep(0.3)
        mark = log_mark()
        if not _start_relay(mark):
            return "ERROR", "the relay never opened the sentence"
        time.sleep(0.4)
        play(CLIP_EN)
        time.sleep(0.6)
        _stop_relay()
        time.sleep(0.3)
        te_front()
        post(MODS, {"keys": his_ptt_keys(), "holdMs": 6000})
        time.sleep(0.4)
        play(CLIP_SPEECH, seconds=5)
        time.sleep(1.0)
        _wait_end(mark, 60)
        wait_for(lambda: te_text().strip(), 30, 0.5)
        time.sleep(4)
        te, wt = te_text(), witness_text()
        o = _after(ctx, mark, ref_r)
        txt = log_since(mark)
        r_w, r_c = copies(wt, ref_r), copies(te, ref_r, avoid=ref_h)
        h_c, h_w = copies(te, ref_h), copies(wt, ref_h)
        note = ("relay: witness %.1f, TextEdit %.1f · his: TextEdit %.1f, witness %.1f · Q19 line %s · drop line %s; %s"
                % (r_w, r_c, h_c, h_w, re.search(r"\((?:B, )?Q19\)", txt) is not None, "dropped" in txt, _fmt(o))) + " · TE=%r" % te[:300]
        if h_w > 0 or r_c > 0:
            return "FAIL", "crossed: " + note
        if o["up"] or r_w > 1.4 or h_c > 1.4:
            return "FAIL", note
        if r_w < 0.5 and not (o["recoverable"] or o["failure"]):
            return "FAIL", "the relay's sentence lost silently: " + note
        if h_c < 0.5:
            return "BUG", "his sentence lost (W4; lab finding 3): " + note
        return "PASS", note
    finally:
        _unrig(ctx)


# ---------------------------------------------------------------- TX9: cold, three times (W11)
@case("TX9", tags=("gesture", "audio", "chaos", "cold"), engine="wispr", lab_only=True, pre=needs(PROC),
      expect="3 sentences each 1 s after a Wispr relaunch: all delivered with their head (first 5 words), or said "
             "why — losses counted")
def tx9():
    """W11 (Q20): a sentence started 1 s after Wispr came back. TW4 lost it 2/2 (no row within
    12 s, and the relay judged its own recording `0.0 s voiced` so Q14 did not stand in). Three
    samples; a loss is nothing delivered or < 40 % recall, a head loss ≥ 3 of the first 5 words."""
    ctx = _rig()
    ref = ref_words(CLIP_SPEECH)[:24]
    recs = []
    try:
        for i in range(3):
            if _relaunch_wispr(settle=1.0) is None:
                recs.append("#%d relaunch failed" % i)
                continue
            witness_clear()
            mark = log_mark()
            opened = _start_relay(mark)
            if opened:
                time.sleep(0.2)
                play(CLIP_SPEECH, seconds=8)
                time.sleep(0.6)
                _stop_relay()
            _wait_end(mark, 60)
            time.sleep(2)
            o = _after(ctx, mark, ref)
            got = set(_tokens(witness_text()))
            head = sum(1 for w in ref[:5] if w not in got)
            lost = o["n"] == 0 or (o["recall"] or 0) < 0.4
            recs.append({"i": i, "opened": opened, "lost": lost, "head": head, "o": o})
            _unrig({"autosend0": None})
            post("/test/autosend", {"on": True})
            CHAOS["touched"] = True
        runs = [r for r in recs if isinstance(r, dict)]
        losses = sum(r["lost"] for r in runs)
        heads = sum(1 for r in runs if not r["lost"] and r["head"] >= 3)
        silent = sum(1 for r in runs if r["lost"] and not (r["o"]["recoverable"] or r["o"]["failure"] or r["o"]["refused"]))
        stuck = [r["o"]["up"] for r in runs if r["o"]["up"]]
        lines = ["#%d opened %s %s head-miss %d/5; %s" % (r["i"], r["opened"], "LOST" if r["lost"] else "ok", r["head"],
                                                          _fmt(r["o"])) for r in runs]
        note = "losses %d/%d (silent %d), head losses %d; %s\n%s" % (
            losses, len(runs), silent, heads, " · ".join(x for x in recs if isinstance(x, str)), "\n".join(lines))
        if len(runs) < 3:
            return "ERROR", note
        if stuck:
            return "FAIL", "stuck after a cold sentence: " + note
        if losses or heads:
            return "BUG", note
        return "PASS", note
    finally:
        _unrig(ctx)


# ---------------------------------------------------------------- TX10: ten alternating (W4, W6)
@case("TX10", tags=("gesture", "audio", "chaos"), engine="wispr", lab_only=True, pre=needs(MODS),
      expect="5 relay + 5 standalone sentences alternating, 2 s gaps: relay words only in the witness, his only in "
             "TextEdit; losses counted, 0 misroutes, 0 stuck")
def tx10():
    """W4 (the relay-owned window swallowing his ⌘V) and W6 (a toggle into a sentence that is not
    the relay's), at speed: relay (CLIP_EN) and standalone (his `61+60`, the first 4 s of
    CLIP_SPEECH, TextEdit in front) alternating with 2 s after each close, not waiting for the
    words. Relay starts refused by Q16 (*one sentence at a time*) are counted, never stopped (a
    stop to a refused start would open a stray sentence)."""
    ctx = _rig(te=True)
    ref_r = ref_words(CLIP_EN)
    ref_h = [w for w in ref_words(CLIP_SPEECH)[:10] if w not in ref_r]
    refused, opened = 0, 0
    try:
        te_front()
        te_clear()
        time.sleep(0.3)
        mark = log_mark()
        for i in range(10):
            if i % 2 == 0:
                m = log_mark()
                if _start_relay(m):
                    opened += 1
                    time.sleep(0.4)
                    play(CLIP_EN)
                    time.sleep(0.6)
                    _stop_relay()
                else:
                    refused += 1
            else:
                te_front()
                post(MODS, {"keys": his_ptt_keys(), "holdMs": 5500})
                time.sleep(0.4)
                play(CLIP_SPEECH, seconds=4)
                time.sleep(0.8)
            time.sleep(2.0)
        _wait_end(mark, 60)
        wait_for(lambda: not _really_busy(state()), 60, 0.5)
        time.sleep(8)
        te, wt = te_text(), witness_text()
        r_w, r_c = copies(wt, ref_r), copies(te, ref_r, avoid=ref_h)
        h_c, h_w = copies(te, ref_h), copies(wt, ref_h)
        o = _after(ctx, mark, ref_r)
        lost_r = max(0.0, 5 - r_w)
        lost_h = max(0.0, 5 - h_c)
        note = ("relay: %d opened, %d refused, witness %.1f/5, TextEdit %.1f · his: TextEdit %.1f/5, witness %.1f · "
                "losses relay %.0f his %.0f; %s" % (opened, refused, r_w, r_c, h_c, h_w, lost_r, lost_h, _fmt(o))) + " · TE=%r" % te[:400]
        if r_c > 0 or h_w > 0:
            return "FAIL", "misrouted: " + note
        if o["up"] or not o["pidSame"] or r_w > 5.4 or h_c > 5.4:
            return "FAIL", note
        if lost_r or lost_h:
            return "BUG", note
        return "PASS", note
    finally:
        _unrig(ctx)


# ---------------------------------------------------------------- TX11a–h: a cancel at every offset (W3, W6, W17)
def _tx11(off):
    def fn():
        """W3 (a cancel keeps the audio for Recover) / W6 / W17 (a late row after a cancel never
        delivers): 🔼← at `off` s into a 4 s sentence (4.0 = 0.1 s after the stop, in the settle).
        Each ends in Recover or nothing — never a stray delivery, even when Wispr's row finishes
        later (watched 35 s, Wispr's own budget)."""
        ctx = _rig()
        try:
            mark = log_mark()
            if not _start_relay(mark):
                return "ERROR", "the relay never opened the sentence"
            t0 = time.time()
            th = _play_bg(CLIP_EN)
            if off < 4.0:
                time.sleep(max(0.0, t0 + off - time.time()))
                gesture("forward-left")
                how = "mid-sentence"
            else:
                time.sleep(max(0.0, t0 + 4.0 - time.time()))
                _stop_relay()
                time.sleep(0.1)
                gesture("forward-left")
                how = "0.1 s after the stop"
            th.join(10)
            wait_for(lambda: _deliveries(mark), 35, 0.5)
            time.sleep(1.0)
            o = _after(ctx, mark, ref_words(CLIP_EN))
            note = "cancel %s (+%.1f s): %s" % (how, off, _fmt(o))
            if o["n"] or (o["copies"] or 0) > 0:
                return "FAIL", "stray delivery after the cancel: " + note
            if o["up"] or not o["pidSame"]:
                return "FAIL", note
            return "PASS", ("Recover" if o["recoverable"] else "nothing") + ": " + note
        finally:
            _unrig(ctx)
    return fn

for _i, _off in enumerate((0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0)):
    case("TX11" + "abcdefgh"[_i], tags=("gesture", "audio", "chaos"), engine="wispr", lab_only=True, pre=needs(),
         expect="🔼← at +%.1f s of a 4 s sentence: Recover or nothing, never a delivery, nothing stuck" % _off)(_tx11(_off))


# ---------------------------------------------------------------- TX12: the History DB locked (W14)
def _lock_db(path, hold, mode="IMMEDIATE", write=None, ready=None):
    """A thread holding a `BEGIN <mode>` on `path` for `hold` s; `write(conn)` runs inside it (the
    fake's terminal write, committed at the release); without it the transaction rolls back and
    nothing is written — Wispr's real file is never changed. Returns (thread, info)."""
    info = {"locked": None, "released": None, "error": None, "journal": None}
    stop = threading.Event()
    CHAOS["db_release"].append(stop.set)
    def run():
        c = None
        try:
            c = sqlite3.connect(path, timeout=0.2, isolation_level=None)
            info["journal"] = c.execute("pragma journal_mode").fetchone()[0]
            t_end = time.time() + 2.0
            while True:
                try:
                    c.execute("BEGIN %s" % mode)
                    break
                except sqlite3.OperationalError as e:
                    if time.time() > t_end:
                        raise e
                    time.sleep(0.05)
            if write:
                write(c)
            info["locked"] = time.time()
            if ready:
                ready.set()
            stop.wait(hold)
            c.execute("COMMIT" if write else "ROLLBACK")
            info["released"] = time.time()
        except Exception as e:
            info["error"] = "%s: %s" % (type(e).__name__, e)
            if ready:
                ready.set()
        finally:
            if c is not None:
                try:
                    c.close()
                except Exception:
                    pass
    th = threading.Thread(target=run, daemon=True)
    th.start()
    return th, info

@case("TX12", tags=("gesture", "audio", "chaos", "db"), engine="wispr", lab_only=True, pre=needs(db=True),
      expect="a write transaction held on Wispr's flow.sqlite for 8 s from the stop: the relay survives, the row "
             "(or the Q14 fallback) is delivered once after the release, nothing stuck")
def tx12():
    """W14 (the reader's health; BUSY/IOERR, a transient read error failing closed): at the stop a
    python `sqlite3` connection takes `BEGIN IMMEDIATE` on Wispr's real `flow.sqlite` for 8 s and
    rolls back (nothing written). Wispr's file is WAL: the relay's `mode=ro` reader is *not*
    blocked by it — Wispr's own terminal write is, so the row goes late (or Wispr fails it). TX12d
    blocks the reader itself on the fake."""
    ctx = _rig()
    ref = ref_words(CLIP_SPEECH)[:18]
    th = None
    try:
        mark = log_mark()
        if not _start_relay(mark):
            return "ERROR", "the relay never opened the sentence"
        time.sleep(0.4)
        play(CLIP_SPEECH, seconds=6)
        time.sleep(0.6)
        _stop_relay()
        ready = threading.Event()
        th, info = _lock_db(fw.REAL, 8.0, "IMMEDIATE", ready=ready)
        ready.wait(4)
        if info["error"]:
            return "ERROR", "could not lock flow.sqlite: %s" % info["error"]
        th.join(15)
        _wait_end(mark, 70)
        time.sleep(6)
        o = _after(ctx, mark, ref)
        dbl = len(re.findall(r"wispr db|SQLITE|BUSY|IOERR", log_since(mark)))
        land = (state().get("lastDelivery") or {}).get("at")
        note = "journal %s, held %.1f s; %s; db log lines %d; lastDelivery.at %s" % (
            info["journal"], (info["released"] or 0) - (info["locked"] or 0), _fmt(o), dbl, land)
        v, why = _once(o)
        return v, why + ": " + note
    finally:
        for f in list(CHAOS["db_release"]):
            f()
        if th:
            th.join(5)
        _unrig(ctx)

@case("TX12d", tags=("desk", "chaos", "db"), engine="wispr", pre=needs_desk,
      expect="the fake History locked EXCLUSIVE for 8 s with the terminal write inside: no give-up during the lock, "
             "delivered once within 10 s of the release, the app alive")
def tx12d():
    """W14 at a desk (no real Wispr heard: `WT_WISPR_DB`, chords muted — `cases_wispr.desk`): the
    row `processing`, then a connection takes `BEGIN EXCLUSIVE` on the fake (rollback journal, so
    the relay's reader gets BUSY for 8 s), writes the finished row inside the transaction and
    commits at the release. The reader must survive the BUSY reads — no *No words*, no fallback,
    no row taken as gone — and deliver the row once it can read it."""
    db = desk()
    bind_witness()
    witness_clear()
    s0 = state()
    ctx = {"pid": s0.get("pid"), "t_iso": now_iso(), "cc0": (s0.get("pasteboard") or {}).get("changeCount") or 0,
           "row0": (s0.get("wisprLive") or {}).get("newestRowId")}
    text = "tx twelve the locked history row arrives once"
    th = None
    try:
        mark = log_mark()
        rid = open_sentence(db)
        time.sleep(1.5)
        chord(state_="stop")
        db.update(rid, status="processing", speech=1.5)
        time.sleep(0.8)
        def write(c):
            c.execute("update History set status='formatted', asrText=?, formattedText=?, pastedText=?, "
                      "e2eLatency=850 where rowid=?", (text, text, text, rid))
        ready = threading.Event()
        th, info = _lock_db(FAKE_DB, 8.0, "EXCLUSIVE", write=write, ready=ready)
        ready.wait(4)
        if info["error"]:
            return "ERROR", "could not lock the fake: %s" % info["error"]
        during = []
        while th.is_alive():
            s = state()
            during.append((bool(s.get("settling") or (s.get("wisprLive") or {}).get("captureOpen")),
                           (s.get("lastDelivery") or {}).get("at")))
            time.sleep(0.25)
        released = info["released"] or time.time()
        held_through = bool(during) and all(x[0] for x in during)
        landed_early = any(x[1] and x[1] != (s0.get("lastDelivery") or {}).get("at") for x in during)
        early = log_since(mark)
        gave_up = re.search(r"No words came back|stands in \(Q14\)|never opened its microphone|carried nothing", early)
        got = wait_for(lambda: "locked" in witness_text(), 10, 0.2)
        dt = (time.time() - released) if got else None
        time.sleep(3)
        ref = _tokens(text)
        o = _after(ctx, mark, ref)
        busy_lines = len(re.findall(r"BUSY|database is locked|wispr db", log_since(mark)))
        note = ("held %.1f s (%s); capture held through the lock %s; given up during the lock: %s; delivered %s "
                "after the release; db log lines %d; %s"
                % ((info["released"] or 0) - (info["locked"] or 0), info["journal"], held_through,
                   gave_up.group(0) if gave_up else "no", "%.1f s" % dt if dt is not None else "never",
                   busy_lines, _fmt(o)))
        if landed_early:
            return "ERROR", "a delivery during the lock — the lock did not hold the row back: " + note
        if gave_up or (not held_through and dt is None):
            return "FAIL", "the reader gave up on a BUSY read: " + note
        v, why = _once(o, min_recall=0.5)
        if v == "PASS" and o["n"] == 0:
            v, why = "FAIL", "the row was never delivered after the release"
        return v, why + ": " + note
    finally:
        for f in list(CHAOS["db_release"]):
            f()
        if th:
            th.join(5)


# ---------------------------------------------------------------- TX13: the app relaunched over a row in flight (W17 / W-B5)
@case("TX13", tags=("gesture", "audio", "chaos", "restart"), engine="wispr", lab_only=True,
      pre=needs(CHORD, restart=True),
      expect="Wispr frozen with the row in flight: relay-restart.sh's gate holds; after cancel + restart + thaw, the "
             "late row is never delivered, the next sentence carries only its own words")
def tx13():
    """W17 / W-B5: `rescueFromRow` / `lastRow` live in memory, so a freshly relaunched relay knows
    nothing of the row in flight before it. Wispr is frozen (SIGSTOP, dead-man 240 s) 0.3 s after
    the stop so its row stays in flight; `relay-restart.sh --dry-run` must refuse (a Wispr
    sentence is a restart blocker). The relay then lets go (`/test/wispr-chord {"state": "cancel"}`
    — no ⌃Esc on the wire), Recover (if staged) is delivered, the app is restarted for real
    through `relay-restart.sh`, Wispr thawed, its late row finishes — and nothing of it may reach
    the witness, alone or inside the next sentence (CLIP_EN)."""
    ctx = _rig()
    ref_old = ref_words(CLIP_SPEECH)[:18]
    ref_new = ref_words(CLIP_EN)
    old_only = [w for w in ref_old if w not in ref_new]
    steps = []
    try:
        mark = log_mark()
        if not _start_relay(mark):
            return "ERROR", "the relay never opened the sentence"
        time.sleep(0.4)
        play(CLIP_SPEECH, seconds=6)
        time.sleep(0.6)
        _stop_relay()
        time.sleep(0.3)
        pid_w = wispr_freeze(240)
        time.sleep(2.0)
        lv = live()
        rid, st0 = lv.get("newestRowId"), lv.get("newestRowStatus")
        steps.append("row %s %s at the freeze" % (rid, st0))
        p = subprocess.run(["./relay-restart.sh", "--dry-run", "--max-wait", "10", "--quiet", "2"], cwd=REPO,
                           capture_output=True, text=True, timeout=90)
        gate_held = p.returncode == 3
        steps.append("dry-run gate exit %d" % p.returncode)
        chord(state_="cancel")
        ok, w = _quiet(45)
        if not ok:
            return "BUG", "the relay would not let go of a capture on a frozen Wispr (Q24 has no cap): busy %s; %s" % (
                w, "; ".join(steps))
        # Lab wave 2: the gate held on `audio staged for Recover` — the WAV is staged a beat
        # after the cancel, so wait for it, deliver it, and wait until nothing is staged.
        for _ in range(3):
            if not wait_for(lambda: state().get("recoverable"), 8, 0.3):
                break
            m = log_mark()
            post("/test/recover")
            wait_for(lambda: log_has(m, r"📦 delivery:|No speech|no speech|No words|recovered"), 60, 0.5)
            steps.append("Recover → %s" % (_deliveries(m) or "nothing"))
            _quiet(20)
            wait_for(lambda: not state().get("recoverable"), 15, 0.5)
        if state().get("recoverable"):
            steps.append("Recover still staged: %s" % state().get("recoverable"))
        pre_copies = copies(witness_text(), old_only) if old_only else 0.0
        p = subprocess.run(["./relay-restart.sh", "--max-wait", "120", "--quiet", "3"], cwd=REPO,
                           capture_output=True, text=True, timeout=240)
        steps.append("restart exit %d" % p.returncode)
        if p.returncode != 0:
            return "ERROR", "relay-restart.sh did not restart: %s; %s" % (p.stdout.strip().splitlines()[-1:] or "", "; ".join(steps))
        if not wait_for(lambda: get("/up", timeout=2).get("ok"), 60, 0.5):
            return "ERROR", "no relay on port %d after the restart (a new port?); %s" % (PORT, "; ".join(steps))
        s = state()
        steps.append("app pid %s → %s" % (ctx["pid"], s.get("pid")))
        if CHAOS.get("frozen") is None:
            return "ERROR", "Wispr thawed before the restart (dead-man) — W-B5 not reached; " + "; ".join(steps)
        mic_override(LOOPBACK)
        post("/test/autosend", {"on": True})
        if engine().get("engine") != "wispr":
            set_engine("wispr")
        if not s.get("bound"):
            post("/bind", {"tty": WITNESS["tty"]})
        witness_clear()
        m_after = log_mark()
        wispr_thaw()
        steps.append("Wispr %d thawed" % pid_w)
        wait_for(lambda: (live().get("newestRowId") == rid and live().get("newestRowStatus")
                          not in (None, "processing")), 40, 0.5)
        lv = live()
        steps.append("late row %s → %s (%s chars)" % (rid, lv.get("newestRowStatus"), lv.get("newestRowText")))
        time.sleep(5)
        stray = _deliveries(m_after)
        m2 = log_mark()
        if not _start_relay(m2):
            return "ERROR", "the next sentence never opened; " + "; ".join(steps)
        time.sleep(0.4)
        play(CLIP_EN)
        time.sleep(0.6)
        _stop_relay()
        _wait_end(m2, 60)
        time.sleep(5)
        wt = witness_text()
        ctx2 = dict(ctx, pid=state().get("pid"))
        o = _after(ctx2, m2, ref_new)
        leaked = copies(wt, old_only) if old_only else 0.0
        note = ("gate held %s; %s; stray deliveries after the restart before the next sentence %s; old words in the "
                "witness after the restart %.1f (before it %.1f); next: %s"
                % (gate_held, "; ".join(steps), stray or "none", leaked, pre_copies, _fmt(o)))
        if stray or leaked > 0:
            return "FAIL", "the pre-restart row reached the witness (W-B5): " + note
        if not gate_held:
            return "FAIL", "relay-restart.sh's gate opened over a Wispr row in flight: " + note
        if o["n"] != 1 or (o["recall"] or 0) < 0.3 or o["up"]:
            return "FAIL", "the next sentence did not land cleanly: " + note
        return "PASS", note
    finally:
        wispr_thaw()
        _unrig(ctx)
