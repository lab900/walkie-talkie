#!/usr/bin/env python3
"""Is `-800px` still read as the width once the footer stops saying `at 800px width`?

Victor, 2026-09-29: *"is it still comprehensible the 800 is width? eval it on a few
claude code runs."* Two envelopes, his own dictation of 10:02, identical except for
the footer row; each run a fresh `claude -p` with no tools (answers from the text
alone, as a model skimming the prompt would), in an empty directory.
"""
import json, re, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

HEAD = "[📸0🖱️@290:518 auto]\nSo, if I take this idea now\n\n[Dictated in RO or EN]\n[📁=$WALKIE_SHOTS/2026-09-29-09-57-23/10-02-42]\n"
ARMS = {
    "old": HEAD + "[📸0 = 📁/screenshot-0-800px.jpg at 800px width, or -original.jpg at 1920x1080px]",
    "new": HEAD + "[📸0 = 📁/screenshot-0-800px.jpg, or -original.jpg at 1920x1080px]",
}
QUESTIONS = """
---
Do not open any file. From the message above alone, answer as one JSON object and nothing else:
{
 "w800": <width in pixels of screenshot-0-800px.jpg, a number>,
 "h800": <its height in pixels, a number — work it out if you can>,
 "dim": "<is 800 that file's width, its height, its longest side, a quality/size setting, or unclear>",
 "pointer_in_800": "<where the pointer is inside screenshot-0-800px.jpg, as x,y>",
 "unclear": "<anything you had to guess at, one line>"
}"""


def one(arm, model, run):
    with tempfile.TemporaryDirectory() as d:
        p = subprocess.run(["claude", "-p", ARMS[arm] + "\n" + QUESTIONS, "--model", model,
                            "--allowedTools", "", "--output-format", "json"],
                           cwd=d, capture_output=True, text=True, timeout=600)
    out = {"arm": arm, "model": model, "run": run}
    try:
        m = re.search(r"\{.*\}", json.loads(p.stdout)["result"], re.S)
        out.update(json.loads(m.group(0)))
    except Exception as e:
        out["error"] = f"{e}: {p.stdout[-400:]} {p.stderr[-400:]}"
    print(json.dumps(out, ensure_ascii=False), flush=True)
    return out


if __name__ == "__main__":
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    jobs = [(a, m, r) for a in ARMS for m in ("sonnet", "opus") for r in range(runs)]
    with ThreadPoolExecutor(6) as ex:
        results = list(ex.map(lambda j: one(*j), jobs))
    json.dump(results, open(__file__.replace("ask.py", "results.json"), "w"), ensure_ascii=False, indent=1)
