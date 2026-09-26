#!/usr/bin/env python3
"""Merge the regression run's per-batch reports (report-R-*.md) into report-regression-2026-09-26.md,
with the diff against the morning run (report-2026-09-26.md)."""
import re, glob, os, datetime, json
HERE = os.path.dirname(os.path.abspath(__file__))
ROW = re.compile(r"\| (\S+) \| \*\*(\w+)\*\* \| (\d+) \| (.*)$")

def morning():
    m, seen = {}, {}
    for line in open(os.path.join(HERE, "report-2026-09-26.md"), encoding="utf-8"):
        c = [x.strip() for x in line.split("|")]
        if len(c) < 9 or c[1] in ("case", "") or c[1].startswith("---"):
            continue
        cid, phase, v = c[1], c[2], c[4].strip("*")
        if cid in ("TR21", "TR22"):                 # two modules, lifecycle row first
            seen[cid] = seen.get(cid, 0) + 1
            key = cid if seen[cid] == 1 else cid + "'"
        else:
            key = cid
        if key in m and "re-run" in phase:          # B3 flaky: FAIL then PASS
            m[key] = (m[key][0] + "→" + v, phase)
        else:
            m[key] = (v, phase)
    return m

ORDER = [("report-R-A.md", "A"), ("report-R-A2.md", "A (re-run after case fix)"),
         ("report-R-B1.md", "B"), ("report-R-B2.md", "B"),
         ("report-R-C1.md", "C"), ("report-R-C2.md", "C")]
ORDER += [(os.path.basename(p), "D") for p in sorted(glob.glob(HERE + "/report-R-D*.md"))]
ORDER += [(os.path.basename(p), "D (re-run 21:44, build 2e2d8d5)") for p in sorted(glob.glob(HERE + "/report-R-X*.md"))]
rows, order, first = {}, [], {}
for fn, phase in ORDER:
    p = os.path.join(HERE, fn)
    if not os.path.exists(p):
        continue
    txt = open(p, encoding="utf-8").read()
    t = datetime.datetime.strptime(re.search(r"# Test plan run — (\d{4}-\d\d-\d\d \d\d:\d\d)", txt).group(1), "%Y-%m-%d %H:%M")
    inthis = {}
    for line in txt.splitlines():
        mm = ROW.match(line)
        if not mm:
            continue
        cid, v, s, rest = mm.groups()
        inthis[cid] = inthis.get(cid, 0) + 1
        key = cid + ("'" if inthis[cid] == 2 else "")
        if key in rows:
            first.setdefault(key, rows[key][4])
        if key not in rows:
            order.append(key)
        # a re-run inside a phase label that is not "A"/"C"/... keeps its own label
        ph = phase
        if key in rows and phase in ("C", "B", "D"):
            ph = phase + " (re-run after case fix)"
        rows[key] = (fn, ph, t.strftime("%H:%M"), cid, v, s, rest.rstrip().rstrip("|").rstrip())
        t += datetime.timedelta(seconds=int(s))

M = morning()
NOTES = json.load(open(os.path.join(HERE, ".regression_notes.json"), encoding="utf-8")) \
    if os.path.exists(os.path.join(HERE, ".regression_notes.json")) else {}
BAD = {"BUG", "FAIL", "ERROR"}
groups = {"b_case": [], "a": [], "b": [], "c": [], "d": [], "same_pass": [], "same_skip": [], "new": [], "other": []}
for k in order:
    now = rows[k][4]
    mv = M.get(k, (None, ""))[0]
    mfinal = mv.split("→")[-1] if mv else None
    if mv is None:
        groups["new"].append(k)
    elif mfinal == "PASS" and now == "PASS" and first.get(k) in BAD:
        groups["b_case"].append(k)
    elif mfinal in BAD and now == "PASS":
        groups["a"].append(k)
    elif mfinal in ("PASS", "SKIP") and now in BAD and not (mfinal == "SKIP" and now == "ERROR"):
        groups["b"].append(k)
    elif mfinal in BAD and now in BAD:
        groups["c"].append(k)
    elif now in ("SKIP", "ERROR") and mfinal != now:
        groups["d"].append(k)
    elif mfinal == "PASS" and now == "PASS":
        groups["same_pass"].append(k)
    elif mfinal == now == "SKIP":
        groups["same_skip"].append(k)
    else:
        groups["other"].append(k)
