"""**Wispr soak** — TS1–TS6 (2026-09-28), robustness measured over many sentences instead of one
path asserted. Lab only (`lab_only=True`: the real Wispr Flow in the Tart guest, audio through
BlackHole — `docs/vm-lab.md`, `docs/vm-wispr.md`), Engine = Wispr, every case SKIPs without
Wispr running (`needs_wispr`).

Why: the lab run of 2026-09-28 (`evals/plan/vm/wispr/report-lab-2026-09-28.md`) counted the
Wispr-side losses one case at a time — rows left `status NULL`, a relay sentence back as `How`,
rows only at the close after a relaunch, the ghost microphone opened by itself 10–20 s after a
chord to a cold Wispr, main-thread stalls after a relaunch. One run of one case cannot say how
often. These cases say how often.

Each case loops, records one line per sentence (row seen, words landed, `via`, word recall
against the clip's corpus `.txt`, close→landed latency, the relay's stuck flags) and **always**
returns the rates in its evidence string, PASS only above the thresholds:

| case | loop | PASS when |
|---|---|---|
| TS1 | 30 relay sentences to the bound witness, 3 s gaps, CLIP_EN / CLIP_RO alternating | delivered ≥ 95 % and 0 silent losses |
| TS2 | 20 standalone sentences (Wispr's own ptt, `61+60`, TextEdit in front) | ≥ 95 % landed at the caret, 0 into the terminal / outbox |
| TS3 | 20 mixed relay / standalone, seeded random order, 1–6 s gaps | ≥ 90 % routed right, 0 misroutes, 0 silent losses, 0 stuck |
| TS4 | 10 min idle (Wispr's mic sampled every 30 s), then one relay sentence | mic never open, row ≤ 12 s after the gesture, delivered |
| TS5 | 10 relay sentences, each 5 s after a Wispr relaunch (cold) | delivered ≥ 80 % (informational: W11 head loss, ghost mic) |
| TS6 | 10 relay sentences over a known clipboard string (Q17) | 0 violations: clipboard = the sentence after, never the preset back |

Definitions (the same in every case):

- **landed** — any text reached the destination (the witness file, or TextEdit's document).
- **truncated** — landed with fewer than 40 % of the reference's word count (row 15's `How` from
  an 11-word clip). Length, not recall, so a Romanian clip recognised as English is not truncated.
- **delivered** — landed and not truncated.
- **silent loss** — nothing landed and the app said nothing: `lastFailure` unchanged, no audio
  staged for Recover, no refusal line.
- **recall** — share of the reference's words (multiset) found in what landed; lowercase,
  diacritics folded, punctuation dropped (`_tokens`). Reported, not judged (Wispr's own quality).
- **doubled** — the landed text's first three words appear twice (finding 1: a typed delivery
  *and* the `do script` fallback into the witness). Reported, not judged.
- **stuck** — `busy` (Recover staging aside) continuously for > 60 s, or `isRecording` /
  `capturing` / `wisprLive.captureOpen` still up 60 s after the close.

Every loop guards its wall clock (`WT_SOAK_CAP_MIN`, default and ceiling 25 min per case): past
it the loop stops and the evidence says `PARTIAL n/N`, judged on what ran. Between sentences the
relay is let settle (`_quiet`: `busy` false, *audio staged for Recover* aside — that one holds
`busy` for five minutes by design). Each case restores what it touched in `finally` (the open
sentence, TextEdit's document, the clipboard, Wispr's ghost microphone); the harness's `cleanup`
does the bind and the mic override. Per-sentence records land in `WORK/soak-<id>-<time>.json`.

Knobs: `WT_SOAK_N` (2026-09-29: `12` for every loop, or `TS1=10,TS3=8`; unset = the wave-5 counts
30 / 20 / 20 / 10 / 10), `WT_SOAK_SCALE` (0.1–1, shrinks every loop for a smoke run; `WT_SOAK_N` wins), `WT_SOAK_SEED` (TS3),
`WT_SOAK_IDLE_MIN` (TS4, default 10), `WT_CLIP_RO` (a Romanian corpus WAV with its `.txt`).
**CLIP_RO in the guest**: the lab corpus holds three clips; copy
`voice-corpus/2026-09-11/17-08-41-98d90459.{wav,txt}` in (or set `WT_CLIP_RO`), else the cases
scan `corpus.jsonl` for a short RO clip and fall back to CLIP_EN, saying so in the evidence.
TS5 relaunches Wispr ten times: `WT_ALLOW_WISPR_KILL=1` or the lab. A phase running these needs
its cap ≥ 25 min per case (the 08:18 cap killed TW12 mid-case)."""
import json, os, random, re, subprocess, threading, time, unicodedata, wave
from collections import Counter
from harness import *
from cases_wispr import needs_wispr, wispr_pid, his_ptt_keys, KILL_OK

CAP_S = 60 * min(25.0, float(os.environ.get("WT_SOAK_CAP_MIN", "25")))
SCALE = max(0.1, min(1.0, float(os.environ.get("WT_SOAK_SCALE", "1"))))
IDLE_MIN = float(os.environ.get("WT_SOAK_IDLE_MIN", "10"))
STUCK_S = 60
# 5.9 s Romanian, "Postman știe să ruleze teste automate pe pipeline." (8 words).
CLIP_RO_DEFAULT = CORPUS + "/2026-09-11/17-08-41-98d90459.wav"

