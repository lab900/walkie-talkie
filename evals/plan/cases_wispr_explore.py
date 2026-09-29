"""**Wispr exploratory combos** — TE1–TE28 (2026-09-29 morning, lab only, after wave 5's YES).

Victor: *"when all done, run another agent to creatively try out new test combos to search for more
bugs"*. Each case is a combination the plan (TW / TX / TS / TQ / TA) never ran, with its one-line
hypothesis of what could break in the docstring. Real Wispr Flow in the Tart guest `wt-lab`, BlackHole
2ch, Engine = wispr, the relay's witness tab bound, TextEdit in front as *his* caret.

Two clips that share no marker word: **the relay's** is `CLIP_SPEECH`'s first 6 s (EN), **his** is the
Romanian corpus clip (`clip_ro()`), so a copy of either in the wrong destination shows as its marker
word there. Verdicts: **PASS** (delivered once where it belongs, or ended loudly) · **BUG** (lost
silently, doubled, into the wrong destination, stuck — relay-side) · **WISPR** (a loss on Wispr's side
the relay could not see: no row for his chord) · **RIG** (the rig did not do what the case needs:
DEAF take on BlackHole's shared ring, a key that never reached the app) · **ERROR**. Every case writes
its log slice to `~/wt-lab/night/explore/logs/<id>.log`; the verdict note says what the log showed.

Run (in the guest, through `tart exec` — over SSH BlackHole reads zeros):
    python3 -u cases_wispr_explore.py --only 'TE*' --report …
It registers its cases into the harness, then calls `harness.main()` (the harness's own module list is
left alone).
"""
import os, re, subprocess, sys, threading, time, wave

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import harness as _h            # noqa: E402 — the one runner module every case module binds to
    sys.modules["harness"] = _h

from harness import *  # noqa: E402,F401,F403
import harness as H  # noqa: E402
import cases_wispr as cw  # noqa: E402
from cases_wispr import his_ptt_keys, wispr_pid, live, chord  # noqa: E402
from cases_wispr_chaos import (_rig, _unrig, _start_relay, _stop_relay, _wait_end, _after, _fmt, _once,  # noqa: E402
                               _deliveries, copies, _marker, _variants, PROC, net_cut, net_restore, _net_note,
                               REPO, _quiet as _cq)
from cases_wispr_soak import (ref_words, clip_ro, te_open, te_front, te_text, te_clear, te_close, pb_get,  # noqa: E402
                              pb_set, _tokens, recall, doubled, _quiet, _relaunch_wispr, _clear_ghost, _seconds)

import cases_wispr_chaos as _cc  # noqa: E402

# **Rig fix, found here (E0, 2026-09-29):** `cases_wispr_chaos._marker` returns the chosen word's count in
# the reference by its exact spelling, while `copies()` counts the word in EITHER number (`_variants`,
# batch 4's *assumption/assumptions* fix). CLIP_SPEECH's head says both "the assumption, the
# assumptions", so every single delivery of it read as `copies 2.0` → "delivered twice" (TQ2, TQ3 FAIL
# with 📦×1). Counted in both numbers here too; patched into the chaos module for every case this
# entry runs (TQ2/TW20 in phase 2 included). The same one-liner belongs in `cases_wispr_chaos.py`.
_marker_exact = _cc._marker

def _marker_both(ref, avoid=()):
    w, per = _marker_exact(ref, avoid)
    if w:
        per = max(1, sum(ref.count(v) for v in _variants(w)))
    return w, per

_cc._marker = _marker_both

LOGDIR = os.path.expanduser("~/wt-lab/night/explore/logs")
REL_S = 6.0                                           # the relay's clip: CLIP_SPEECH's first 6 s
DEAF_RE = r"DEAF|peak 0\b"


# ---------------------------------------------------------------- vocabulary
def _rel_ref():
    r = ref_words(CLIP_SPEECH)
    return r[: max(6, int(len(r) * REL_S / CLIP_SPEECH_SECONDS))]

def _his_clip():
    return clip_ro()[0]

def _his_ref():
    return ref_words(_his_clip())

def _dump(cid, mark, extra=""):
    try:
        os.makedirs(LOGDIR, exist_ok=True)
        with open(os.path.join(LOGDIR, cid + ".log"), "a", encoding="utf-8") as f:
            f.write("==== %s %s\n" % (cid, now_iso()))
            f.write(log_since(mark))
            if extra:
                f.write("\n---- note\n" + extra + "\n")
    except Exception as e:
        print("  (dump %s: %s)" % (cid, e))

def _key_lines(mark, n=14):
    """The lines a verdict is read from, short."""
    pat = (r"📦 delivery|words landed|refused|kept for Recover|No speech|No words|DEAF|🛡️|⌘V from|→ caret|🧷|👻|"
           r"engine switched|finish the sentence first|☠️|over budget|budget|Wispr Flow did not answer|"
           r"stands in|local-forced|exited|quit|restart|🔒|Secure|blind|held for the next bind|spawn|✨")
    out = [l[6:14] + " " + l[l.find("]") + 1:].strip()[:150] for l in log_since(mark).splitlines()
           if re.search(pat, l) and "POST /test" not in l and "⌨️trace" not in l]
    return out[-n:]

def _count(text, ref, avoid=()):
    return copies(text, ref, avoid) if ref else 0.0

def _relay_play(mark, seconds=REL_S, clip=None, after=1.0, stop=True, direct=False):
    """🔼→, the clip into BlackHole, 🔼→ (or the handler, `direct`). True when opened."""
    if direct:
        post("/test/gesture", {"name": "forward-right", "direct": True})
        ok = H.wait_for(lambda: state()["listening"], 8, 0.05)
    else:
        ok = _start_relay(mark)
    if not ok:
        return False
    time.sleep(0.4)
    play(clip or CLIP_SPEECH, seconds=seconds)
    time.sleep(after)
    if stop:
        _stop(direct)
    return True

def _stop(direct=False):
    if not state()["listening"]:
        return False
    if direct:
        post("/test/gesture", {"name": "forward-right", "direct": True})
    else:
        gesture("forward-right")
    return True

def _his(hold_s=None, clip=None, bg=True):
    """His own Wispr push-to-talk (61+60) held over his clip, TextEdit in front. Returns the thread."""
    clip = clip or _his_clip()
    hold = hold_s or min(10.0, _seconds(clip) + 2.5)
    te_front()
    time.sleep(0.2)
    def run():
        post("/test/modifiers", {"keys": his_ptt_keys(), "holdMs": int(hold * 1000)})
        time.sleep(0.4)
        play(clip, seconds=max(1.0, hold - 1.6))
    th = threading.Thread(target=run, daemon=True)
    th.start()
    if not bg:
        th.join(hold + 5)
    return th, hold

def _wait_te(te0, timeout=25):
    return H.wait_for(lambda: (te_text() or "") != te0 and (te_text() or "").strip(), timeout, 0.5)

def _cross(wt, tt, rel_ref, his_ref):
    """Copies of each clip in each destination: (relay→witness, relay→TextEdit, his→TextEdit, his→witness)."""
    return (_count(wt, rel_ref, his_ref), _count(tt, rel_ref, his_ref), _count(tt, his_ref, rel_ref),
            _count(wt, his_ref, rel_ref))

def _judge_pair(o, wt, tt, rel_ref, his_ref, his_expected=True, his_rows=None):
    """The relay sentence once in the witness and never in TextEdit; his words in TextEdit and never
    in the witness. → (verdict, why)."""
    rw, rt, ht, hw = _cross(wt, tt, rel_ref, his_ref)
    v, why = _once(o)
    parts = ["relay→witness %.1f, relay→TextEdit %.1f, his→TextEdit %.1f, his→witness %.1f" % (rw, rt, ht, hw)]
    if rt > 0.4 or hw > 0.4:
        return "BUG", "cross-destination paste; " + parts[0]
    if v != "PASS":
        return ("RIG" if o.get("deaf") else "BUG"), why + "; " + parts[0]
    if his_expected and ht < 0.4:
        # his words nowhere: Wispr's loss when it made no row for his chord
        return ("WISPR" if (his_rows is not None and his_rows == 0) else "BUG"), \
            "his sentence did not reach TextEdit (Wispr rows for it: %s); %s" % (his_rows, parts[0])
    if ht > 1.4 or rw > 1.4:
        return "BUG", "doubled; " + parts[0]
    return "PASS", why + "; " + parts[0]

def _begin(cid, te=True):
    ctx = _rig(te=te)
    ctx["cid"] = cid
    ctx["mark0"] = log_mark()
    return ctx

def _end(ctx, note):
    _dump(ctx["cid"], ctx["mark0"], note)
    _unrig(ctx)

def _deaf(mark):
    return re.search(DEAF_RE, log_since(mark)) is not None

def _rows_since(row0):
    return (live().get("newestRowId") or 0) - (row0 or 0)

def _result(v, why, keys):
    return v, why + " || log: " + " ¦ ".join(keys)


