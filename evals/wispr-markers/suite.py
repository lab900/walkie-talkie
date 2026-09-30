#!/usr/bin/env python3
"""The combined feature over all ten base clips, in `wt-lab` (2026-09-30 night, Victor: *"You can run
a more comprehensive test suite if you want during the night"*).

    TART_HOME=~/tart /usr/local/bin/python3 evals/wispr-markers/suite.py run [--arm NAME] [--reps N]
    /usr/local/bin/python3 evals/wispr-markers/suite.py score

Each run is `dryrun.py` in the guest: the real relay (Wispr engine, bridge on) hears a base clip,
the shutter is pressed 1–4 times at seeded random moments (`/test/area`), and the envelope that lands
in the bound tab is read back. Per clip one run with no press is the reference for damage.

Scored per run: **placed** (the strict check passed: every token inline) and per marker **where**:
the word the token stands before, against the first pause of ≥ 0.3 s after the press in the base
clip (what the splice waits for), mapped onto the no-press envelope's words — within one word. Plus
the catch-up time after each marker and the words changed around it.
"""
from __future__ import annotations

import json
import os
import random
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run as R  # noqa: E402  — base clips, word timings, alignment, normalisation

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "combined.jsonl")
GUEST = "/Users/admin/wt-lab/evals/wispr-markers"
TOKEN = re.compile(r"\[📸(\d+)[^\]]*\]")


def presses_for(base, rep, arm):
    dur = len(R.read16(os.path.join(R.CORPUS, base))) / R.RATE
    rnd = random.Random("%s|%d|%s" % (base, rep, arm))
    n = 0 if rep == 0 else rnd.choice([1, 2, 2, 3, 3, 4])
    return sorted(round(rnd.uniform(2.0, dur - 3.0), 2) for _ in range(n))