# What these cases exercise, for `harness.py --changed-since` (evals/plan/README.md).
_COV = covers("wispr", "gesture", "recorder", "local", "delivery", "chip")


def _soak_n():
    """`WT_SOAK_N`: `12` (every soak loop) or `TS1=10,TS3=8` (per case); unset = the wave-5 counts."""
    raw = (os.environ.get("WT_SOAK_N") or "").strip()
    if not raw:
        return {}
    if "=" not in raw:
        return {"*": max(1, int(raw))}
    return {k.strip(): max(1, int(v)) for k, v in (p.split("=", 1) for p in raw.split(",") if "=" in p)}

SOAK_N = _soak_n()

def _n(default, cid=None):
    """The loop's sentence count: `WT_SOAK_N` if it names this case (or all), else the wave-5 count
    shrunk by `WT_SOAK_SCALE`. A shorter loop measures the same rates on fewer sentences — the
    thresholds are shares, so it passes and fails on the same criteria, with wider error bars."""
    n = SOAK_N.get(cid, SOAK_N.get("*"))
    return n if n else max(1, int(round(default * SCALE)))


# ---------------------------------------------------------------- clips and their words
_RO = {}

def clip_ro():
    """(path, note): a short Romanian corpus clip with its `.txt`, or CLIP_EN and why."""
    if "v" in _RO:
        return _RO["v"]
    found = None
    for p in (os.environ.get("WT_CLIP_RO"), CLIP_RO_DEFAULT):
        if p and os.path.exists(p) and os.path.exists(os.path.splitext(p)[0] + ".txt"):
            found = p
            break
    if not found:
        try:
            for line in open(os.path.join(CORPUS, "corpus.jsonl"), encoding="utf-8", errors="replace"):
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("detectedLanguage") != "ro" or not (3.5 <= float(d.get("duration") or 0) <= 7.0):
                    continue
                if int(d.get("words") or 0) < 8:
                    continue
                w, t = os.path.join(CORPUS, d.get("wav") or "-"), os.path.join(CORPUS, d.get("txt") or "-")
                if os.path.exists(w) and os.path.exists(t):
                    found = w
                    break
        except (IOError, OSError):
            pass
    _RO["v"] = (found, None) if found else (CLIP_EN, "no RO clip in this corpus — CLIP_EN in its place")
    return _RO["v"]

def _seconds(wav):
    try:
        w = wave.open(wav)
        s = w.getnframes() / float(w.getframerate())
        w.close()
        return s
    except Exception:
        return 0.0

def ref_words(wav):
    """The corpus `.txt` beside the clip; for CLIP_SPEECH (the first 12 s of CLIP_EN_LONG) its
    share of the long clip's words — the head is exact, the tail approximate."""
    src, share = wav, 1.0
    if wav == CLIP_SPEECH:
        src = CLIP_EN_LONG
        d = _seconds(CLIP_EN_LONG)
        share = (CLIP_SPEECH_SECONDS / d) if d else 1.0
    txt = os.path.splitext(src)[0] + ".txt"
    words = _tokens(open(txt, encoding="utf-8", errors="replace").read()) if os.path.exists(txt) else []
    if share < 1.0 and words:
        words = words[: max(1, int(round(len(words) * share)))]
    return words

def _tokens(s):
    """Lowercase, diacritics folded (ș→s, ă→a), anything not a letter or digit a separator."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    return [t for t in re.split(r"[^0-9a-z]+", s) if t]

def recall(ref, hyp_text):
    if not ref:
        return None
    got = Counter(_tokens(hyp_text))
    return sum((Counter(ref) & got).values()) / float(len(ref))

def head_missing(ref, hyp_text, head=8):
    """W11: of the reference's first `head` words, how many are absent from what landed."""
    got = set(_tokens(hyp_text))
    return sum(1 for w in ref[:head] if w not in got)

def doubled(hyp_text):
    t = _tokens(hyp_text)
    if len(t) < 6:
        return False
    tri = t[:3]
    return sum(1 for i in range(len(t) - 2) if t[i:i + 3] == tri) >= 2


# ---------------------------------------------------------------- numbers
def pct(a, b):
    return "%.1f %%" % (100.0 * a / b) if b else "n/a"