# ================================================================ his chord while a relay sentence is in the air
def _his_during(cid, when):
    ctx = _begin(cid)
    rel_ref, his_ref = _rel_ref(), _his_ref()
    try:
        te_clear(); te0 = te_text()
        mark = log_mark()
        row0 = live().get("newestRowId")
        if not _relay_play(mark):
            return "ERROR", "the relay never opened"
        t_stop = time.time()
        if when == "before-row":
            time.sleep(0.15)
        elif when == "during-row":
            H.wait_for(lambda: (live().get("newestRowId") or 0) != (row0 or 0), 6, 0.03)
        elif when == "typing":
            H.wait_for(lambda: witness_text().strip(), 20, 0.02)
        t_his = time.time() - t_stop
        m_his = log_mark()
        row_h0 = live().get("newestRowId")
        th, hold = _his()
        th.join(hold + 5)
        _wait_end(mark, 40)
        _wait_te(te0, 20)
        time.sleep(3)
        o = _after(ctx, mark, rel_ref)
        o["deaf"] = _deaf(mark)
        wt, tt = witness_text(), te_text()
        his_rows = _rows_since(row_h0)
        # ⌥-glyphs (å ∫ ç ∂ ƒ © ˙ ∆ ˚ ¬ µ ø π œ ® ß † ¨ √ ∑ ≈ ¥ Ω …) live below U+2400; the envelope's own
        # emoji (📸 📁 🖱 + U+FE0F) and RO diacritics are not a leak (E1's first TE1 read them as one).
        odd = sorted(set(c for c in wt if 127 < ord(c) < 0x2400 and c not in "ăâîșțşţĂÂÎȘȚ’‘“”…–—•·"))
        v, why = _judge_pair(o, wt, tt, rel_ref, his_ref, his_rows=his_rows)
        if odd and v == "PASS":
            v, why = "BUG", "odd characters in the witness (modifiers leaked into the typing?) %s; %s" % (odd, why)
        note = "his chord %.2f s after the relay's stop (%s); %s; Wispr rows after his chord %d; %s" % (
            t_his, when, why, his_rows, _fmt(o))
        return _result(v, note, _key_lines(mark))
    finally:
        _end(ctx, "")


