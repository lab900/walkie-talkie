#!/usr/bin/env python3
"""Wispr envelope: the words first, every picture after them with its clock.

Victor, 2026-09-30 (dictated): *"să nu înceapă prompt-ul generat cu imagine zero, ci să pui
imaginea respectivă și toate celelalte cu timestamp asociat la finalul, după textul prompt-ului
… rulează și aici niște evaluri … încearcă să minimizezi cât de mult poți textul"*.

Wispr gives no word timings, so no token can sit in the words; today 📸0 leads them anyway and the
pressed frames lose their pointer in the footer. Three arms, a fresh `claude -p` per run with no
tools (answers from the text alone), Sonnet and Opus:

  now   — what the app sends today on the Wispr path
  tail  — no leading token; each frame one full row: token + pointer + clock + files
  fold  — no leading token; the file template once, then one short row per frame
"""
import json, re, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

D = "[📁=$WALKIE_SHOTS/2026-09-30-09-57-21/11-31-07]"
WORDS = ("Uite, aici pe butonul ăsta de Save nu se întâmplă nimic când dau click. Și după aia, "
         "în consolă apare eroarea asta roșie. Fix it, and add a test for it.")
HINT = "[Dictated in RO or EN]"
SIZE = "3456x2234px"

SCENES = {
  "three": {
    "now": f"[📸0🖱️@1952:1134 auto]\n{WORDS}\n\n{HINT}\n{D}\n"
           f"[📸0 = 📁/screenshot-0-800px.jpg, or -original.jpg at {SIZE}]\n"
           f"[📸1 at 0:04 = 📁/screenshot-1-800px.jpg, or -original.jpg at {SIZE}]\n"
           f"[📸2 at 0:09 = 📁/screenshot-2-800px.jpg, or -original.jpg at {SIZE}]",
    "tail": f"{WORDS}\n\n{HINT}\n{D}\n"
            f"[📸0🖱️@1952:1134 auto at 0:00 = 📁/screenshot-0-800px.jpg, or -original.jpg at {SIZE}]\n"
            f"[📸1🖱️@1204:388 at 0:04 = 📁/screenshot-1-800px.jpg, or -original.jpg at {SIZE}]\n"
            f"[📸2🖱️@610:1790 at 0:09 = 📁/screenshot-2-800px.jpg, or -original.jpg at {SIZE}]",
    "fold": f"{WORDS}\n\n{HINT}\n{D}\n"
            f"[📸n = 📁/screenshot-n-800px.jpg, or -original.jpg at {SIZE}]\n"
            f"[📸0🖱️@1952:1134 auto at 0:00]\n"
            f"[📸1🖱️@1204:388 at 0:04]\n"
            f"[📸2🖱️@610:1790 at 0:09]",
  },
  "one": {
    "now": f"[📸0🖱️@1952:1134 auto]\n{WORDS}\n\n{HINT}\n{D}\n"
           f"[📸0 = 📁/screenshot-0-800px.jpg, or -original.jpg at {SIZE}]",
    "tail": f"{WORDS}\n\n{HINT}\n{D}\n"
            f"[📸0🖱️@1952:1134 auto at 0:00 = 📁/screenshot-0-800px.jpg, or -original.jpg at {SIZE}]",
  },
}

Q = {
  "three": """{
 "first_words": "<the first four words the user said>",
 "auto": "<which picture was taken automatically rather than by the user, e.g. 📸1, or none>",
 "p1_small": "<path of the smaller file of 📸1>",
 "p2_full": "<path of the full-resolution file of 📸2>",
 "t2": <seconds into the dictation 📸2 was taken, a number, or null if not stated>,
 "mouse1": "<pointer position in 📸1 as x,y, or unknown>",
 "error_frame": "<which picture most likely shows the red console error>",
 "unclear": "<anything you had to guess at, one line>"
}""",
  "one": """{
 "first_words": "<the first four words the user said>",
 "auto": "<which picture was taken automatically rather than by the user, e.g. 📸1, or none>",
 "p0_small": "<path of the smaller file of 📸0>",
 "p0_full": "<path of the full-resolution file of 📸0>",
 "mouse0": "<pointer position in 📸0 as x,y, or unknown>",
 "unclear": "<anything you had to guess at, one line>"
}""",
}
HEAD = "\n---\nDo not open any file. From the message above alone, answer as one JSON object and nothing else:\n"
DIR = "$WALKIE_SHOTS/2026-09-30-09-57-21/11-31-07/"
EXPECT = {
  "three": {"first_words": "uite, aici pe butonul", "auto": "📸0", "p1_small": DIR + "screenshot-1-800px.jpg",
            "p2_full": DIR + "screenshot-2-original.jpg", "t2": 9, "mouse1": "1204,388", "error_frame": "📸2"},
  "one": {"first_words": "uite, aici pe butonul", "auto": "📸0", "p0_small": DIR + "screenshot-0-800px.jpg",
          "p0_full": DIR + "screenshot-0-original.jpg", "mouse0": "1952,1134"},
}


def norm(v):
    return re.sub(r"[\s\"'.]", "", str(v)).lower()


def score(scene, ans):
    out = {}
    for k, want in EXPECT[scene].items():
        got = ans.get(k)
        if k == "first_words":
            out[k] = norm(got).startswith(norm(want).replace(",", "")) or norm(got).startswith(norm(want))
        elif k == "t2":
            out[k] = isinstance(got, (int, float)) and abs(got - want) < 0.6
        elif k.startswith("mouse"):
            out[k] = norm(got).replace("(", "").replace(")", "") == want
        else:
            out[k] = norm(got) == norm(want)
    return out


def one(scene, arm, model, run):
    msg = SCENES[scene][arm]
    with tempfile.TemporaryDirectory() as d:
        p = subprocess.run(["claude", "-p", msg + HEAD + Q[scene], "--model", model,
                            "--allowedTools", "", "--output-format", "json"],
                           cwd=d, capture_output=True, text=True, timeout=600)
    out = {"scene": scene, "arm": arm, "model": model, "run": run, "chars": len(msg)}
    try:
        m = re.search(r"\{.*\}", json.loads(p.stdout)["result"], re.S)
        out["answer"] = json.loads(m.group(0))
        out["ok"] = score(scene, out["answer"])
    except Exception as e:
        out["error"] = f"{e}: {p.stdout[-400:]} {p.stderr[-400:]}"
    print(json.dumps(out, ensure_ascii=False), flush=True)
    return out


if __name__ == "__main__":
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    jobs = [(s, a, m, r) for s in SCENES for a in SCENES[s] for m in ("sonnet", "opus") for r in range(runs)]
    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(lambda j: one(*j), jobs))
    json.dump(results, open(__file__.replace("ask.py", "results.json"), "w"), ensure_ascii=False, indent=1)
    agg = {}
    for r in results:
        key = (r["scene"], r["arm"])
        a = agg.setdefault(key, {"chars": r["chars"], "n": 0})
        a["n"] += 1
        for k, v in (r.get("ok") or {}).items():
            a[k] = a.get(k, 0) + bool(v)
    for (s, arm), a in agg.items():
        print(s, arm, json.dumps(a, ensure_ascii=False))