def run(argv):
    arm = argv[argv.index("--arm") + 1] if "--arm" in argv else "main"
    reps = int(argv[argv.index("--reps") + 1]) if "--reps" in argv else 2
    late = argv[argv.index("--late") + 1] if "--late" in argv else ""
    done = {(r["base"], r["rep"], r["arm"]) for r in load()}
    lock = R.single_driver()  # noqa: F841
    for rep in range(0 if arm == "main" else 1, reps + 1):
        for base, lang in R.BASES:
            if (base, rep, arm) in done:
                continue
            presses = presses_for(base, rep, arm)
            clip = "%s/clips/base__%s" % (GUEST, os.path.basename(base))
            t0 = time.time()
            cmd = ["tart", "exec", "wt-lab", "/usr/bin/python3", GUEST + "/dryrun.py", clip,
                   ",".join("%.2f" % (p + 0.2) for p in presses) or ","] + ([late] if late else [])
            try:
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
                row = json.loads(p.stdout.strip().splitlines()[-1])
            except Exception as ex:  # noqa: BLE001
                row = {"error": str(ex)[-300:]}
            row.update(base=base, lang=lang, rep=rep, arm=arm, press_clip_s=presses,
                       at=time.strftime("%F %T", time.localtime(t0)))
            with open(OUT, "a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            placed = [l for l in row.get("log", []) if "📣 markers" in l]
            print("%s %-36s rep %d %-5s presses %-24s %s" % (row["at"][11:], base[11:], rep, arm, presses,
                                                           (placed[-1][30:140] if placed else row.get("error", "no marker line"))),
                  flush=True)


def load():
    return [json.loads(l) for l in open(OUT) if l.strip()] if os.path.exists(OUT) else []


def words_before_tokens(env):
    """The envelope's sentence (above `[Dictated`): normalised words with tokens removed, and for
    each token its number and how many words stand before it."""
    body = env.split("[Dictated")[0]
    kept, marks = [], []
    pos = 0
    for m in re.finditer(r"\[📸(\d+)[^\]]*\]|[\w]+", body):
        if m.group(1):
            marks.append((int(m.group(1)), len(kept)))
        else:
            w = R.norm_words(m.group(0))
            kept += w
    return kept, marks


def expected_word(base, lang, press, ref):
    """Where the splice should land: the first pause ≥ 0.3 s after the press, as a word index in the
    reference envelope (clip end if none)."""
    audio = R.read16(os.path.join(R.CORPUS, base))
    info = R.word_timings(os.path.join(R.CORPUS, base), lang)
    r = R.frame_rms(audio)
    floor = R.np.percentile(r, 10)
    quiet = r <= max(floor * 2.5, 1e-3)
    start = int(press / 0.02)
    run_ = 0
    t = len(audio) / R.RATE
    for i in range(start, len(quiet)):
        run_ = run_ + 1 if quiet[i] else 0
        if run_ * 0.02 >= 0.3:
            t = (i + 1) * 0.02 - run_ * 0.02
            break
    wl = [R.norm_words(w["w"])[0] if R.norm_words(w["w"]) else "" for w in info["words"]]
    before = sum(1 for w in info["words"] if (w["s"] + w["e"]) / 2 < t)
    return R.map_index(wl, ref, before)


def score(argv):
    rows = [r for r in load() if not r.get("error")]
    ref = {r["base"]: words_before_tokens(r["envelope"])[0] for r in rows if r["rep"] == 0}
    by_arm = {}
    for r in rows:
        if r["rep"] == 0 or r["base"] not in ref:
            continue
        a = by_arm.setdefault(r["arm"], dict(runs=0, placed=0, presses=0, near=0, catch=[], dmg=0, dmg_n=0, why={},
                                             held=[], first=[]))
        # what was still queued at his stop (the drain), and the first catch-up (the late start's)
        a["held"] += [float(m.group(1)) / 1000 for l in r.get("log", [])
                      for m in [re.search(r"holding the stop for (\d+) ms", l)] if m] or [0.0]
        a["first"] += [float(m.group(1)) for l in r.get("log", [])
                       for m in [re.search(r"bridge caught up — Wispr hears him live ([\d.]+) s after the release", l)] if m]
        a["runs"] += 1
        a["presses"] += len(r["press_clip_s"])
        line = next((l for l in r.get("log", []) if "📣 markers" in l), "")
        ok = "markers placed" in line
        a["placed"] += ok
        if not ok:
            why = line.split(": ", 2)[-1][:60] if line else "no marker line"
            a["why"][why] = a["why"].get(why, 0) + 1
        kept, marks = words_before_tokens(r["envelope"])
        base_ref = ref[r["base"]]
        for (n, at), press in zip(sorted(marks), r["press_clip_s"]):
            exp = expected_word(r["base"], r["lang"], press, base_ref)
            got = R.map_index(kept, base_ref, at)
            a["near"] += abs(got - exp) <= 1
            win_ref = base_ref[max(0, exp - 3):exp + 3]
            win_got = kept[max(0, at - 3):at + 3]
            a["dmg_n"] += 1
            a["dmg"] += win_ref != win_got
        a["catch"] += [float(m.group(1)) for l in r.get("log", [])
                       for m in [re.search(r"caught up after the marker in ([\d.]+) s", l)] if m]
    for arm, a in by_arm.items():
        c = sorted(a["catch"])
        print("%s: %d runs, %d presses — placed %d/%d runs; placed markers within one word of the pause "
              "after the press %d/%d; words around changed %d/%d; catch-up after a marker median %.1f s "
              "(max %.1f, n=%d)" % (arm, a["runs"], a["presses"], a["placed"], a["runs"], a["near"], a["dmg_n"],
                                  a["dmg"], a["dmg_n"], c[len(c) // 2] if c else 0, c[-1] if c else 0, len(c)))
        h, f = sorted(a["held"]), sorted(a["first"])
        print("   queued at his stop: median %.2f s, max %.2f s; start caught up: median %.1f s (n=%d)"
              % (h[len(h) // 2] if h else 0, h[-1] if h else 0, f[len(f) // 2] if f else 0, len(f)))
        for why, k in sorted(a["why"].items(), key=lambda kv: -kv[1]):
            print("   fell back %d× — %s" % (k, why))


if __name__ == "__main__":
    {"run": run, "score": score}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda a: print(__doc__))(sys.argv)