@case("TE1", tags=("gesture", "audio", "explore"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="his 61+60 sentence 0.15 s after the relay's stop, before its row: relay once in the witness, his in TextEdit")
def te1():
    """Hypothesis: the relay's capture adopts his row (the first row after its chord) — his words into the
    terminal, the relay's row pasted by Wispr at his caret."""
    return _his_during("TE1", "before-row")


@case("TE2", tags=("gesture", "audio", "explore"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="his 61+60 sentence while the relay's row is `processing`: each sentence in its own place")
def te2():
    """Hypothesis: the firewall's tail (keyed on rows) drops his ⌘V because the relay's row is still open."""
    return _his_during("TE2", "during-row")


@case("TE3", tags=("gesture", "audio", "explore"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="his 61+60 held while the relay types into the witness: the typed text unmodified, his words in TextEdit")
def te3():
    """Hypothesis: his held right ⌥⇧ leaks into the relay's synthetic typing (⌥-glyphs / capitals in the
    terminal), or the typing's keys reach TextEdit once he brings it forward."""
    return _his_during("TE3", "typing")


# ================================================================ engine switch mid-flight and in the tail
def _pick(eid):
    code, r = post("/engine", {"id": eid})
    return (r or {}).get("engine") == eid, (r or {}).get("engine")

@case("TE4", tags=("gesture", "audio", "explore"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="POST /engine whisper mid-sentence and eleven during the Wispr wait: both refused, the sentence once via Wispr")
def te4():
    """Hypothesis: a pick during the Wispr wait (settling, row not yet there) swaps the source and the
    words land nowhere, or the menu tick moves while the source does not."""
    ctx = _begin("TE4")
    H.fake_env(True)
    rel_ref = _rel_ref()
    try:
        mark = log_mark()
        if not _start_relay(mark):
            return "ERROR", "the relay never opened"
        time.sleep(0.4)
        th = threading.Thread(target=lambda: play(CLIP_SPEECH, seconds=REL_S), daemon=True); th.start()
        time.sleep(2.0)
        a_ok, a_eng = _pick("whisper")
        th.join(15); time.sleep(0.8)
        _stop()
        time.sleep(0.2)
        b_ok, b_eng = _pick("eleven")
        _wait_end(mark, 40); time.sleep(3)
        o = _after(ctx, mark, rel_ref)
        e_now = engine().get("engine")
        v, why = _once(o)
        flashes = len(re.findall(r"finish the sentence first", log_since(mark)))
        note = "mid-sentence pick taken %s (engine %s); Wispr-wait pick taken %s (engine %s); engine after %s; " \
               "refusal flashes %d; %s; %s" % (a_ok, a_eng, b_ok, b_eng, e_now, flashes, why, _fmt(o))
        if a_ok or b_ok:
            v = "BUG" if v == "PASS" else v
            note = "a pick went through mid-sentence; " + note
        elif e_now != "wispr":
            v, note = "BUG", "the engine moved after two refused picks; " + note
        elif v == "PASS" and not any(x.startswith("wispr") or x.startswith("local") for x in o["vias"]):
            v = "BUG"
        return _result(v, note, _key_lines(mark))
    finally:
        set_engine("wispr")
        _end(ctx, "")


def _alternate(cid, seq, clips=None):
    """Back-to-back relay sentences, each engine picked the moment the last one's words land (retrying
    the pick until taken). → per-sentence notes, verdicts."""
    ctx = _begin(cid)
    H.fake_env(True)
    rel_ref = _rel_ref()
    res, notes = [], []
    try:
        te_clear(); te0 = te_text()
        for i, eid in enumerate(seq):
            t0 = time.time()
            took = False
            while time.time() - t0 < 30:
                took, _ = _pick(eid)
                if took:
                    break
                time.sleep(0.25)
            wait_pick = time.time() - t0
            if H.RUN.get("fake") and eid.startswith("eleven"):
                H.fake_script(CLIP_SPEECH, REL_S)
            witness_clear()
            mark = log_mark()
            if not _relay_play(mark):
                res.append("ERROR"); notes.append("%d %s: never opened" % (i + 1, eid)); continue
            _wait_end(mark, 40)
            H.wait_for(lambda: witness_text().strip(), 10, 0.2)
            o = _after(ctx, mark, rel_ref)
            o["deaf"] = _deaf(mark)
            v, why = _once(o)
            if v == "PASS":
                want = {"wispr": ("wispr", "local"), "whisper": ("local",), "eleven": ("elevenlabs", "local")}[eid]
                if not any(x.startswith(want) for x in o["vias"]):
                    v, why = "BUG", "via %s on engine %s" % (o["vias"], eid)
                if any(not t.startswith("terminal:") for t in o["tos"]):
                    v, why = "BUG", "delivered to %s" % o["tos"]
            if v != "PASS" and o["deaf"]:
                v = "RIG"
            res.append(v)
            notes.append("%d %s (pick waited %.1f s, taken %s): %s %s" % (i + 1, eid, wait_pick, took, v, _fmt(o)))
        time.sleep(4)
        tt = te_text()
        leak = tt != te0 and tt.strip()
        v = "PASS" if all(x == "PASS" for x in res) else ("BUG" if "BUG" in res else ("RIG" if "RIG" in res else "ERROR"))
        if leak:
            v, notes = "BUG", ["TextEdit got %r" % tt[:80]] + notes
        return _result(v, " | ".join(notes), _key_lines(ctx["mark0"], 20))
    finally:
        set_engine("wispr")
        _end(ctx, "")


@case("TE5", tags=("gesture", "audio", "explore"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="wispr → eleven (fake) → wispr, each pick at the previous sentence's landing (the tail): each sentence once, "
             "on its own engine, nothing at the caret")
def te5():
    """Hypothesis: a pick inside the 10 s relay-owned tail tears the firewall down while Wispr's late ⌘V
    for the last row is still coming — it pastes at his caret (TextEdit in front)."""
    return _alternate("TE5", ["wispr", "eleven", "wispr"])


@case("TE6", tags=("gesture", "audio", "explore"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="4 back-to-back relay sentences alternating wispr / whisper: each once, on its engine, nothing at the caret")
def te6():
    """Hypothesis: Wispr's row for sentence N lands after the switch to local and is delivered again with
    sentence N+1 (a stale row adopted by the next capture), or pasted at the caret."""
    return _alternate("TE6", ["wispr", "whisper", "wispr", "whisper"])


# ================================================================ Wispr quit during its own paste
@case("TE7", tags=("gesture", "audio", "explore", "chaos"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="(a) relay sentence, Wispr SIGKILLed the moment its row turns final (its swallowed ⌘V in flight): once; "
             "(b) his sentence, Wispr killed as it writes the clipboard: nothing of his in the witness, the relay usable after")
def te7():
    """Hypothesis: (a) the exit watch's `abandonForDeadWispr` sends the take to Q14 while the History row
    delivers too — a double; (b) the relay's firewall/rescue treats his dead Wispr's row as its own."""
    ctx = _begin("TE7")
    rel_ref, his_ref = _rel_ref(), _his_ref()
    notes, vs = [], []
    try:
        # (a)
        mark = log_mark()
        row0 = live().get("newestRowId")
        if not _relay_play(mark):
            return "ERROR", "the relay never opened"
        got = H.wait_for(lambda: (live().get("newestRowId") or 0) != (row0 or 0)
                         and live().get("newestRowStatus") not in (None, "processing"), 15, 0.02)
        post(PROC, {"kill": True})
        _wait_end(mark, 40); time.sleep(4)
        o = _after(ctx, mark, rel_ref)
        o["deaf"] = _deaf(mark)
        va, why = _once(o)
        if va != "PASS" and o["deaf"]:
            va = "RIG"
        vs.append(va)
        notes.append("(a) killed at row %s status %s (seen %s): %s — %s; %s" % (
            live().get("newestRowId"), live().get("newestRowStatus"), bool(got), va, why, _fmt(o)))
        post(PROC, {"relaunch": True})
        H.wait_for(lambda: wispr_pid() and engine().get("ready"), 60, 0.5)
        time.sleep(15)          # past AutoLocal.wisprStartupGrace, so (b) is Wispr's
        # (b)
        te_clear(); te0 = te_text(); witness_clear()
        s0 = state(); cc0 = (s0.get("pasteboard") or {}).get("changeCount") or 0
        mb = log_mark()
        th, hold = _his()
        def other_write():
            ev = (state().get("pasteboard") or {}).get("events") or []
            return any(e.get("writer") == "other" and (e.get("changeCount") or 0) > cc0 for e in ev)
        seen = H.wait_for(other_write, hold + 12, 0.03)
        post(PROC, {"kill": True})
        th.join(hold + 5); time.sleep(4)
        tt, wt = te_text(), witness_text()
        hw = _count(wt, his_ref, rel_ref)
        ht = _count(tt, his_ref, rel_ref)
        dels = _deliveries(mb)
        vb = "BUG" if hw > 0.4 or dels else "PASS"
        vs.append(vb)
        notes.append("(b) killed at Wispr's clipboard write (seen %s): his→TextEdit %.1f, his→witness %.1f, relay "
                     "deliveries %s, clipboard now %r" % (bool(seen), ht, hw, dels, (pb_get() or "")[:40]))
        post(PROC, {"relaunch": True})
        H.wait_for(lambda: wispr_pid() and engine().get("ready"), 60, 0.5)
        time.sleep(15)
        # the relay afterwards
        witness_clear(); mc = log_mark()
        _relay_play(mc)
        _wait_end(mc, 40); H.wait_for(lambda: witness_text().strip(), 10, 0.3)
        oc = _after(ctx, mc, rel_ref)
        vc, whyc = _once(oc)
        vs.append(vc)
        notes.append("(c) next relay sentence: %s %s" % (vc, _fmt(oc)))
        v = "BUG" if "BUG" in vs or "FAIL" in vs else ("RIG" if "RIG" in vs else "PASS")
        return _result(v, " | ".join(notes), _key_lines(ctx["mark0"], 22))
    finally:
        if not wispr_pid():
            post(PROC, {"relaunch": True}); H.wait_for(lambda: wispr_pid(), 45, 0.5)
        _end(ctx, "")


@case("TE24", tags=("gesture", "audio", "explore", "chaos"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="relay sentence, Wispr SIGKILLed the instant the firewall reports its ⌘V for the relay's row (the paste "
             "in flight, after the row is final): delivered once, nothing at the caret, the next sentence delivered")
def te24():
    """TE7 (a)'s kill landed at the close, before the row was final. This one waits for the `🛡️ ⌘V from
    Wispr Flow` line (Wispr pasting the finished row) and kills then. Hypothesis: the exit watch's
    `abandonForDeadWispr` sends the take to Q14 while the History row is being delivered — a double."""
    ctx = _begin("TE24")
    rel_ref = _rel_ref()
    try:
        te_clear()
        mark = log_mark()
        if not _relay_play(mark):
            return "ERROR", "the relay never opened"
        got = H.wait_for(lambda: log_has(mark, r"🛡️ ⌘V from Wispr Flow"), 15, 0.01)
        post(PROC, {"kill": True})
        at = (live().get("newestRowStatus"), _deliveries(mark))
        _wait_end(mark, 40); time.sleep(5)
        o = _after(ctx, mark, rel_ref)
        o["deaf"] = _deaf(mark)
        v, why = _once(o)
        rt = _count(te_text(), rel_ref)
        if rt > 0.4:
            v, why = "BUG", "the relay's words at the caret (%.1f)" % rt
        post(PROC, {"relaunch": True})
        H.wait_for(lambda: wispr_pid() and engine().get("ready"), 60, 0.5)
        time.sleep(15)
        witness_clear(); m2 = log_mark()
        _relay_play(m2); _wait_end(m2, 40); H.wait_for(lambda: witness_text().strip(), 10, 0.3); time.sleep(2)
        o2 = _after(ctx, m2, rel_ref)
        v2, why2 = _once(o2)
        if v == "PASS" and v2 != "PASS":
            v, why = v2, "next sentence: " + why2
        if v != "PASS" and o["deaf"]:
            v = "RIG"
        note = "⌘V line seen %s; at the kill row status %s, deliveries so far %s; %s; %s | next: %s" % (
            bool(got), at[0], at[1], why, _fmt(o), _fmt(o2))
        return _result(v, note, _key_lines(mark))
    finally:
        if not wispr_pid():
            post(PROC, {"relaunch": True}); H.wait_for(lambda: wispr_pid(), 45, 0.5)
        _end(ctx, "")


# ================================================================ a Terminal window moves during the delivery
def _cat_tab(name):
    path = "%s/%s.txt" % (WORK, name)
    open(path, "w").close()
    script = "printf '\\\\e]0;%s\\\\a'; stty -echo; exec cat >> %s" % (name, path)
    tty = osa('tell application "Terminal" to set t to do script "%s"' % script,
              'tell application "Terminal" to get tty of t').replace("/dev/", "")
    time.sleep(0.8)
    return tty, path

def _front_tab(tty):
    """Bring the window holding that tty to the front (what his click on another Terminal window does)."""
    return osa('tell application "Terminal"', 'repeat with w in windows', 'repeat with t in tabs of w',
               'if tty of t is "/dev/%s" then' % tty, 'set index of w to 1',
               'return "ok"', 'end if', 'end repeat', 'end repeat', 'return "none"', 'end tell')

def _read(path):
    try:
        return open(path, encoding="utf-8", errors="replace").read()
    except IOError:
        return ""

@case("TE25", tags=("gesture", "audio", "explore"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="a Terminal window opened, or another brought to the front, while the relay types into the bound tab "
             "(inside `writeToTerminalApp`'s 0.5 s between the text and its Return): the text AND its Return land in "
             "the bound tab; nothing lands in the other one")
def te25():
    """Found by TE11 (c): the delivery's `do script "" in t` runs 0.5 s after `do script "<text>" in t`, and `t` is
    an AppleScript reference by position (`item k of tabs of item j of windows`), re-resolved at each use. A window
    opened or raised in between shifts the positions: the Return (and the read-back's `history of t`) goes to
    whichever tab now sits there. Hypothesis: the bound sentence stays unsubmitted and a bare Return — or the
    text — lands in the tab he just opened or clicked."""
    ctx = _begin("TE25", te=False)
    rel_ref = _rel_ref()
    tty_a, path_a = WITNESS["tty"], WITNESS["file"]
    others, notes, vs = [], [], []
    try:
        d_tty, d_path = _cat_tab("wt-te25-d")          # an existing second window, behind
        others.append(d_tty)
        post("/bind", {"tty": tty_a})
        for trial in ("control", "new-window", "raise-other", "new-window-2"):
            witness_clear()
            open(d_path, "w").close()
            mark = log_mark()
            if not _relay_play(mark):
                vs.append("ERROR"); notes.append("%s: never opened" % trial); continue
            seen = H.wait_for(lambda: log_has(mark, r"⌨️ %s foreground=" % tty_a), 30, 0.01)
            acted, c_path = None, None
            if trial.startswith("new-window"):
                c_tty, c_path = _cat_tab("wt-te25-%s" % trial)
                others.append(c_tty); acted = c_tty
            elif trial == "raise-other":
                acted = _front_tab(d_tty)
            _wait_end(mark, 30)
            H.wait_for(lambda: log_has(mark, r"📦 delivery"), 15, 0.2)
            time.sleep(2.5)
            a = _read(path_a)
            other_txt = _read(c_path) if c_path else _read(d_path)
            a_tail = repr(a[-3:])
            stray = other_txt.count("\n")
            leaked = _count(other_txt, rel_ref) > 0.2
            v = "PASS"
            if trial != "control" and (stray or leaked):
                v = "BUG"
            if trial != "control" and not a.endswith("\n\n") and notes and "A ends '\\n\\n'" in notes[0]:
                v = "BUG"
            vs.append(v)
            notes.append("%s: %s — acted %s (delivery line seen %s); A ends %s (%.1f copies); other tab got %d newline(s)%s %r; tail %s" % (
                trial, v, acted, bool(seen), "'\\n\\n'" if a.endswith("\n\n") else a_tail, _count(a, rel_ref), stray,
                ", the sentence" if leaked else "", other_txt[:40],
                [l for l in _key_lines(mark, 30) if "read-back" in l or "Return" in l][:2]))
            _quiet(15)
        v = "BUG" if "BUG" in vs else ("PASS" if all(x == "PASS" for x in vs) else "ERROR")
        return _result(v, " | ".join(notes), _key_lines(ctx["mark0"], 6))
    finally:
        for t in others:
            try:
                H.close_tty_tab(t)
            except Exception:
                pass
        post("/bind", {"tty": tty_a})
        _end(ctx, "")


# ================================================================ p95 + the local transcript prepared ahead, on the real Wispr
# (master 985689a/1069d2c, 2026-09-29 morning: nothing is inserted on a clock — `💻 Use local  ⌘⌃X` is offered)
TRACE_RE = r"📊 fallback: ([^\n]+)"
READY_RE = r"🔮 local transcript ready \+([\d.]+) s after the close"
USE_LOCAL_RE = r"Use local\s+⌘⌃X"

def _trace(mark):
    m = re.findall(TRACE_RE, log_since(mark))
    if not m:
        return {}
    return dict(kv.split("=", 1) for kv in m[-1].split() if "=" in kv)

def _num(tr, k):
    try:
        return float(re.match(r"[-+]?[\d.]+", tr.get(k, "")).group(0))
    except Exception:
        return None

def _chip_rows():
    try:
        return [str(r) for r in (state().get("chip") or []) if r]
    except Exception:
        return []

def _fmt_tr(tr):
    return " ".join("%s=%s" % (k, tr[k]) for k in ("budget", "localEta", "specStart", "localReady", "engineAnswer",
                                                 "budgetExpired", "outcome", "wasted", "toWords") if k in tr)

@case("TE26", tags=("gesture", "audio", "explore", "p95"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="6 warm relay sentences on the real Wispr (6 s / 12 s clips): each delivered once via Wispr, never a local "
             "insert; one `📊 fallback:` line each — the seconds-to-ready table and how often local was ready by the budget")
def te26():
    """Hypothesis: the decode ahead (started budget − localEta into the wait) steals the GPU/CPU Wispr's
    formatting needs, or its words leak into the delivery when Wispr answers in the same beat."""
    ctx = _begin("TE26", te=False)
    post("/test/local-auto", {"on": True, "budget": None, "localEta": None})
    rows, res = [], []
    try:
        for i in range(6):
            secs = REL_S if i % 2 == 0 else 12.0
            ref = _rel_ref() if secs == REL_S else ref_words(CLIP_SPEECH)
            witness_clear()
            mark = log_mark()
            if not _relay_play(mark, seconds=secs):
                res.append("ERROR"); continue
            _wait_end(mark, 40); H.wait_for(lambda: _trace(mark), 15, 0.3); time.sleep(1.5)
            o = _after(ctx, mark, ref)
            tr = _trace(mark)
            v, why = _once(o)
            if v == "PASS" and not any(x.startswith("wispr") for x in o["vias"]):
                v, why = "BUG", "via %s" % o["vias"]
            res.append(v)
            rows.append("%d (%.0f s clip): %s via %s; %s" % (i + 1, secs, v, ",".join(o["vias"]), _fmt_tr(tr) or "no 📊 line"))
            time.sleep(2)
        v = "PASS" if all(x == "PASS" for x in res) else ("BUG" if "BUG" in res or "FAIL" in res else "ERROR")
        return _result(v, " | ".join(rows), _key_lines(ctx["mark0"], 4))
    finally:
        _end(ctx, "")


def _frozen_p95(cid, press):
    ctx = _begin(cid)
    rel_ref = ref_words(CLIP_SPEECH)
    try:
        post("/test/local-auto", {"on": True, "budget": None, "localEta": None})
        te_clear()
        mark = log_mark()
        if not _relay_play(mark, seconds=12.0, after=0.8):
            return "ERROR", "never opened"
        t_close = time.time()
        post(PROC, {"stop": True, "afterMs": 300, "forMs": 20000})
        H.wait_for(lambda: re.search(r"⏱ budget ([\d.]+) s", log_since(mark)), 4, 0.05)
        b = re.search(r"⏱ budget ([\d.]+) s", log_since(mark))
        budget = float(b.group(1)) if b else None
        use_seen = H.wait_for(lambda: any(re.search(USE_LOCAL_RE, r) for r in _chip_rows()), (budget or 5) + 6, 0.05)
        t_use = time.time() - t_close if use_seen else None
        pressed = None
        if press and use_seen:
            pressed = time.time() - t_close
            post("/test/local-now")
        H.wait_for(lambda: time.time() - t_close > (budget or 5) + 1.5, 20, 0.2)
        early = _deliveries(mark)
        over = re.search(r"over budget — ([\d.]+) s since the close[^\n]*nothing is inserted", log_since(mark))
        _wait_end(mark, 40)
        time.sleep(max(0.0, 24 - (time.time() - t_close)))       # the thaw at ~20.3 s and its late row
        o = _after(ctx, mark, rel_ref)
        o["deaf"] = _deaf(mark)
        tr = _trace(mark)
        ready = re.search(READY_RE, log_since(mark))
        rt = _count(te_text(), rel_ref)
        v, why = _once(o)
        if press:
            if v == "PASS" and "local-forced" not in o["vias"]:
                v, why = "BUG", "⌘⌃X on the offer did not insert the local words: via %s" % o["vias"]
        else:
            if early:
                v, why = "BUG", "inserted on a clock before Wispr answered: %s" % early
            elif v == "PASS" and not any(x.startswith("wispr") for x in o["vias"]):
                v, why = "BUG", "via %s" % o["vias"]
        if rt > 0.3:
            v, why = "BUG", "words at the caret (%.1f copies)" % rt
        if not use_seen and v == "PASS":
            v, why = "BUG", "no `Use local  ⌘⌃X` row by budget + 6 s"
        if v not in ("PASS", "BUG") and o["deaf"]:
            v = "RIG"
        note = ("budget %s s; local ready +%s s; Use local on the chip at +%s s; ⌘⌃X at %s; over-budget 'nothing is "
                "inserted' line %s; deliveries before the thaw %s; %s; %s; 📊 %s" % (
                    budget, ready.group(1) if ready else "-", "%.2f" % t_use if t_use else "-",
                    "+%.2f s" % pressed if pressed else "-", bool(over), early, why, _fmt(o), _fmt_tr(tr)))
        return _result(v, note, _key_lines(mark, 16))
    finally:
        post(PROC, {"cont": True})
        _end(ctx, "")

@case("TE27", tags=("gesture", "audio", "explore", "p95", "chaos"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="real Wispr frozen 0.3 s after the stop for 20 s: local ready by the budget, `Use local  ⌘⌃X` offered, NOTHING "
             "inserted at the budget; Wispr's row delivered once at the thaw; 📊 outcome=engine wasted=true")
def te27():
    """Hypothesis: with no clock insert left, a frozen Wispr now holds the sentence until the thaw (20 s) — fine —
    but the late row after `over budget` may be treated as `late` (only logged) and the sentence lost."""
    return _frozen_p95("TE27", press=False)

@case("TE28", tags=("gesture", "audio", "explore", "p95", "chaos"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="real Wispr frozen for 20 s, ⌘⌃X the moment `Use local` shows: local-forced once, at once; Wispr's row at the "
             "thaw only logged, never pasted (not at the caret either)")
def te28():
    """Hypothesis: the prepared words are inserted, then the thawed Wispr's ⌘V (for the same sentence) passes the
    firewall because the relay has closed the capture — a caret double."""
    return _frozen_p95("TE28", press=True)


# ================================================================ ⌘⌃X in the Wispr wait and in the auto countdown
def _auto_on():
    return (post("/test/local-auto", {"on": True, "wisprDown": False, "fakeLaunch": False})[1] or {}).get("localAuto") or {}

@case("TE8", tags=("gesture", "audio", "explore"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="⌘⌃X 0.2 s after the stop (Wispr's row not there yet): local-forced once; Wispr's row only logged, never pasted")
def te8():
    """Hypothesis: the forced local answer and Wispr's row race — both delivered, or Wispr's own ⌘V for
    the row gets through once the relay has let the sentence go."""
    ctx = _begin("TE8")
    rel_ref = _rel_ref()
    try:
        te_clear(); te0 = te_text()
        mark = log_mark()
        if not _relay_play(mark):
            return "ERROR", "the relay never opened"
        time.sleep(0.2)
        ln = state().get("localNow") or {}
        post("/test/local-now")
        _wait_end(mark, 40); time.sleep(8)
        o = _after(ctx, mark, rel_ref)
        o["deaf"] = _deaf(mark)
        v, why = _once(o)
        tt = te_text()
        rt = _count(tt, rel_ref)
        if v == "PASS" and "local-forced" not in o["vias"]:
            v, why = "BUG", "not local-forced: %s" % o["vias"]
        if rt > 0.4:
            v, why = "BUG", "Wispr's row pasted at the caret (%.1f copies)" % rt
        if v != "PASS" and o["deaf"]:
            v = "RIG"
        note = "localNow at the press %s; %s; late row logged only %s; %s" % (ln, why, o["late"], _fmt(o))
        return _result(v, note, _key_lines(mark))
    finally:
        _end(ctx, "")


@case("TE9", tags=("gesture", "audio", "explore", "chaos"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="Wispr frozen after the stop, ⌘⌃X at half the auto budget: local-forced once, local-auto never fires a second")
def te9():
    """Hypothesis: the auto countdown is not cancelled by ⌘⌃X — local-auto delivers the same take again."""
    ctx = _begin("TE9")
    rel_ref = _rel_ref()
    try:
        _auto_on()
        mark = log_mark()
        if not _relay_play(mark, after=0.8):
            return "ERROR", "the relay never opened"
        t_close = time.time()
        post(PROC, {"stop": True, "afterMs": 300, "forMs": 15000})
        H.wait_for(lambda: (state().get("localAuto") or {}).get("budget"), 3, 0.05)
        la = state().get("localAuto") or {}
        budget = la.get("budget") or 3.0
        time.sleep(max(0.0, budget * 0.5 - (time.time() - t_close)))
        t_press = time.time() - t_close
        post("/test/local-now")
        _wait_end(mark, 40)
        time.sleep(max(0.0, 17 - (time.time() - t_close)))       # past the thaw and the late row
        o = _after(ctx, mark, rel_ref)
        o["deaf"] = _deaf(mark)
        v, why = _once(o)
        fired = "over budget" in log_since(mark)
        if v == "PASS" and "local-forced" not in o["vias"]:
            v, why = "BUG", "via %s" % o["vias"]
        if v != "PASS" and o["deaf"]:
            v = "RIG"
        note = "budget %.2f s, ⌘⌃X at %.2f s; over-budget line %s; %s; %s" % (budget, t_press, fired, why, _fmt(o))
        return _result(v, note, _key_lines(mark))
    finally:
        _end(ctx, "")


@case("TE10", tags=("gesture", "audio", "explore", "chaos"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="auto fallback racing the real row: Wispr frozen after the stop and thawed at budget −0.9/−0.6/−0.35/−0.1 s "
             "so the row lands around the fire: every sentence delivered exactly once")
def te10():
    """Hypothesis: the row that lands in the same beat as `over budget` is delivered by both — the History
    row and local-auto — or neither (each thinking the other has it)."""
    ctx = _begin("TE10")
    rel_ref = _rel_ref()
    res, notes = [], []
    try:
        _auto_on()
        for off in (-0.9, -0.6, -0.35, -0.1):
            witness_clear()
            mark = log_mark()
            if not _relay_play(mark, after=0.8):
                res.append("ERROR"); continue
            t_close = time.time()
            post(PROC, {"stop": True, "afterMs": 150, "forMs": 20000})
            H.wait_for(lambda: (state().get("localAuto") or {}).get("budget"), 3, 0.03)
            budget = (state().get("localAuto") or {}).get("budget") or 3.0
            wake = budget + off
            time.sleep(max(0.0, wake - (time.time() - t_close)))
            post(PROC, {"cont": True})
            _wait_end(mark, 40); time.sleep(5)
            o = _after(ctx, mark, rel_ref)
            o["deaf"] = _deaf(mark)
            v, why = _once(o)
            txt = log_since(mark)
            fired = re.search(r"over budget — ([\d.]+) s", txt)
            rs = (live().get("rowSeen") or {})
            if v != "PASS" and o["deaf"]:
                v = "RIG"
            res.append(v)
            notes.append("thaw at budget%+.2f (%.2f s of %.2f): %s via %s, fired %s, row seen %s %s; %s" % (
                off, wake, budget, v, o["vias"], fired.group(1) if fired else "no", rs.get("status"), rs.get("at"),
                "; ".join(x for x in _fmt(o).split("; ")[:3])))
            _quiet(20)
        v = "PASS" if all(x == "PASS" for x in res) else ("BUG" if "BUG" in res or "FAIL" in res else "RIG")
        return _result(v, " | ".join(notes), _key_lines(ctx["mark0"], 24))
    finally:
        post(PROC, {"cont": True})
        _end(ctx, "")


# ================================================================ bind / unbind / rebind
@case("TE11", tags=("gesture", "audio", "explore"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="(a) unbind + rebind mid-sentence → the witness once; (b) unbind mid-sentence, rebind after the stop → "
             "somewhere, once, said; (c) in the tail rebind to a second tab → nothing late in either, the next sentence in B")
def te11():
    """Hypothesis: the recipient latched at the close is the caret when the bind is momentarily gone (F1's
    cousin), and a late Wispr ⌘V in the tail follows the new bind."""
    from cases_gestures import witness_b_open, witness_b_close
    ctx = _begin("TE11")
    rel_ref = _rel_ref()
    notes, vs = [], []
    tty = WITNESS["tty"]
    try:
        te_clear(); te0 = te_text()
        # (a)
        mark = log_mark()
        if not _start_relay(mark):
            return "ERROR", "never opened"
        time.sleep(0.4)
        th = threading.Thread(target=lambda: play(CLIP_SPEECH, seconds=REL_S), daemon=True); th.start()
        time.sleep(1.5); post("/unbind"); time.sleep(1.0); post("/bind", {"tty": tty})
        th.join(15); time.sleep(0.8); _stop()
        _wait_end(mark, 40); H.wait_for(lambda: witness_text().strip(), 10, 0.3); time.sleep(2)
        o = _after(ctx, mark, rel_ref)
        va, why = _once(o)
        if va == "PASS" and any(not t.startswith("terminal:") for t in o["tos"]):
            va, why = "BUG", "to %s" % o["tos"]
        vs.append(va); notes.append("(a) %s %s — %s" % (va, why, _fmt(o)))
        _quiet(20)
        # (b)
        witness_clear(); te_clear(); te0 = te_text()
        mark = log_mark()
        if not _start_relay(mark):
            return "ERROR", "(b) never opened"
        time.sleep(0.4)
        th = threading.Thread(target=lambda: play(CLIP_SPEECH, seconds=REL_S), daemon=True); th.start()
        time.sleep(1.5); post("/unbind")
        th.join(15); time.sleep(0.8); _stop()
        time.sleep(0.5); post("/bind", {"tty": tty})
        _wait_end(mark, 40); time.sleep(6)
        o = _after(ctx, mark, rel_ref)
        tt = te_text()
        rt = _count(tt, rel_ref)
        wc = _count(witness_text(), rel_ref)
        held = "held for the next bind" in log_since(mark)
        # One copy of the 6 s clip reads 0.5 (its marker is counted in both numbers, Wispr keeps one) — so the
        # verdict is on the deliveries: exactly one, to a terminal or held for the bind, and nothing at the caret.
        vb = "PASS" if (o["n"] == 1 and rt < 0.3 and all(t.startswith("terminal:") or t == "held" for t in o["tos"])) \
            else ("PASS" if o["n"] == 0 and (o["recoverable"] or o["failure"]) else "BUG")
        vs.append(vb)
        notes.append("(b) %s: witness %.1f, TextEdit %.1f, held-for-bind %s, tos %s — %s" % (vb, wc, rt, held, o["tos"], _fmt(o)))
        _quiet(20)
        # (c)
        witness_clear(); te_clear()
        mark = log_mark()
        _relay_play(mark)
        H.wait_for(lambda: witness_text().strip(), 30, 0.05)
        btty, bpath = witness_b_open()
        post("/bind", {"tty": btty})
        time.sleep(10)
        a_after = _count(witness_text(), rel_ref)
        b_late = open(bpath, errors="replace").read()
        m2 = log_mark()
        _relay_play(m2)
        _wait_end(m2, 40); time.sleep(4)
        b_txt = open(bpath, errors="replace").read()
        wa = _count(witness_text(), rel_ref)
        vc = "PASS" if a_after <= 1.4 and not b_late.strip() and _count(b_txt, rel_ref) >= 0.6 and wa <= 1.4 else "BUG"
        vs.append(vc)
        notes.append("(c) %s: A after the tail %.1f copies, B before its sentence %r, B after %.1f, A after %.1f; B's delivery %s" % (
            vc, a_after, b_late[:60], _count(b_txt, rel_ref), wa, _deliveries(m2)))
        v = "BUG" if "BUG" in vs or "FAIL" in vs else ("RIG" if "RIG" in vs else "PASS")
        return _result(v, " | ".join(notes), _key_lines(ctx["mark0"], 24))
    finally:
        try:
            witness_b_close()
        except Exception:
            pass
        post("/bind", {"tty": tty})
        _end(ctx, "")


# ================================================================ spawn, kamikaze
def _terminal_ttys():
    out = osa('tell application "Terminal"', 'set r to ""',
              'repeat with w in windows', 'repeat with t in tabs of w', 'set r to r & (tty of t) & ","',
              'end repeat', 'end repeat', 'return r', 'end tell')
    return set(x.replace("/dev/", "") for x in out.split(",") if x.strip())

@case("TE12", tags=("gesture", "audio", "explore"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="🔼↑ spawn sentence on Wispr: delivered once to `spawn:<folder>`, nothing in the bound witness or at the caret")
def te12():
    """Hypothesis: the History-row path skips the spawn flag (it delivers to the bound terminal), or the
    folder menu left on screen blocks the main thread while Wispr's row waits."""
    ctx = _begin("TE12")
    rel_ref = _rel_ref()
    before = _terminal_ttys()
    try:
        te_clear(); te0 = te_text()
        mark = log_mark()
        gesture("forward-up")
        if not H.wait_for(lambda: state()["listening"], 8, 0.05):
            return _result("ERROR", "the spawn sentence never opened", _key_lines(mark))
        time.sleep(0.4); play(CLIP_SPEECH, seconds=REL_S); time.sleep(1.0)
        sp = state().get("spawnPending")
        _stop()
        _wait_end(mark, 45); time.sleep(6)
        o = _after(ctx, mark, rel_ref)
        o["deaf"] = _deaf(mark)
        wt, tt = witness_text(), te_text()
        new = _terminal_ttys() - before
        o["recall"] = 1.0 if o["n"] == 1 else o["recall"]     # the words are in the spawned tab, not the witness
        v, why = _once(o)
        if v == "PASS" and not all(t.startswith("spawn:") for t in o["tos"]):
            v, why = "BUG", "delivered to %s, not spawn:" % o["tos"]
        if _count(wt, rel_ref) > 0.4 or _count(tt, rel_ref) > 0.4:
            v, why = "BUG", "words in the witness (%.1f) / TextEdit (%.1f)" % (_count(wt, rel_ref), _count(tt, rel_ref))
        if v != "PASS" and o["deaf"]:
            v = "RIG"
        note = "spawnPending mid-sentence %s; new Terminal tabs %s; %s; %s" % (sp, sorted(new), why, _fmt(o))
        return _result(v, note, _key_lines(mark))
    finally:
        for t in _terminal_ttys() - before:
            try:
                H.close_tty_tab(t)
            except Exception:
                pass
        _end(ctx, "")


@case("TE13", tags=("gesture", "audio", "explore"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="🔼↓ kamikaze during a Wispr relay sentence: the witness text ends with `kamikaze`, once; the next sentence plain")
def te13():
    """Hypothesis: the History-row delivery path bypasses the kamikaze append (the word is added only on
    the transcript path), or the flag leaks into the next sentence."""
    ctx = _begin("TE13")
    rel_ref = _rel_ref()
    try:
        mark = log_mark()
        if not _start_relay(mark):
            return "ERROR", "never opened"
        time.sleep(0.4)
        th = threading.Thread(target=lambda: play(CLIP_SPEECH, seconds=REL_S), daemon=True); th.start()
        time.sleep(1.0); gesture("forward-down")
        th.join(15); time.sleep(0.8); _stop()
        _wait_end(mark, 40); H.wait_for(lambda: witness_text().strip(), 10, 0.3); time.sleep(2)
        o = _after(ctx, mark, rel_ref)
        o["deaf"] = _deaf(mark)
        wt1 = witness_text()
        k1 = len(re.findall(r"kamikaze", wt1, re.I))
        v, why = _once(o)
        witness_clear()
        m2 = log_mark()
        _relay_play(m2)
        _wait_end(m2, 40); H.wait_for(lambda: witness_text().strip(), 10, 0.3); time.sleep(2)
        k2 = len(re.findall(r"kamikaze", witness_text(), re.I))
        armed = "☠️ kamikaze — this sentence" in log_since(mark)
        if v == "PASS" and (k1 != 1 or k2 != 0):
            v, why = "BUG", "kamikaze in sentence 1: %d, in sentence 2: %d (armed %s)" % (k1, k2, armed)
        if v != "PASS" and o["deaf"]:
            v = "RIG"
        note = "armed %s; %s; via %s; tail of text %r; next sentence kamikaze %d" % (armed, why, o["vias"], wt1.strip()[-40:], k2)
        return _result(v, note, _key_lines(mark))
    finally:
        _end(ctx, "")


# ================================================================ caret vs terminal, every sentence
@case("TE14", tags=("gesture", "audio", "explore"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="🔼→ (terminal) / 🔽→ (Walkie's plain dictation at the caret) alternating ×2 pairs, the next one 0.3 s after "
             "a stop then after the landing: terminal words only in the witness, caret words only in TextEdit, B refused out loud if early")
def te14():
    """Hypothesis: the caret latch of a plain sentence and the terminal latch of a relay sentence cross when
    they alternate fast (F1's latch, two sentences in the queue)."""
    ctx = _begin("TE14")
    rel_ref, his_ref = _rel_ref(), _his_ref()
    notes, vs = [], []
    try:
        for i, gap in enumerate(("tight", "landed")):
            witness_clear(); te_front(); te_clear()
            m1 = log_mark()
            if not _relay_play(m1):
                vs.append("ERROR"); continue
            if gap == "tight":
                time.sleep(0.3)
            else:
                _wait_end(m1, 40); H.wait_for(lambda: witness_text().strip(), 10, 0.2); time.sleep(0.5)
            te_front()
            m2 = log_mark()
            gesture("back-right")
            opened = H.wait_for(lambda: state()["listening"] or log_has(m2, r"opening|recording through"), 6, 0.05)
            refused = log_has(m2, H.__dict__.get("REFUSE_RE", r"refused|one sentence at a time|one engine at a time"))
            if opened and not refused:
                time.sleep(0.4); play(_his_clip()); time.sleep(0.8)
                if state()["listening"]:
                    gesture("back-right")
            _wait_end(m1, 40); _wait_end(m2, 40)
            _wait_te("", 12); time.sleep(4)
            wt, tt = witness_text(), te_text()
            rw, rt, ht, hw = _cross(wt, tt, rel_ref, his_ref)
            loud = bool(re.search(r"refused|one sentence at a time|one engine at a time|finish the sentence", log_since(m2)))
            if rt > 0.4 or hw > 0.4:
                v = "BUG"
            elif rw < 0.6 or rw > 1.4:
                v = "BUG" if not _deaf(m1) else "RIG"
            elif ht < 0.6 and not loud:
                v = "RIG" if _deaf(m2) else "BUG"
            else:
                v = "PASS"
            vs.append(v)
            notes.append("pair %d (%s): %s — relay→witness %.1f, relay→TextEdit %.1f, caret→TextEdit %.1f, caret→witness %.1f, "
                         "B opened %s, B loud %s, deliveries %s" % (i + 1, gap, v, rw, rt, ht, hw, bool(opened), loud,
                                                                    _deliveries(m1) + _deliveries(m2)))
            _quiet(20)
        v = "BUG" if "BUG" in vs else ("RIG" if "RIG" in vs else ("PASS" if vs and all(x == "PASS" for x in vs) else "ERROR"))
        return _result(v, " | ".join(notes), _key_lines(ctx["mark0"], 24))
    finally:
        _end(ctx, "")


# ================================================================ Secure Input, display sleep
@case("TE15", tags=("gesture", "audio", "explore"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="Secure Input held 9 s from 0.5 s into a relay sentence (stop by the handler): the words once in the "
             "witness, nothing at the caret, no ghost microphone after")
def te15():
    """Hypothesis: with every tap blind, Wispr's ⌘V for the relay's row is not swallowed and pastes at the
    caret too (a cross-destination double), or Wispr never sees the stop chord and its mic stays open."""
    ctx = _begin("TE15")
    rel_ref = _rel_ref()
    try:
        te_front(); te_clear(); te0 = te_text()
        mark = log_mark()
        if not _start_relay(mark):
            return "ERROR", "never opened"
        time.sleep(0.5)
        r = post("/test/tap", {"kill": "secure", "seconds": 9})[1]
        time.sleep(0.2)
        play(CLIP_SPEECH, seconds=REL_S); time.sleep(0.8)
        fw = post("/test/firewall")[1]
        _stop(direct=True)
        _wait_end(mark, 45); time.sleep(10)
        o = _after(ctx, mark, rel_ref)
        o["deaf"] = _deaf(mark)
        tt, wt = te_text(), witness_text()
        rt = _count(tt, rel_ref)
        v, why = _once(o)
        mic_after = live().get("micOpen")
        if rt > 0.4:
            v, why = "BUG", "the relay's words at the caret too (%.1f copies) — Wispr's ⌘V passed the blind tap" % rt
        elif v == "PASS" and mic_after:
            v, why = "BUG", "Wispr's microphone still open 10 s after (ghost)"
        if v not in ("PASS", "BUG") and o["deaf"]:
            v = "RIG"
        note = "tap answer %s; firewall mid-sentence tap=%s; %s; TextEdit %r; mic after %s; %s" % (
            {k: r.get(k) for k in ("tap", "hidden", "ok")} if r else r, (fw or {}).get("tap"), why, tt[:60], mic_after, _fmt(o))
        return _result(v, note, _key_lines(mark))
    finally:
        time.sleep(1)
        _end(ctx, "")


@case("TE16", tags=("gesture", "audio", "explore"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="the display put to sleep 1 s into a relay sentence (pmset displaysleepnow), woken after the stop: once, "
             "nothing stuck. (System sleep is not attempted — a VZ guest has no host-side wake in tart 2.34.)")
def te16():
    """Hypothesis: the band's display link and the chip's timers stop with the display; a row poll or the
    settle that hangs off them stalls the delivery until a wake."""
    ctx = _begin("TE16")
    rel_ref = _rel_ref()
    try:
        cap = subprocess.run(["pmset", "-g", "cap"], capture_output=True, text=True).stdout.strip().replace("\n", " ")[:120]
        mark = log_mark()
        if not _start_relay(mark):
            return "ERROR", "never opened"
        time.sleep(0.4)
        th = threading.Thread(target=lambda: play(CLIP_SPEECH, seconds=REL_S), daemon=True); th.start()
        time.sleep(1.0)
        subprocess.run(["pmset", "displaysleepnow"], capture_output=True, timeout=10)
        th.join(15); time.sleep(0.8)
        _stop(direct=True)
        t_stop = time.time()
        _wait_end(mark, 45)
        dt = time.time() - t_stop
        subprocess.run(["caffeinate", "-u", "-t", "2"])
        time.sleep(3)
        o = _after(ctx, mark, rel_ref)
        o["deaf"] = _deaf(mark)
        v, why = _once(o)
        if v != "PASS" and o["deaf"]:
            v = "RIG"
        note = "pmset cap: %s; ended %.1f s after the stop while the display slept; %s; %s" % (cap, dt, why, _fmt(o))
        return _result(v, note, _key_lines(mark))
    finally:
        subprocess.run(["caffeinate", "-u", "-t", "2"])
        _end(ctx, "")


# ================================================================ the network flapping in the row wait
@case("TE17", tags=("gesture", "audio", "explore", "net"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="443 cut 1.2 s / open 1 s / cut 1.2 s right after the stop (the row wait): once (Wispr's row, Q14 or "
             "local-auto), never twice; the next sentence on a steady network once")
def te17():
    """Hypothesis: Wispr's retry after the flap writes a second row (or re-finishes the first) after the
    relay fell back locally — a double."""
    ctx = _begin("TE17")
    rel_ref = _rel_ref()
    try:
        _auto_on()
        mark = log_mark()
        if not _relay_play(mark):
            return "ERROR", "never opened"
        net_cut(1.2, probe=False); time.sleep(1.3); net_restore(); time.sleep(1.0)
        net_cut(1.2, probe=False); time.sleep(1.3); net_restore()
        _wait_end(mark, 60); time.sleep(12)          # Wispr's retries, whatever they write
        o = _after(ctx, mark, rel_ref)
        o["deaf"] = _deaf(mark)
        v, why = _once(o)
        witness_clear()
        m2 = log_mark()
        _relay_play(m2); _wait_end(m2, 40); H.wait_for(lambda: witness_text().strip(), 10, 0.3); time.sleep(2)
        o2 = _after(ctx, m2, rel_ref)
        v2, why2 = _once(o2)
        vv = v if v != "PASS" else v2
        if vv != "PASS" and o["deaf"]:
            vv = "RIG"
        note = "flap: %s | %s %s | next: %s %s" % (_net_note(), why, _fmt(o), why2, _fmt(o2))
        return _result(vv, note, _key_lines(ctx["mark0"], 20))
    finally:
        net_restore()
        _end(ctx, "")


# ================================================================ clipboard race
def _cmd_v():
    """His ⌘V: flagsChanged(⌘) · v down/up with ⌘ · flagsChanged([]), posted at the HID tap."""
    try:
        import Quartz as Q
        src = Q.CGEventSourceCreate(Q.kCGEventSourceStateHIDSystemState)
        seq = [(55, True, Q.kCGEventFlagMaskCommand), (9, True, Q.kCGEventFlagMaskCommand),
               (9, False, Q.kCGEventFlagMaskCommand), (55, False, 0)]
        for code, down, flags in seq:
            e = Q.CGEventCreateKeyboardEvent(src, code, down)
            Q.CGEventSetFlags(e, flags)
            Q.CGEventPost(Q.kCGHIDEventTap, e)
            time.sleep(0.02)
        return "quartz"
    except Exception as e:
        rc = subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "v" using command down'],
                            capture_output=True, text=True, timeout=10)
        return "osascript rc %d (%s)" % (rc.returncode, type(e).__name__)

@case("TE18", tags=("gesture", "audio", "explore"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="his ⌘V into TextEdit at the instant the relay writes its Q17 clipboard (and 0.3 s later): his keys pass "
             "(never swallowed), the witness gets the sentence once")
def te18():
    """Hypothesis: the firewall reads his ⌘V inside the relay-owned window as Wispr's and drops it; or the
    Q17 write lands between his two ⌘Vs and he pastes the relay's sentence into TextEdit."""
    ctx = _begin("TE18")
    rel_ref = _rel_ref()
    try:
        post("/test/key-trace", {"on": True})
        te_front(); te_clear()
        pb_set("zebra-his-own-clipboard ")
        cc0 = (state().get("pasteboard") or {}).get("changeCount") or 0
        mark = log_mark()
        if not _relay_play(mark):
            return "ERROR", "never opened"
        def walkie_write():
            ev = (state().get("pasteboard") or {}).get("events") or []
            return any(e.get("writer") == "walkie" and (e.get("changeCount") or 0) > cc0 for e in ev)
        seen = H.wait_for(walkie_write, 30, 0.02)
        te_front()
        how1 = _cmd_v(); time.sleep(0.3); how2 = _cmd_v()
        _wait_end(mark, 40); time.sleep(4)
        o = _after(ctx, mark, rel_ref)
        o["deaf"] = _deaf(mark)
        tt = te_text()
        txt = log_since(mark)
        dropped = len(re.findall(r"⌘V from [^\n]*dropped|SWALLOWED", txt))
        zebra = tt.count("zebra-his-own-clipboard")
        rt = _count(tt, rel_ref)
        v, why = _once(o)
        if v == "PASS" and not tt.strip():
            v, why = ("RIG" if not re.search(r"key 9|⌘V", txt) else "BUG"), \
                "TextEdit empty after his two ⌘Vs (dropped lines %d)" % dropped
        if v != "PASS" and o["deaf"]:
            v = "RIG"
        note = "Q17 write seen %s; posted %s/%s; TextEdit: his clipboard ×%d, the relay's sentence %.1f copies; dropped/" \
               "swallowed lines %d; %s; %s" % (bool(seen), how1, how2, zebra, rt, dropped, why, _fmt(o))
        return _result(v, note, _key_lines(mark))
    finally:
        post("/test/key-trace", {"on": False})
        _end(ctx, "")


# ================================================================ very short / empty / long mixed takes
@case("TE19", tags=("gesture", "audio", "explore"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="relay takes of 0.3 / 0.6 / 1.0 s of speech and one empty (0.8 s, silence): each ends — once or loudly — "
             "within 20 s; nothing stuck, nothing at the caret")
def te19():
    """Hypothesis: a take under Wispr's minimum makes no row and the relay waits the full 12 s / Q24
    ceiling (or forever) — a stuck `settling`; or a no-audio row is pasted as an empty delivery."""
    ctx = _begin("TE19")
    his = _his_clip()
    notes, vs = [], []
    try:
        te_clear()
        for secs in (0.3, 0.6, 1.0, 0.0):
            witness_clear()
            mark = log_mark()
            if not _start_relay(mark):
                vs.append("ERROR"); notes.append("%.1f s never opened" % secs); continue
            t_open = time.time()
            time.sleep(0.3)
            if secs:
                play(his, seconds=secs, lead=0.1, tail=0.1)
            else:
                time.sleep(0.8)
            # E3's first run stopped the 0.3 s and the empty take inside the 2 s stop dwell
            # (`🎯 ➡️ F10 … but the sentence is only 1322ms old — not stopping it`, by design): the sentence ran on
            # 63.8 s and the next case step became its stop. Short *speech*, never a take under 2.2 s.
            time.sleep(max(0.0, 2.2 - (time.time() - t_open)))
            t_stop = time.time()
            _stop()
            ended = _wait_end(mark, 40)
            dt = time.time() - t_stop
            time.sleep(2)
            o = _after(ctx, mark, None)
            txt = log_since(mark)
            loud = bool(o["recoverable"] or o["failure"] or re.search(r"No speech|no speech|No words|nothing was recording|"
                                                                        r"kept for Recover|too short|refused", txt))
            if not ended or o["up"]:
                v = "BUG"
            elif o["n"] > 1:
                v = "BUG"
            elif o["n"] == 0 and not loud:
                v = "BUG" if secs >= 0.6 else "PASS"      # a 0.3 s blip may end quietly
            elif dt > 20:
                v = "BUG"
            else:
                v = "PASS"
            vs.append(v)
            notes.append("%.1f s: %s — ended %s in %.1f s, 📦×%d %s, loud %s, witness %r" % (
                secs, v, ended, dt, o["n"], o["vias"], loud, witness_text().strip()[:40]))
            _quiet(20)
        tt = te_text()
        if tt.strip():
            vs.append("BUG"); notes.append("TextEdit got %r" % tt[:60])
        v = "BUG" if "BUG" in vs else ("PASS" if all(x == "PASS" for x in vs) else "ERROR")
        return _result(v, " | ".join(notes), _key_lines(ctx["mark0"], 24))
    finally:
        _end(ctx, "")


def _mixed_wav():
    """RO (6 s) · 3 s silence · EN long's first 20 s · 2.5 s silence · RO · 1.5 s silence · CLIP_EN → ~42 s, 16 kHz."""
    import numpy as np
    path = WORK + "/te20-mixed.wav"
    def rd(p, secs=None):
        w = wave.open(p); a = np.frombuffer(w.readframes(w.getnframes()), np.int16); sr = w.getframerate(); w.close()
        if sr != 16000:
            from scipy.signal import resample_poly
            a = resample_poly(a.astype(np.float32), 16000, sr).astype(np.int16)
        return a[: int(16000 * secs)] if secs else a
    z = lambda s: np.zeros(int(16000 * s), np.int16)
    ro = rd(_his_clip())
    parts = [ro, z(3.0), rd(CLIP_EN_LONG, 20), z(2.5), ro, z(1.5), rd(CLIP_EN)]
    a = np.concatenate(parts)
    w = wave.open(path, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(a.tobytes()); w.close()
    en20 = ref_words(CLIP_EN_LONG)
    en20 = en20[: int(len(en20) * 20.0 / max(1.0, _seconds(CLIP_EN_LONG)))]
    ref = _his_ref() + en20 + _his_ref() + ref_words(CLIP_EN)
    return path, ref, len(a) / 16000.0

@case("TE20", tags=("gesture", "audio", "explore", "long"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="a 42 s RO/EN relay sentence with 1.5–3 s pauses: delivered once, whole (recall ≥ 0.5), not doubled")
def te20():
    """Hypothesis: a pause ≥ 2.5 s inside a long Wispr sentence reads as a close (the 100 ms mic poll, the
    peak-0 watchdog on silence), cutting the sentence in two — the second half lost or delivered apart."""
    ctx = _begin("TE20")
    try:
        path, ref, secs = _mixed_wav()
        mark = log_mark()
        if not _start_relay(mark):
            return "ERROR", "never opened"
        time.sleep(0.4); play(path, peak=0.5); time.sleep(1.2)
        still = state()["listening"]
        _stop()
        _wait_end(mark, 90); H.wait_for(lambda: witness_text().strip(), 20, 0.3); time.sleep(3)
        o = _after(ctx, mark, ref)
        o["deaf"] = _deaf(mark)
        wt = witness_text()
        rc = recall(ref, wt)
        v, why = _once(o, min_recall=0.5)
        restarts = len(re.findall(r"🔁 mic:", log_since(mark)))
        if v != "PASS" and o["deaf"]:
            v = "RIG"
        if v == "PASS" and not still:
            v, why = "BUG", "the relay was no longer listening at the clip's end (closed on a pause?)"
        note = "%.0f s clip, %d ref words; listening at the end %s; recall %.2f; %d mic restarts; %s; %s" % (
            secs, len(ref), still, rc or 0, restarts, why, _fmt(o))
        return _result(v, note, _key_lines(mark))
    finally:
        _end(ctx, "")


# ================================================================ two relaunches in a row
@case("TE21", tags=("gesture", "audio", "explore", "cold"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="Wispr relaunched twice 3 s apart, then relay sentences at +1 s (borrowed local) and +15 s (Wispr): each once, "
             "the exit watch on the live pid, no ghost")
def te21():
    """Hypothesis: the exit watch or the process-age check stays on the first relaunch's pid — the +15 s
    sentence is abandoned for a dead Wispr that is alive, or waits on one that is gone."""
    ctx = _begin("TE21")
    rel_ref = _rel_ref()
    notes, vs = [], []
    try:
        p0 = wispr_pid()
        post(PROC, {"relaunch": True}); H.wait_for(lambda: wispr_pid() not in (0, None, p0), 30, 0.2)
        p1 = wispr_pid(); time.sleep(3)
        post(PROC, {"relaunch": True}); H.wait_for(lambda: wispr_pid() not in (0, None, p1), 30, 0.2)
        p2 = wispr_pid()
        for lag in (1.0, 15.0):
            time.sleep(lag)
            witness_clear()
            mark = log_mark()
            if not _relay_play(mark):
                vs.append("ERROR"); continue
            _wait_end(mark, 45); H.wait_for(lambda: witness_text().strip(), 10, 0.3); time.sleep(2)
            o = _after(ctx, mark, rel_ref)
            o["deaf"] = _deaf(mark)
            v, why = _once(o)
            txt = log_since(mark)
            borrowed = bool(re.search(r"Wispr Flow is starting|is not running|process is [\d.]+ s old", txt))
            exit_pid = (live().get("exitWatchPid"))
            if v != "PASS" and o["deaf"]:
                v = "RIG"
            vs.append(v)
            notes.append("+%.0f s: %s — borrowed %s, exit watch pid %s (live %s); %s" % (lag, v, borrowed, exit_pid, wispr_pid(), _fmt(o)))
        time.sleep(3)
        ghost = live().get("micOpen") and not state().get("listening")
        v = "BUG" if "BUG" in vs or "FAIL" in vs or ghost else ("RIG" if "RIG" in vs else "PASS")
        return _result(v, "pids %s → %s → %s; ghost after %s | %s" % (p0, p1, p2, bool(ghost), " | ".join(notes)),
                       _key_lines(ctx["mark0"], 22))
    finally:
        _end(ctx, "")


# ================================================================ a stuck processing row, then his sentence
@case("TE22", tags=("gesture", "audio", "explore", "chaos"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="relay row stuck `processing` (Wispr frozen 0.3 s after the stop, 9 s) → local-auto delivers; his 61+60 sentence "
             "pressed right then (spanning the thaw): the late relay row never at his caret, his words in TextEdit only")
def te22():
    """Hypothesis: at the thaw Wispr finishes the relay's row and pastes it — by then the relay's capture is
    gone, so the firewall passes that ⌘V into TextEdit; or his row is taken for the relay's late one."""
    ctx = _begin("TE22")
    rel_ref, his_ref = _rel_ref(), _his_ref()
    try:
        _auto_on()
        te_clear(); te0 = te_text()
        mark = log_mark()
        if not _relay_play(mark, after=0.8):
            return "ERROR", "never opened"
        post(PROC, {"stop": True, "afterMs": 300, "forMs": 9000})
        H.wait_for(lambda: witness_text().strip() or _deliveries(mark), 15, 0.1)
        t_his = log_mark()
        row_h0 = live().get("newestRowId")
        th, hold = _his(hold_s=8.0)
        th.join(hold + 5)
        _wait_end(mark, 30)
        _wait_te(te0, 25); time.sleep(5)
        o = _after(ctx, mark, rel_ref)
        o["deaf"] = _deaf(mark)
        wt, tt = witness_text(), te_text()
        his_rows = _rows_since(row_h0)
        v, why = _judge_pair(o, wt, tt, rel_ref, his_ref, his_rows=his_rows)
        note = "%s; rows after his chord %d; %s" % (why, his_rows, _fmt(o))
        return _result(v, note, _key_lines(mark, 20))
    finally:
        post(PROC, {"cont": True})
        _end(ctx, "")


# ================================================================ the gated restart during his own sentence
@case("TE23", tags=("gesture", "audio", "explore", "restart"), engine="wispr", lab_only=True, pre=cw.needs_wispr,
      expect="relay-restart.sh (gated) started 1 s into his own 61+60 sentence: the gate waits for it; his words in TextEdit "
             "once, nothing in the witness; the app restarted after; the next relay sentence delivered")
def te23():
    """Hypothesis: the gate reads only the relay's own dictations — his standalone Wispr sentence is not a
    blocker, the app quits under his ⌘V (the firewall gone mid-paste) or the relaunch adopts his row."""
    ctx = _begin("TE23")
    rel_ref, his_ref = _rel_ref(), _his_ref()
    tty = WITNESS["tty"]
    out = {}
    try:
        te_clear(); te0 = te_text()
        pid0 = state().get("pid")
        mark = log_mark()
        th, hold = _his(hold_s=8.0)
        time.sleep(1.0)
        t_r = time.time()
        def restart():
            p = subprocess.run(["./relay-restart.sh", "--max-wait", "90", "--quiet", "3"], cwd=REPO,
                               capture_output=True, text=True, timeout=240)
            out["rc"], out["tail"], out["dt"] = p.returncode, (p.stdout + p.stderr).strip().splitlines()[-3:], time.time() - t_r
        rt = threading.Thread(target=restart, daemon=True); rt.start()
        th.join(hold + 5)
        t_release = time.time() - t_r
        rt.join(200)
        H.wait_for(lambda: get("/up", timeout=2).get("ok"), 60, 0.5)
        _wait_te(te0, 10); time.sleep(3)
        tt = te_text()
        pid1 = state().get("pid")
        ht = _count(tt, his_ref, rel_ref)
        hw = _count(witness_text(), his_ref, rel_ref)
        # the relay again, as after TX13's restart
        mic_override(LOOPBACK); post("/test/autosend", {"on": True})
        if engine().get("engine") != "wispr":
            set_engine("wispr")
        post("/bind", {"tty": tty})
        witness_clear()
        m2 = log_mark()
        _relay_play(m2); _wait_end(m2, 40); H.wait_for(lambda: witness_text().strip(), 10, 0.3); time.sleep(2)
        ctx2 = dict(ctx, pid=state().get("pid"))
        o2 = _after(ctx2, m2, rel_ref)
        v2, why2 = _once(o2)
        waited = out.get("dt", 0) > t_release - 0.5
        if hw > 0.4:
            v = "BUG"
        elif out.get("rc") != 0:
            v = "ERROR"
        elif not waited:
            v = "BUG"
        elif ht < 0.4:
            v = "WISPR" if ht == 0 and pid1 != pid0 else "BUG"
        else:
            v = v2 if v2 != "PASS" else "PASS"
        note = ("restart rc %s after %.1f s (his chord released at %.1f s; waited for it %s); app pid %s → %s; "
                "his→TextEdit %.1f, his→witness %.1f; TextEdit %r; restart tail %s; next relay: %s %s" % (
                    out.get("rc"), out.get("dt", -1), t_release, waited, pid0, pid1, ht, hw, tt[:50], out.get("tail"),
                    why2, _fmt(o2)))
        return _result(v, note, _key_lines(mark, 22))
    finally:
        _end(ctx, "")


if __name__ == "__main__":
    H.main()
