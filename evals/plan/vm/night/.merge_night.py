#!/usr/bin/env python3
"""Merge the night's guest reports (report-vm-A/B/C.md, report-vm-DNN-*.md) against the host's
regression run (evals/plan/report-regression-2026-09-26.md, its merged table's `verdict` column).
Prints markdown: counts, the diff groups and the merged table. Notes per case: .night_notes.json."""
import re, glob, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
PLAN = os.path.dirname(os.path.dirname(HERE))
ROW = re.compile(r"\| (\S+) \| \*\*(\w+)\*\* \| (\d+) \| (.*) \| (.*) \|$")
DUP = {"TR21": ("lifecycle", "delivery"), "TR22": ("lifecycle", "delivery")}
BAD = {"BUG", "FAIL", "ERROR"}

def host():
    h, on = {}, False
    for line in open(os.path.join(PLAN, "report-regression-2026-09-26.md"), encoding="utf-8"):
        if line.startswith("| case | phase"):
            on = True; continue
        if not on or not line.startswith("| ") or line.startswith("|---"):
            continue
        c = [x.strip() for x in line.split("|")]
        h[c[1]] = (c[5].strip("*"), c[2], c[8])
    return h

def guest():
    files = [("report-vm-A.md", "A"), ("report-vm-B.md", "B"), ("report-vm-C.md", "C")]
    files += [(os.path.basename(p), "D") for p in sorted(glob.glob(HERE + "/report-vm-D*.md"))]
    files += [(os.path.basename(p), "X") for p in sorted(glob.glob(HERE + "/report-vm-X*.md"))]
    g, order, first = {}, [], {}
    for fn, ph in files:
        p = os.path.join(HERE, fn)
        if not os.path.exists(p):
            continue
        seen = {}
        for line in open(p, encoding="utf-8"):
            m = ROW.match(line.rstrip("\n"))
            if not m:
                continue
            cid, v, s, exp, obs = m.groups()
            seen[cid] = seen.get(cid, 0) + 1
            key = f"{cid} ({DUP[cid][seen[cid] - 1]} module)" if cid in DUP else cid
            rph = ph
            if key not in g:
                order.append(key)
            elif ph == "X":
                first[key] = g[key][0]
                rph = g[key][1] + " → re-run"
            g[key] = (v, rph, int(s), obs, fn)
    return g, order, first

H = host(); G, order, FIRST = guest()
N = json.load(open(os.path.join(HERE, ".night_notes.json"), encoding="utf-8")) \
    if os.path.exists(os.path.join(HERE, ".night_notes.json")) else {}
counts = {}
for k in order:
    counts[G[k][0]] = counts.get(G[k][0], 0) + 1
groups = {"extra": [], "fixed": [], "regressed": [], "still": [], "lab": [], "same_pass": [], "same_skip": [], "other": []}
for k in order:
    gv = G[k][0]; hv = H.get(k, ("?",))[0].split("→")[-1]
    if k in N.get("_lab_only", []):
        groups["lab"].append(k)
    elif hv == "SKIP" and gv != "SKIP":
        groups["extra"].append(k)
    elif hv in BAD and gv == "PASS":
        groups["fixed"].append(k)
    elif hv == "PASS" and gv in BAD:
        groups["regressed"].append(k)
    elif hv in BAD and gv in BAD:
        groups["still"].append(k)
    elif hv == gv == "PASS":
        groups["same_pass"].append(k)
    elif hv == gv == "SKIP":
        groups["same_skip"].append(k)
    elif gv in ("SKIP", "ERROR") or hv in ("SKIP", "ERROR"):
        groups["lab"].append(k)
    else:
        groups["other"].append(k)
notrun = [k for k in H if k not in G]

def item(k):
    hv = H.get(k, ("—",))[0]; note = N.get(k, "")
    return f"- **{k}**: host {hv} → lab **{G[k][0]}**" + (f" — {note}" if note else "")

out = ["**Lab:** " + " · ".join(f"{k} {v}" for k, v in sorted(counts.items())) + f" ({len(order)} case runs). "
       "**Host regression:** " + " · ".join(f"{k} {v}" for k, v in sorted(
           {v: sum(1 for x in H.values() if x[0] == v) for v in {x[0] for x in H.values()}}.items())) +
       f" ({len(H)} case runs).", ""]
titles = [("regressed", "Regressed in the lab — host PASS → BUG/FAIL/ERROR"),
          ("still", "Still failing — bad on the host and in the lab"),
          ("fixed", "Fixed in the lab — host BUG/FAIL/ERROR → PASS"),
          ("extra", "Ran in the lab, SKIP on the host"),
          ("lab", "Lab-only differences — the verdict moved because of the guest, not the app"),
          ("other", "Other changes")]
for key, t in titles:
    out += [f"### {t} ({len(groups[key])})", ""] + ([item(k) for k in groups[key]] or ["none"]) + [""]
out += [f"### PASS on both ({len(groups['same_pass'])})", "", ", ".join(groups["same_pass"]) or "none", "",
        f"### Re-run once in the lab ({len(FIRST)})", ""] + [f"- **{k}**: first {FIRST[k]} → re-run **{G[k][0]}**"
        + (f" — {N[k]}" if N.get(k) else "") for k in FIRST] + ["",
        f"### SKIP on both ({len(groups['same_skip'])})", "", ", ".join(groups["same_skip"]) or "none", "",
        f"### On the host, not run in the lab ({len(notrun)})", "", ", ".join(notrun) or "none", ""]
out += ["## Merged table", "", "| case | phase | host | lab | s | observed in the lab | source |", "|---|---|---|---|---|---|---|"]
for k in order:
    v, ph, s, obs, fn = G[k]
    fv = f"{FIRST[k]} → " if k in FIRST else ""
    out.append(f"| {k} | {ph} | {H.get(k, ('—',))[0]} | {fv}**{v}** | {s} | {obs} | {fn} |")
print("\n".join(out))