def perc(xs, p):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    k = max(0, min(len(xs) - 1, int(-(-p * len(xs) // 100)) - 1))   # nearest rank
    return xs[k]

def fmt_s(x):
    return "-" if x is None else "%.1f s" % x

def dump(case_id, extra):
    path = os.path.join(WORK, "soak-%s-%s.json" % (case_id, time.strftime("%Y%m%d-%H%M%S")))
    try:
        with open(path, "w") as f:
            json.dump(extra, f, indent=1, default=str)
    except Exception as e:
        return "(json not written: %s)" % e
    return path


class Clock(object):
    """The case's wall clock: `room(need)` is False once `need` more seconds would cross the cap."""
    def __init__(self, cap=CAP_S):
        self.t0 = time.time()
        self.end = self.t0 + cap
        self.hit = False

    def left(self):
        return self.end - time.time()

    def room(self, need):
        if self.left() < need:
            self.hit = True
        return not self.hit

    def elapsed(self):
        return time.time() - self.t0


# ---------------------------------------------------------------- the relay's state
def _really_busy(s):
    """`busy` without *audio staged for Recover* (it holds busy for five minutes by design)."""
    why = [w for w in (s.get("busyWhy") or []) if not str(w).startswith("audio staged for Recover")]
    return bool(why)

def _quiet(timeout=90):
    """Until the relay is idle (Recover staging aside); (True, s waited) or (False, busyWhy)."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            s = state()
            if not _really_busy(s) and not s.get("listening") and not s.get("settling"):
                return True, time.time() - t0
        except Exception:
            pass
        time.sleep(0.4)
    try:
        return False, state().get("busyWhy")
    except Exception:
        return False, "state unreadable"

def _unstick():
    """Whatever a stuck sentence left: cancel it and give the relay 10 s."""
    try:
        s = state()
        if s.get("listening") or s.get("settling") or s.get("isRecording"):
            post("/test/cancel")
    except Exception:
        pass
    _quiet(10)

def _mic_open():
    try:
        return bool((state().get("wisprLive") or {}).get("micOpen"))
    except Exception:
        return None

def _relaunch_wispr(settle=5.0, timeout=45):
    """Kill + `open` Wispr by path (`/test/wispr-proc`), until a new pid is up and the source is
    ready; then `settle` s. Returns seconds taken, or None."""
    pid0 = wispr_pid()
    t0 = time.time()
    post("/test/wispr-proc", {"relaunch": True})
    ok = wait_for(lambda: wispr_pid() not in (0, pid0) and engine().get("ready"), timeout, 0.3)
    if not ok:
        return None
    time.sleep(settle)
    return time.time() - t0

def _clear_ghost():
    """Wispr's microphone open with no sentence (finding 2): relaunch it (lab / KILL_OK), 20 s
    to settle. Returns what was done."""
    if not _mic_open():
        return "mic closed"
    if not KILL_OK:
        return "ghost mic open — not relaunched (WT_ALLOW_WISPR_KILL=1 or the lab)"
    took = _relaunch_wispr(settle=20.0)
    return "ghost mic open — Wispr relaunched (%s), mic now %s" % (fmt_s(took), "open" if _mic_open() else "closed")


# ---------------------------------------------------------------- TextEdit and the clipboard
TE = {"name": None}

def _osa_out(*lines):
    cmd = ["osascript"]
    for l in lines:
        cmd += ["-e", l]
    try:
        # 25 s, not 8 (lab wave 2, 2026-09-28): under a guest load of 7–40 `make new document`
        # overran 8 s and TS2/TS3 ERRORed before their first sentence.
        r = subprocess.run(cmd, capture_output=True, timeout=25)
        return r.returncode, r.stdout.decode("utf-8", "replace").rstrip("\n")
    except Exception:
        return 1, ""

def te_open():
    rc, name = _osa_out('tell application "TextEdit"', 'activate', 'set d to make new document',
                        'set text of d to ""', 'return name of d', 'end tell')
    TE["name"] = name if rc == 0 and name else None
    time.sleep(0.8)
    return TE["name"]

def _te_ref():
    return 'document "%s"' % TE["name"] if TE["name"] else "document 1"

def te_front():
    _osa_out('tell application "TextEdit"', 'activate',
             'try', 'set index of (first window whose name is "%s") to 1' % (TE["name"] or ""), 'end try',
             'end tell')

def te_text():
    rc, out = _osa_out('tell application "TextEdit" to get text of %s' % _te_ref())
    return out if rc == 0 else ""

def te_clear():
    _osa_out('tell application "TextEdit" to set text of %s to ""' % _te_ref())

def te_close():
    if TE["name"]:
        _osa_out('tell application "TextEdit" to close %s saving no' % _te_ref())
    TE["name"] = None

UTF8 = dict(os.environ, LANG="en_US.UTF-8", LC_ALL="en_US.UTF-8")

def pb_get():
    try:
        r = subprocess.run(["pbpaste"], capture_output=True, timeout=3, env=UTF8)
        if r.returncode == 0:
            return r.stdout.decode("utf-8", "replace")
    except Exception:
        pass
    rc, out = _osa_out("return (the clipboard as text)")
    return out if rc == 0 else None

def pb_set(s):
    try:
        subprocess.run(["pbcopy"], input=(s or "").encode("utf-8"), timeout=3, env=UTF8)
    except Exception:
        pass


# ---------------------------------------------------------------- one sentence
def _outbox_n():
    try:
        return outbox_count()
    except (IOError, OSError):
        return 0

def _snapshot():
    s = state()
    lv = s.get("wisprLive") or {}
    return {"row": lv.get("newestRowId"), "last": s.get("lastDelivery"), "fail": s.get("lastFailure"),
            "recov": (s.get("recoverable") or {}).get("path"), "outbox": _outbox_n(),
            "cc": (s.get("pasteboard") or {}).get("changeCount"), "micOpen": lv.get("micOpen")}

def _watch(rec, snap, mark, t_close, dest, te0=None, sampler=None):
    """After the close: poll until the words landed (and the relay went quiet) or the relay went
    quiet with nothing (3 s), or 75 s. Fills `rec` in place."""
    t_land = t_row = busy_since = None
    max_busy, quiet_since, landed_text = 0.0, None, ""
    last_te = 0.0
    cap = 75.0 if dest == "witness" else 30.0
    while True:
        now = time.time()
        try:
            s = state()
        except Exception:
            time.sleep(0.3)
            continue
        lv = s.get("wisprLive") or {}
        if t_row is None and lv.get("newestRowId") is not None and lv.get("newestRowId") != snap["row"]:
            t_row = now
        b = _really_busy(s)
        if b:
            busy_since = busy_since or now
            max_busy = max(max_busy, now - busy_since)
            quiet_since = None
        else:
            busy_since = None
            quiet_since = quiet_since or now
        if dest == "witness":
            txt = witness_text()
        elif now - last_te > 0.5:
            last_te, txt = now, te_text()
        else:
            txt = landed_text
        if txt.strip() and txt != te0:
            if t_land is None:
                t_land = now
            if txt != landed_text:
                landed_text = txt
        if sampler:
            sampler(now)
        if t_land and quiet_since and now - t_land >= 1.2 and now - quiet_since >= 1.0:
            break
        if not t_land and quiet_since and now - t_close >= 4.0 and now - quiet_since >= 3.0:
            # standalone: the relay stays idle while Wispr formats and pastes by itself — give it the cap
            if dest == "witness" or now - t_close >= cap:
                break
        if now - t_close >= cap:
            break
        if max_busy > STUCK_S:
            break
        time.sleep(0.15)
    s = state()
    lv = s.get("wisprLive") or {}
    txt = log_since(mark)
    deliveries = re.findall(r"📦 delivery: (\S+) → (\S+)", txt)
    last = s.get("lastDelivery") or {}
    via = deliveries[-1][0] if deliveries else (last.get("via") if last != snap["last"] else None)
    to = deliveries[-1][1] if deliveries else (last.get("to") if last != snap["last"] else None)
    # Lab wave 2 (2026-09-28): TS1 #13/#14 were refusals on the chip (`🚫 start refused — …`,
    # flashed `⏳ …`) counted *silent* because only the W6 wording was matched. Any of the
    # relay's refusal lines is loud; so is the C pair's `nothing was recording`.
    refusal = re.search(r"(?:dictate gesture refused|🚫 start refused|🎙️ ⬅️ [^\n]* refused|start refused) — ([^\n]*)"
                        r"|(nothing was recording[^\n]*)", txt)
    loud = (s.get("lastFailure") != snap["fail"]) or \
           ((s.get("recoverable") or {}).get("path") not in (None, snap["recov"])) or bool(refusal)
    still = [k for k, v in (("isRecording", s.get("isRecording")), ("capturing", s.get("capturing")),
                            ("captureOpen", lv.get("captureOpen"))) if v]
    stuck = max_busy > STUCK_S or (bool(still) and time.time() - t_close > STUCK_S)
    rec.update({
        "row": t_row is not None, "rowStatus": lv.get("newestRowStatus") if t_row else None,
        "rowNull": t_row is not None and lv.get("newestRowStatus") is None,
        "rowAfterGesture": round(t_row - rec["tGesture"], 2) if t_row else None,
        "landed": bool(landed_text.strip()), "text": landed_text.strip()[:400],
        "closeToLanded": round(t_land - t_close, 2) if t_land else None,
        "via": via, "to": to, "outbox": _outbox_n() - snap["outbox"],
        "loud": loud, "why": ((refusal.group(1) or refusal.group(2)) if refusal else (s.get("lastFailure") or {}).get("why") if loud else None),
        "noWords": "No words came back" in txt, "stuck": stuck, "stillUp": still, "maxBusy": round(max_busy, 1),
    })
    if stuck:
        _unstick()
    return rec

def _judge(rec, ref):
    words = _tokens(rec.get("text") or "")
    rec["refWords"] = len(ref)
    rec["recall"] = None if not rec["landed"] else (round(recall(ref, rec["text"]), 2) if ref else None)
    rec["truncated"] = bool(rec["landed"] and ref and len(words) < 0.4 * len(ref))
    rec["delivered"] = bool(rec["landed"] and not rec["truncated"])
    rec["silent"] = bool(not rec["landed"] and not rec["loud"])
    rec["doubled"] = doubled(rec.get("text") or "")
    return rec

def relay_sentence(clip, idx=0, dest="witness", te_check=False, sampler=None):
    """🔼→ (the bound witness), the clip into BlackHole, 🔼→ again — the stop only if the relay is
    still listening (TW4: a stop sent to a relay that gave up opens a stray sentence)."""
    ref = ref_words(clip)
    snap = _snapshot()
    witness_clear()
    te0 = te_text() if te_check else None
    mark = log_mark()
    rec = {"i": idx, "kind": "relay", "clip": os.path.basename(clip), "tGesture": time.time(),
           "ghostBefore": bool(snap["micOpen"]), "at": now_iso()}
    gesture("forward-right")
    opened = wait_for(lambda: state()["listening"] or log_has(mark, r"opening the dictation|mic: recording through"), 8, 0.1)
    rec["opened"] = bool(opened)
    if opened:
        time.sleep(0.4)
        play(clip)
        time.sleep(1.2)
        rec["stopSent"] = bool(state()["listening"])
        if rec["stopSent"]:
            gesture("forward-right")
    t_close = time.time()
    _watch(rec, snap, mark, t_close, "witness", sampler=sampler)
    if te_check:
        rec["intoTextEdit"] = te_text() != te0
    return _judge(rec, ref)

def standalone_sentence(clip, idx=0):
    """Wispr's own push-to-talk (`/engine.wisprShortcuts.ptt`, 61+60) held over the clip, TextEdit
    in front; Wispr pastes at the caret itself (Q9). The witness stays bound: nothing may reach it."""
    ref = ref_words(clip)
    te_front()
    te_clear()
    time.sleep(0.3)
    te0 = te_text()
    snap = _snapshot()
    witness_clear()
    mark = log_mark()
    rec = {"i": idx, "kind": "standalone", "clip": os.path.basename(clip), "tGesture": time.time(),
           "ghostBefore": bool(snap["micOpen"]), "at": now_iso()}
    hold = min(10.0, _seconds(clip) + 2.0 + 1.0)      # 0.4 lead-in + play's 0.5 + 0.5 pads + 0.6 tail
    post("/test/modifiers", {"keys": his_ptt_keys(), "holdMs": int(hold * 1000)})
    rec["opened"] = True
    time.sleep(0.4)
    play(clip, seconds=max(1.0, hold - 2.0))
    time.sleep(max(0.0, hold - (time.time() - rec["tGesture"])) + 0.2)
    t_close = time.time()
    _watch(rec, snap, mark, t_close, "textedit", te0=te0)
    rec["intoTerminal"] = bool(witness_text().strip())
    return _judge(rec, ref)


# ---------------------------------------------------------------- the summary
def summary(recs, n_planned, clock, extra=""):
    n = len(recs)
    delivered = sum(r["delivered"] for r in recs)
    trunc = sum(r["truncated"] for r in recs)
    lost = sum(not r["landed"] for r in recs)
    silent = sum(r["silent"] for r in recs)
    rows = sum(r["row"] for r in recs)
    nulls = sum(r["rowNull"] for r in recs)
    stuck = sum(r["stuck"] for r in recs)
    dbl = sum(r["doubled"] for r in recs)
    vias = Counter(r["via"] or "none" for r in recs if r["kind"] == "relay")
    rc = [r["recall"] for r in recs if r["recall"] is not None]
    lat = [r["closeToLanded"] for r in recs]
    head = ("PARTIAL %d/%d%s · " % (n, n_planned, " (cap %.0f min hit)" % (CAP_S / 60) if clock.hit else "")
            if n < n_planned else "%d/%d · " % (n, n_planned))
    s = (head + "delivered %d (%s) · truncated %d · lost %d (silent %d) · rows %d/%d (NULL %d) · "
         % (delivered, pct(delivered, n), trunc, lost, silent, rows, n, nulls))
    if vias:
        s += "via " + ", ".join("%s %d" % kv for kv in sorted(vias.items())) + " · "
    s += ("recall mean %s min %s · close→landed p50 %s p90 %s · doubled %d · stuck %d · %.0f s%s"
          % ("%.2f" % (sum(rc) / len(rc)) if rc else "-", "%.2f" % min(rc) if rc else "-",
             fmt_s(perc(lat, 50)), fmt_s(perc(lat, 90)), dbl, stuck, clock.elapsed(), extra))
    return s

def lines(recs):
    out = []
    for r in recs:
        out.append("#%02d %s %s row %s%s landed %s via %s recall %s%s%s%s%s" % (
            r["i"], r["kind"][:5], r["clip"][:12], "✓" if r["row"] else "✗",
            "(NULL)" if r["rowNull"] else "", fmt_s(r["closeToLanded"]) if r["landed"] else "✗",
            r["via"] or "-", "-" if r["recall"] is None else "%.2f" % r["recall"],
            " TRUNC" if r["truncated"] else "", " SILENT" if r["silent"] else "",
            (" loud: " + str(r["why"]).replace("\n", " ")[:50]) if r["loud"] and not r["landed"] else "",
            " STUCK" if r["stuck"] else ""))
    return "\n".join(out)

def _between(clock, gap, stuck_log):
    ok, w = _quiet(90)
    if not ok:
        stuck_log.append("not idle 90 s after a sentence: %s" % (w,))
        _unstick()
    if gap:
        time.sleep(gap)

def _finish(case_id, recs, extra_json=None):
    d = {"case": case_id, "at": now_iso(), "records": recs}
    d.update(extra_json or {})
    return dump(case_id, d)

def _restore():
    """Common `finally`: the open sentence cancelled, the relay quiet."""
    try:
        s = state()
        if s.get("listening") or s.get("settling"):
            post("/test/cancel")
        _quiet(30)
    except Exception:
        pass


# ---------------------------------------------------------------- TS1: 30 relay sentences
@case("TS1", covers=_COV, tags=("gesture", "audio", "soak"), engine="wispr", lab_only=True, pre=needs_wispr,
      expect="30 relay sentences (EN/RO, 3 s gaps) to the bound witness: delivered ≥ 95 %, 0 silent losses")
def ts1():
    """Loss, fallback and latency rates over 30 consecutive relay sentences to the bound witness,
    CLIP_EN and CLIP_RO alternating, a 3 s gap after each settles."""
    clock, recs, stuck_log = Clock(), [], []
    ro, ro_note = clip_ro()
    N = _n(30, "TS1")
    bind_witness()
    mic_override(LOOPBACK)
    ghost = _clear_ghost()
    try:
        for i in range(N):
            clip = CLIP_EN if i % 2 == 0 else ro
            if not clock.room(_seconds(clip) + 60):
                break
            recs.append(relay_sentence(clip, i + 1))
            _between(clock, 3.0, stuck_log)
    finally:
        _restore()
    fb = sum(1 for r in recs if r["via"] == "local-fallback")
    extra = " · fallback %d (%s)%s%s · start: %s" % (fb, pct(fb, len(recs)), (" · " + ro_note) if ro_note else "",
                                                     (" · " + "; ".join(stuck_log)) if stuck_log else "", ghost)
    path = _finish("TS1", recs)
    note = summary(recs, N, clock, extra) + " · " + path + "\n" + lines(recs)
    n = len(recs)
    ok = n > 0 and sum(r["delivered"] for r in recs) >= 0.95 * n and not any(r["silent"] for r in recs)
    return ("PASS" if ok else "FAIL"), note


# ---------------------------------------------------------------- TS2: 20 standalone sentences
@case("TS2", covers=_COV, tags=("gesture", "audio", "soak"), engine="wispr", lab_only=True, pre=needs_wispr,
      expect="20 standalone sentences (Wispr's ptt 61+60, TextEdit in front): rows created, ≥ 95 % at the caret, 0 into the terminal")
def ts2():
    """Wispr's own sentences left to Wispr (Q9) over 20 tries: a row each, the words at TextEdit's
    caret, nothing into the bound witness and no outbox line."""
    clock, recs, stuck_log = Clock(), [], []
    ro, ro_note = clip_ro()
    N = _n(20, "TS2")
    bind_witness()
    mic_override(LOOPBACK)
    ghost = _clear_ghost()
    if not te_open():
        return "ERROR", "TextEdit would not open a document (osascript)"
    try:
        for i in range(N):
            clip = CLIP_EN if i % 2 == 0 else ro
            if not clock.room(_seconds(clip) + 45):
                break
            recs.append(standalone_sentence(clip, i + 1))
            _between(clock, 2.0, stuck_log)
    finally:
        _restore()
        te_close()
    n = len(recs)
    term = sum(1 for r in recs if r.get("intoTerminal") or r["outbox"] > 0)
    extra = " · into the terminal/outbox %d%s%s · start: %s" % (term, (" · " + ro_note) if ro_note else "",
                                                               (" · " + "; ".join(stuck_log)) if stuck_log else "", ghost)
    path = _finish("TS2", recs)
    note = summary(recs, N, clock, extra) + " · " + path + "\n" + lines(recs)
    ok = n > 0 and sum(r["delivered"] for r in recs) >= 0.95 * n and term == 0
    return ("PASS" if ok else "FAIL"), note


# ---------------------------------------------------------------- TS3: 20 mixed, seeded
@case("TS3", covers=_COV, tags=("gesture", "audio", "soak"), engine="wispr", lab_only=True, pre=needs_wispr,
      expect="20 relay/standalone sentences in seeded random order, 1–6 s gaps: ≥ 90 % routed right, 0 misroutes, 0 silent, 0 stuck")
def ts3():
    """Routing under a mix: a relay sentence belongs in the witness and not in TextEdit; a
    standalone one at TextEdit's caret and not in the witness or the outbox. Seeded RNG (the seed
    in the evidence, `WT_SOAK_SEED` replays it); the gaps follow the relay going idle, so the
    short ones fall inside the relay-owned 10 s tail (TW8b's window)."""
    seed = int(os.environ.get("WT_SOAK_SEED") or (int(time.time()) % 100000))
    rng = random.Random(seed)
    clock, recs, stuck_log = Clock(), [], []
    ro, ro_note = clip_ro()
    N = _n(20, "TS3")
    plan = [(rng.choice(("relay", "standalone")), rng.choice((CLIP_EN, ro)), (float(os.environ["WT_SOAK_GAP"]) if os.environ.get("WT_SOAK_GAP") else round(rng.uniform(1.0, 6.0), 1)))
            for _ in range(N)]
    bind_witness()
    mic_override(LOOPBACK)
    ghost = _clear_ghost()
    if not te_open():
        return "ERROR", "TextEdit would not open a document (osascript)"
    try:
        for i, (kind, clip, gap) in enumerate(plan):
            if not clock.room(_seconds(clip) + 75):
                break
            if kind == "relay":
                te_front()
                te_clear()
                r = relay_sentence(clip, i + 1, te_check=True)
                r["misrouted"] = bool(r.get("intoTextEdit"))
                r["routedRight"] = r["delivered"] and not r["misrouted"]
            else:
                r = standalone_sentence(clip, i + 1)
                r["misrouted"] = bool(r.get("intoTerminal") or r["outbox"] > 0)
                r["routedRight"] = r["delivered"] and not r["misrouted"]
            r["gap"] = gap
            recs.append(r)
            _between(clock, gap, stuck_log)
    finally:
        _restore()
        te_close()
    n = len(recs)
    right = sum(r["routedRight"] for r in recs)
    mis = sum(r["misrouted"] for r in recs)
    kinds = Counter(r["kind"] for r in recs)
    extra = (" · seed %d · relay %d / standalone %d · routed right %d (%s) · misrouted %d%s%s · start: %s"
             % (seed, kinds.get("relay", 0), kinds.get("standalone", 0), right, pct(right, n), mis,
                (" · " + ro_note) if ro_note else "", (" · " + "; ".join(stuck_log)) if stuck_log else "", ghost))
    path = _finish("TS3", recs, {"seed": seed, "plan": [(k, os.path.basename(c), g) for k, c, g in plan]})
    note = summary(recs, N, clock, extra) + " · " + path + "\n" + \
        "\n".join(l + ("  MISROUTED" if r["misrouted"] else "") for l, r in zip(lines(recs).split("\n"), recs))
    ok = (n > 0 and right >= 0.9 * n and mis == 0 and not any(r["silent"] for r in recs)
          and not any(r["stuck"] for r in recs) and not stuck_log)
    return ("PASS" if ok else "FAIL"), note


# ---------------------------------------------------------------- TS4: idle soak
@case("TS4", covers=_COV, tags=("gesture", "audio", "soak"), engine="wispr", lab_only=True, pre=needs_wispr,
      expect="10 min idle: Wispr's mic never open (sampled every 30 s); then one relay sentence: row ≤ 12 s, delivered")
def ts4():
    """Nothing for `WT_SOAK_IDLE_MIN` (10) minutes — Wispr's microphone sampled every 30 s
    (`wisprLive.micOpen`: the ghost of finding 2 must not appear on its own), the relay's `busy`
    with it — then one relay sentence: the row within 12 s of the gesture and the words delivered."""
    clock = Clock()
    idle_s = 60 * min(IDLE_MIN * SCALE if SCALE < 1 else IDLE_MIN, 20.0)
    bind_witness()
    mic_override(LOOPBACK)
    ghost = _clear_ghost()
    samples, recs = [], []
    try:
        t0 = time.time()
        while time.time() - t0 < idle_s and clock.room(90):
            try:
                s = state()
                samples.append({"t": round(time.time() - t0), "micOpen": (s.get("wisprLive") or {}).get("micOpen"),
                                "busy": _really_busy(s), "wisprPid": (s.get("wisprLive") or {}).get("wisprPid")})
            except Exception as e:
                samples.append({"t": round(time.time() - t0), "error": str(e)})
            time.sleep(min(30.0, max(0.0, idle_s - (time.time() - t0))))
        idled = time.time() - t0
        if clock.room(60):
            recs.append(relay_sentence(CLIP_EN, 1))
    finally:
        _restore()
    opened = [x["t"] for x in samples if x.get("micOpen")]
    busy = [x["t"] for x in samples if x.get("busy")]
    pids = sorted(set(x.get("wisprPid") for x in samples if x.get("wisprPid")))
    r = recs[0] if recs else None
    path = _finish("TS4", recs, {"idle": samples})
    note = ("idle %.0f s, %d samples · Wispr mic open in %d (at %s) · relay busy in %d · Wispr pid(s) %s · "
            % (idled, len(samples), len(opened), opened[:6], len(busy), pids))
    if r:
        note += ("then: row %s (%s after the gesture) · landed %s · delivered %s · via %s · recall %s · close→landed %s"
                 % (r["row"], fmt_s(r["rowAfterGesture"]), r["landed"], r["delivered"], r["via"],
                    r["recall"], fmt_s(r["closeToLanded"])))
    else:
        note += "PARTIAL: the cap left no room for the sentence"
    note += " · start: %s · %s" % (ghost, path)
    ok = (r is not None and not opened and r["row"] and (r["rowAfterGesture"] or 99) <= 12.0 and r["delivered"])
    return ("PASS" if ok else "FAIL"), note


# ---------------------------------------------------------------- TS5: cold, after a relaunch
@case("TS5", covers=_COV, tags=("gesture", "audio", "soak", "cold"), engine="wispr", lab_only=True,
      pre=lambda: needs_wispr() or (None if KILL_OK else "relaunches his Wispr: WT_ALLOW_WISPR_KILL=1 or the lab"),
      expect="10 relay sentences each 5 s after a Wispr relaunch: delivered ≥ 80 % (informational: W11 head loss, ghost mic)")
def ts5():
    """W11 and the ghost microphone as rates: relaunch Wispr, 5 s after it is up and ready one
    relay sentence (CLIP_SPEECH, 12 s), then Wispr's microphone watched 25 s after the relay went
    quiet (finding 2 saw it open 10–20 s after). Head loss = of the first 8 reference words, how
    many are missing from what landed."""
    clock, recs, stuck_log = Clock(), [], []
    N = _n(10, "TS5")
    bind_witness()
    mic_override(LOOPBACK)
    ghosts, relaunch_s, fails = [], [], 0
    try:
        for i in range(N):
            if not clock.room(_seconds(CLIP_SPEECH) + 150):
                break
            took = _relaunch_wispr(settle=5.0)
            if took is None:
                fails += 1
                continue
            relaunch_s.append(took)
            r = relay_sentence(CLIP_SPEECH, i + 1)
            ref = ref_words(CLIP_SPEECH)
            r["headMissing"] = head_missing(ref, r["text"]) if r["landed"] else min(8, len(ref))
            _between(clock, 0, stuck_log)
            t0, g = time.time(), None
            while time.time() - t0 < 25 and clock.room(10):
                if _mic_open():
                    g = round(time.time() - t0, 1)
                    break
                time.sleep(1.0)
            r["ghostMicAfter"] = g
            if g is not None:
                ghosts.append(i + 1)
            recs.append(r)
    finally:
        _restore()
        if _mic_open() and KILL_OK:
            _relaunch_wispr(settle=10.0)
    n = len(recs)
    heads = [r["headMissing"] for r in recs]
    extra = (" · head words missing (of 8) %s, mean %s · ghost mic after %d sentence(s) %s · relaunch→ready p50 %s"
             " · relaunch failures %d%s" % (heads, "%.1f" % (sum(heads) / float(len(heads))) if heads else "-",
                                           len(ghosts), ghosts, fmt_s(perc(relaunch_s, 50)), fails,
                                           (" · " + "; ".join(stuck_log)) if stuck_log else ""))
    path = _finish("TS5", recs, {"relaunchSeconds": relaunch_s, "ghosts": ghosts})
    note = summary(recs, N, clock, extra) + " · " + path + "\n" + \
        "\n".join("%s head-missing %d%s" % (l, r["headMissing"],
                                            (" GHOST@%ss" % r["ghostMicAfter"]) if r["ghostMicAfter"] is not None else "")
                  for l, r in zip(lines(recs).split("\n"), recs))
    ok = n > 0 and sum(r["landed"] for r in recs) >= 0.8 * n
    return ("PASS" if ok else "FAIL"), note


# ---------------------------------------------------------------- TS6: the clipboard holds the sentence (Q17)
@case("TS6", covers=_COV, tags=("gesture", "audio", "soak"), engine="wispr", lab_only=True, pre=needs_wispr,
      expect="10 relay sentences over a known clipboard string: after each the clipboard holds the sentence, never the preset again")
def ts6():
    """Q17 (2026-09-28) against Wispr's clipboard dance (W8): before each relay sentence the
    clipboard is set to a known string; the clipboard is read (`pbpaste`, 4 Hz) from the gesture
    until the words landed. A violation is (a) after the sentence the clipboard does not hold it
    (≥ 80 % of the landed words), or (b) the preset read again after the clipboard had moved off it
    (a restore mid-sentence). `state.pasteboard` gives the writers after the preset (walkie /
    other, `skipped` = writes folded into one 50 ms tick), reported with each sentence."""
    probe = "wt-soak-probe-%d" % int(time.time())
    saved = pb_get()
    pb_set(probe)
    if pb_get() != probe:
        pb_set(saved or "")
        return "ERROR", "the clipboard cannot be read back from this process (pbpaste / osascript)"
    clock, recs, stuck_log = Clock(), [], []
    ro, ro_note = clip_ro()
    N = _n(10, "TS6")
    bind_witness()
    mic_override(LOOPBACK)
    ghost = _clear_ghost()
    try:
        for i in range(N):
            clip = CLIP_EN if i % 2 == 0 else ro
            if not clock.room(_seconds(clip) + 60):
                break
            preset = "wt-soak-preset-%02d-%06d" % (i + 1, random.randint(0, 999999))
            pb_set(preset)
            time.sleep(0.3)
            cc0 = (state().get("pasteboard") or {}).get("changeCount")
            reads, stop = [], threading.Event()

            def poll():
                while not stop.is_set():
                    v = pb_get()
                    reads.append((time.time(), v))
                    stop.wait(0.25)
            th = threading.Thread(target=poll)
            th.daemon = True
            th.start()
            try:
                r = relay_sentence(clip, i + 1)
            finally:
                stop.set()
                th.join(3)
            final = pb_get()
            seq = [v for _, v in reads if v is not None]
            moved = next((k for k, v in enumerate(seq) if v != preset), None)
            back = moved is not None and any(v == preset for v in seq[moved:])
            ev = [e for e in ((state().get("pasteboard") or {}).get("events") or [])
                  if cc0 is not None and (e.get("changeCount") or 0) > cc0]
            writers = [e.get("writer") + ("+%d" % e["skipped"] if e.get("skipped") else "") for e in ev]
            holds = None
            if r["landed"]:
                holds = (recall(_tokens(r["text"]), final or "") or 0) >= 0.8
            r.update({"preset": preset, "pbFinal": (final or "")[:200], "pbFinalIsPreset": final == preset,
                      "presetBack": back, "pbHoldsSentence": holds, "writers": writers,
                      "otherAfterWalkie": ("walkie" in [e.get("writer") for e in ev]) and
                                          any(e.get("writer") == "other" for e in
                                              ev[[e.get("writer") for e in ev].index("walkie") + 1:])})
            r["violation"] = bool(back or final == preset or holds is False)
            recs.append(r)
            _between(clock, 2.0, stuck_log)
    finally:
        _restore()
        pb_set(saved or "")
    n = len(recs)
    viol = sum(r["violation"] for r in recs)
    back = sum(r["presetBack"] for r in recs)
    notheld = sum(1 for r in recs if r["pbHoldsSentence"] is False)
    finalpre = sum(r["pbFinalIsPreset"] for r in recs)
    other = sum(r["otherAfterWalkie"] for r in recs)
    extra = (" · Q17 violations %d (preset back mid-sentence %d, clipboard ≠ sentence after %d, preset at the end %d)"
             " · an 'other' write after walkie's %d · checked on %d landed%s%s · start: %s"
             % (viol, back, notheld, finalpre, other, sum(r["landed"] for r in recs),
                (" · " + ro_note) if ro_note else "", (" · " + "; ".join(stuck_log)) if stuck_log else "", ghost))
    path = _finish("TS6", recs)
    note = summary(recs, N, clock, extra) + " · " + path + "\n" + \
        "\n".join("%s pb %s writers %s%s" % (l, {True: "=sentence", False: "≠sentence", None: "-"}[r["pbHoldsSentence"]],
                                             ",".join(r["writers"]) or "-", " VIOLATION" if r["violation"] else "")
                  for l, r in zip(lines(recs).split("\n"), recs))
    ok = n > 0 and viol == 0 and any(r["landed"] for r in recs)
    return ("PASS" if ok else "FAIL"), note