not_run_now = [k for k in M if k not in rows]

def name(k):
    return k.replace("'", " (delivery module)") if k.endswith("'") else (k + " (lifecycle module)" if k in ("TR21", "TR22") else k)
def line(k):
    fn, ph, hm, cid, v, s, rest = rows[k]
    extra = f" (first run {first[k]}, re-run)" if k in first else ""
    note = NOTES.get(k, "")
    return f"- **{name(k)}**: {M.get(k, ('—',))[0]} → **{v}**{extra}" + (f" — {note}" if note else "")

counts = {}
for k in order:
    counts[rows[k][4]] = counts.get(rows[k][4], 0) + 1
out = ["# Regression run — 2026-09-26 evening (after fix batches 1–5)", "",
       NOTES.get("_interim", ""), "", NOTES.get("_intro", ""), "",
       "**Now:** " + " · ".join(f"{k} {v}" for k, v in sorted(counts.items())) + f" ({len(order)} case runs). "
       "**Morning:** BUG 55 · FAIL 13 · PASS 49 · SKIP 17 (134 case runs).", "",
       "## Diff against the morning run", "",
       f"(a) fixed {len(groups['a'])} · (b) regressed {len(groups['b'])} (+ {len(groups['b_case'])} that failed first on a stale case and PASS after the case fix) · (c) still failing {len(groups['c'])} · "
       f"(d) new SKIP/ERROR {len(groups['d'])} · PASS both times {len(groups['same_pass'])} · SKIP both times "
       f"{len(groups['same_skip'])} · not run tonight {len(not_run_now)}" +
       (f" · other {len(groups['other'])}" if groups['other'] else "") +
       (f" · new cases {len(groups['new'])}" if groups['new'] else ""), ""]
for g, title in (("b", "(b) Regressed — PASS → BUG/FAIL/ERROR"),
                 ("b_case", "(b′) Failed on the first run because the case was stale — PASS after the case fix"), ("c", "(c) Still failing"),
                 ("d", "(d) New SKIP / ERROR"), ("other", "Other changes"), ("new", "New cases"),
                 ("a", "(a) Fixed — BUG/FAIL → PASS")):
    out += [f"### {title} ({len(groups[g])})", ""]
    out += [line(k) for k in groups[g]] or ["none"]
    out += [""]
out += ["### PASS both times (%d)" % len(groups["same_pass"]), "", ", ".join(name(k) for k in groups["same_pass"]), "",
        "### SKIP both times (%d)" % len(groups["same_skip"]), "", ", ".join(name(k) for k in groups["same_skip"]), "",
        "### In the morning run, not run tonight (%d)" % len(not_run_now), "",
        (", ".join(f"{name(k)} ({M[k][0]})" for k in not_run_now) or "none") + (" — " + NOTES["_not_run"] if NOTES.get("_not_run") else ""), ""]
for sec in ("_care", "_fixes"):
    if NOTES.get(sec):
        out += NOTES[sec] + [""]
out += ["## Merged table", "",
        "Phase A = routes only, B = gestures (hands-off), C = real audio through 🧪 WT Inject (hands-off), D = spawn/relaunch/slow, "
        "one at a time after 60 s idle. Time = batch start + the preceding cases' durations (local, ≈). A case re-run after a "
        "case fix shows the re-run.", "",
        "| case | phase | time | morning | verdict | s | expectation | observed | source |", "|---|---|---|---|---|---|---|---|---|"]
for k in order:
    fn, ph, hm, cid, v, s, rest = rows[k]
    out.append(f"| {name(k)} | {ph} | {hm} | {M.get(k, ('—',))[0]} | **{v}** | {s} | {rest} | {fn} |")
open(os.path.join(HERE, "report-regression-2026-09-26.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print(counts, len(order), {g: len(v) for g, v in groups.items()}, "not run:", not_run_now)
print({g: v for g, v in groups.items() if g not in ("same_pass",)})
