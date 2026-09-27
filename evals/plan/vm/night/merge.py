#!/usr/bin/env python3
"""Merge one night's guest reports against a baseline night (2026-09-27, for the weekly night run).

    merge.py RUN_DIR [BASE_DIR]

RUN_DIR holds report-vm-A/B/C.md, report-vm-DNN-*.md and re-runs report-vm-X*.md (a later X file
overrides the first verdict, which is shown as "first → re-run"); optional RUN_DIR/notes.json maps a
case id to a note, and its "_lab_only" list forces cases into the "moved because of the guest/quota"
group. BASE_DIR is the previous night in the same layout (default: the newest other
evals/plan/vm/night/<date>/, else the 26/27 Sep run at the top of evals/plan/vm/night/).
Prints markdown: counts, the diff groups, the merged table. Generalised from .merge_night.py, which
compared against the host's regression report instead."""
import re, glob, os, json, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROW = re.compile(r"\| (\S+) \| \*\*(\w+)\*\* \| (\d+) \| (.*) \| (.*) \|$")
DUP = {"TR21": ("lifecycle", "delivery"), "TR22": ("lifecycle", "delivery")}
BAD = {"BUG", "FAIL", "ERROR"}


def night(d):
    files = [(f"report-vm-{p}.md", p) for p in "ABC"]
    files += [(os.path.basename(p), "D") for p in sorted(glob.glob(d + "/report-vm-D*.md"))]
    files += [(os.path.basename(p), "X") for p in sorted(glob.glob(d + "/report-vm-X*.md"))]
    g, order, first = {}, [], {}
    for fn, ph in files:
        p = os.path.join(d, fn)
        if not os.path.exists(p):
            continue
        seen = {}
        for line in open(p, encoding="utf-8"):
            m = ROW.match(line.rstrip("\n"))
            if not m:
                continue
            cid, v, s, exp, obs = m.groups()
            seen[cid] = seen.get(cid, 0) + 1
            key = f"{cid} ({DUP[cid][min(seen[cid], 2) - 1]} module)" if cid in DUP else cid
            rph = ph
            if key not in g:
                order.append(key)
            elif ph == "X":
                first[key] = g[key][0]
                rph = g[key][1] + " → re-run"
            g[key] = (v, rph, int(s), obs, fn)
    return g, order, first


def default_base(run):
    dated = sorted(p for p in glob.glob(HERE + "/20??-??-??") if os.path.abspath(p) != os.path.abspath(run))
    older = [p for p in dated if os.path.basename(p) < os.path.basename(os.path.abspath(run))]
    return older[-1] if older else HERE


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    run = os.path.abspath(sys.argv[1])
    base = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else default_base(run)
    G, order, FIRST = night(run)
    B, _, BFIRST = night(base)
    npath = os.path.join(run, "notes.json")
    N = json.load(open(npath, encoding="utf-8")) if os.path.exists(npath) else {}
    count = lambda T, keys: " · ".join(f"{k} {v}" for k, v in sorted(
        {x: sum(1 for k in keys if T[k][0] == x) for x in {T[k][0] for k in keys}}.items()))
    groups = {k: [] for k in ("regressed", "still", "fixed", "extra", "lab", "other", "same_pass", "same_skip", "new")}
    for k in order:
        gv = G[k][0]
        bv = B[k][0] if k in B else None
        if k in N.get("_lab_only", []):
            groups["lab"].append(k)
        elif bv is None:
            groups["new"].append(k)
        elif bv == "SKIP" and gv != "SKIP":
            groups["extra"].append(k)
        elif bv in BAD and gv == "PASS":
            groups["fixed"].append(k)
        elif bv == "PASS" and gv in BAD:
            groups["regressed"].append(k)
        elif bv in BAD and gv in BAD:
            groups["still"].append(k)
        elif bv == gv == "PASS":
            groups["same_pass"].append(k)
        elif bv == gv == "SKIP":
            groups["same_skip"].append(k)
        else:
            groups["other"].append(k)
    notrun = [k for k in B if k not in G]

    def item(k):
        note = N.get(k, "")
        return f"- **{k}**: before {B[k][0] if k in B else '—'} → now **{G[k][0]}**" + (f" — {note}" if note else "")

    rel = lambda p: os.path.relpath(p, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE)))))
    out = [f"Run `{rel(run)}` against `{rel(base)}`.", "",
           f"**Now:** {count(G, order)} ({len(order)} case runs). **Before:** {count(B, list(B))} ({len(B)} case runs).", ""]
    for key, t in [("regressed", "Regressed — before PASS → now BUG/FAIL/ERROR"),
                   ("still", "Still failing — bad before and now"),
                   ("fixed", "Fixed — before BUG/FAIL/ERROR → now PASS"),
                   ("extra", "Ran now, SKIP before"),
                   ("lab", "Moved for a cause outside the app (quota, credit cap, guest speed) — notes.json _lab_only"),
                   ("new", "New cases (not in the baseline)"),
                   ("other", "Other changes")]:
        out += [f"### {t} ({len(groups[key])})", ""] + ([item(k) for k in groups[key]] or ["none"]) + [""]
    out += [f"### PASS on both ({len(groups['same_pass'])})", "", ", ".join(groups["same_pass"]) or "none", "",
            f"### Re-run once tonight ({len(FIRST)})", ""]
    out += [f"- **{k}**: first {FIRST[k]} → re-run **{G[k][0]}**" + (f" — {N[k]}" if N.get(k) else "") for k in FIRST] or ["none"]
    out += ["", f"### SKIP on both ({len(groups['same_skip'])})", "", ", ".join(groups["same_skip"]) or "none", "",
            f"### In the baseline, not run tonight ({len(notrun)})", "", ", ".join(notrun) or "none", "",
            "## Merged table", "", "| case | phase | before | now | s | observed now | source |", "|---|---|---|---|---|---|---|"]
    for k in order:
        v, ph, s, obs, fn = G[k]
        fv = f"{FIRST[k]} → " if k in FIRST else ""
        out.append(f"| {k} | {ph} | {B[k][0] if k in B else '—'} | {fv}**{v}** | {s} | {obs} | {fn} |")
    print("\n".join(out))


if __name__ == "__main__":
    main()
