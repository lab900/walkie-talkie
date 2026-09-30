#!/usr/bin/env python3
"""Drive the Wispr catch-up eval in `wt-lab` from the host; one JSON row per run into results.jsonl.

    TART_HOME=~/tart python3 evals/wispr-catchup/run.py [--plan b,b,l:warm,l:late2,l:late5,p:2,p:5] [--clips a.wav,b.wav]
    python3 evals/wispr-catchup/run.py --score          # one JSON line per run, scored against its baselines
    python3 evals/wispr-catchup/run.py --table          # the README's tables
    TART_HOME=~/tart python3 evals/wispr-catchup/run.py --plan r:1.0,r:1.0,r:1.25,r:1.5,r:1.75,r:2.0   # Wispr's tolerance

The guest must be up with the rig of README.md (From Walkie installed and on, the relay running with
Engine = Wispr); `guest.py` and `clips/` copied to ~/wt-lab/evals/wispr-catchup/. Each run is one
`tart exec` of guest.py — `tart exec` is the only chain in the guest with a microphone grant.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results.jsonl")
GUEST = "/Users/admin/wt-lab/evals/wispr-catchup"
PLAN = "b,b,l:warm,l:late2,l:late5,p:2,p:5"


def run_one(clip, step):
    kind, _, arg = step.partition(":")
    cmd = ["tart", "exec", "wt-lab", "/usr/bin/python3", GUEST + "/guest.py", kind, GUEST + "/clips/" + clip]
    if arg:
        cmd.append(arg)
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    line = (p.stdout.strip().splitlines() or [""])[-1]
    try:
        row = json.loads(line)
    except ValueError:
        row = {"error": (p.stderr or p.stdout)[-800:]}
    row.update(clip=clip, kind=kind, arg=arg, at=time.strftime("%F %T", time.localtime(t0)))
    return row


def relay_back():
    """The guest relay gone (a crash, or a quit the QuitGate deferred): open it again and wait."""
    subprocess.run(["tart", "exec", "wt-lab", "open", "/Applications/Walkie Talkie.app"])
    for _ in range(60):
        if subprocess.run(["tart", "exec", "wt-lab", "curl", "-fsS", "-m", "3", "http://127.0.0.1:8917/ping"],
                          capture_output=True).returncode in (0, 22):
            time.sleep(3)
            return
        time.sleep(2)


# ── scoring ──────────────────────────────────────────────────────────────────
FILLERS = {"a", "aa", "aaa", "ă", "ăă", "ăăă", "e", "ee", "eee", "uh", "um", "hmm", "so", "deci", "and"}


def words(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return [w for w in re.findall(r"[a-z0-9]+", s) if w not in FILLERS]


def wer(ref, hyp):
    r, h = words(ref), words(hyp)
    if not r:
        return 0.0 if not h else 1.0
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev, d[j] = d[j], cur
    return d[len(h)] / len(r)


def head_kept(ref, hyp, n=5):
    """At least n-1 of the reference's first n words (fillers aside) among the hypothesis's first n+3."""
    r, h = words(ref)[:n], words(hyp)[: n + 3]
    return sum(w in h for w in r) >= len(r) - 1


def tail_kept(ref, hyp, n=5):
    r, h = words(ref)[-n:], words(hyp)[-(n + 3):]
    return sum(w in h for w in r) >= len(r) - 1


def caught_up_s(log):
    for l in log or []:
        m = re.search(r"caught up — Wispr hears him live ([\d.]+) s after the release", l)
        if m:
            return float(m.group(1))
    return None


def released(log):
    for l in log or []:
        m = re.search(r"released \(.*?\) (\d+) ms after the gesture — ([\d.]+) s held, ([\d.]+) s of silence cut.*?([\d.]+) s behind", l)
        if m:
            return {"release_ms": int(m.group(1)), "held": float(m.group(2)), "cut": float(m.group(3)), "behind": float(m.group(4))}
    return {}


def score(rows):
    """Each run against the closer of the clip's two baselines — Wispr's own noise is the floor."""
    by_clip = {}
    for r in rows:
        if "error" in r:
            continue
        by_clip.setdefault(r["clip"], []).append(r)
    out = []
    for clip, rs in by_clip.items():
        bases = [r for r in rs if (r["kind"] == "b" or (r["kind"] == "r" and float(r["arg"]) == 1.0)) and r.get("asr")]
        if not bases:
            continue
        noise = wer(bases[0]["asr"], bases[1]["asr"]) if len(bases) > 1 else None
        for r in rs:
            if r["kind"] == "b" or (r["kind"] == "r" and float(r["arg"]) == 1.0):
                continue
            hyp = r.get("asr", "")
            ref = min(bases, key=lambda b: wer(b["asr"], hyp))["asr"]
            rel = released(r.get("log"))
            out.append({
                "clip": clip, "run": r["kind"] + ":" + r["arg"],
                "head": head_kept(ref, hyp), "tail": tail_kept(ref, hyp),
                "wer": round(wer(ref, hyp), 3), "noise": None if noise is None else round(noise, 3),
                "caught_up": caught_up_s(r.get("log")), **rel,
                "delivery": r.get("delivery"), "empty": not hyp,
                "asr": hyp, "ref": ref,
            })
    return out


def table(scored):
    """Markdown: one row per run kind, then one row per clip × kind."""
    import statistics as st
    kinds = ["l:warm", "l:late2", "l:late5", "p:2", "p:5"] + ["r:%s" % x for x in ("1.25", "1.5", "1.75", "2.0", "2.5")]
    out = ["| run | n | head kept | tail kept | WER median (max) | Wispr's own noise, median | caught up after release, s (median / max) | not Wispr's words |",
           "|---|---|---|---|---|---|---|---|"]
    for k in kinds:
        rs = [r for r in scored if r["run"] == k]
        if not rs:
            continue
        cu = [r["caught_up"] for r in rs if r["caught_up"] is not None]
        nz = [r["noise"] for r in rs if r["noise"] is not None]
        lost = sum(1 for r in rs if r["empty"] or (r["delivery"] and r["delivery"] != "wispr-history"))
        out.append("| %s | %d | %d/%d | %d/%d | %.2f (%.2f) | %s | %s | %d |" % (
            k, len(rs), sum(r["head"] for r in rs), len(rs), sum(r["tail"] for r in rs), len(rs),
            st.median(r["wer"] for r in rs), max(r["wer"] for r in rs),
            "%.2f" % st.median(nz) if nz else "–",
            "%.1f / %.1f" % (st.median(cu), max(cu)) if cu else "–", lost))
    out += ["", "| clip | run | head | tail | WER | noise | released, ms | cut, s | caught up, s | delivery |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(scored, key=lambda r: (r["clip"], r["run"])):
        out.append("| %s | %s | %s | %s | %.2f | %s | %s | %s | %s | %s |" % (
            r["clip"][:-4], r["run"], "✓" if r["head"] else "✗", "✓" if r["tail"] else "✗", r["wer"],
            r["noise"], r.get("release_ms", "–"), r.get("cut", "–"),
            r["caught_up"] if r["caught_up"] is not None else "–", r["delivery"] or "–"))
    return "\n".join(out)


def main(argv):
    if "--table" in argv:
        print(table(score([json.loads(l) for l in open(RESULTS) if l.strip()])))
        return
    if "--score" in argv:
        rows = [json.loads(l) for l in open(RESULTS) if l.strip()]
        for s in score(rows):
            print(json.dumps(s, ensure_ascii=False))
        return
    plan = PLAN
    if "--plan" in argv:
        plan = argv[argv.index("--plan") + 1]
    clips = sorted(f for f in os.listdir(os.path.join(HERE, "clips")) if f.endswith(".wav"))
    if "--clips" in argv:
        clips = argv[argv.index("--clips") + 1].split(",")
    stop_at = os.environ.get("STOP_AT")  # HH:MM — no new run after it (the VM is handed over)
    for clip in clips:
        for step in plan.split(","):
            if stop_at and time.strftime("%H:%M") >= stop_at:
                print("⏹ stop time %s reached" % stop_at, flush=True)
                return
            row = run_one(clip, step)
            if "relay not answering" in row.get("error", ""):
                with open(RESULTS, "a") as f:
                    f.write(json.dumps(dict(row, error="relay gone before this run"), ensure_ascii=False) + "\n")
                relay_back()
                row = run_one(clip, step)
            with open(RESULTS, "a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print("%s %-8s %-28s %s" % (row["at"][11:], step, clip, (row.get("asr") or row.get("error", ""))[:90]),
                  flush=True)


if __name__ == "__main__":
    main(sys.argv)
