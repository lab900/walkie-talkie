"""§7.4 LC — the subtitle band, driven only through `POST /test/live-caption` and read from
`state.liveCaption` (docs/test-plan.md). No microphone, no network: the band's own motion.

**Two lines that roll up since 2026-09-28** (Victor: *"Not very happy with how they look, scrolling
text to the left … when a full line is filled up, a second line should be written below the first
one … at the maximum of eighty percent of the screen width … when the second line gets full as
well, it pushes up the first line … on silence … the whole line is pushed up after sufficient time
to read it … a new sentence starting on the second line … even if under a correction the sentence
is merged with the previous one, it still remains on the second line"*). No horizontal scroll, no
eraser. Constants (LiveCaptionBand.swift): maxLineShare 0.8, readTime = max(readMin 3.0 s,
readPerWord 0.3 s × words on the line) of silence (restarted when a line has rolled out; a gentle
correction does not restart it), lineGlide τ 0.2 s with `landed` at 0.03 slot, font 30.4 pt
semibold, backdrop 10 pt around the lines' text boxes, dodge to the bottom (one frame, 12 pt / 0.25 s
hysteresis back up), vMax 700, ease 0.45, swap 1.0 (ghost 0.5), correctionFade 1.6, reflow 0.26,
provisionalFloor 0.4, fadeIn 0.22, entry front revealSpeed 320 pt/s with a 160 pt soft edge
(letter by letter since 2026-09-27, 84d420e).

`state.liveCaption.lines[i]`: `id` (sticky), `slot` (0 top, drawn), `slotTarget`, `landed`, `first`
(absolute index), `words`, `text`, `anchor`, `velocity`, `width` (target), `visibleWidth`, `centre`,
`readTime`, `reason` (`first`｜`full`｜`sentence`). `lineOf` is each visible word's line index;
`leaving` the lines rolling out; `lifts` counts roll-ups; `backdrop`/`lineBoxes`/`frame`/`screen` are
screen points; `position` `top`｜`bottom`. Each line is centred (an assumption kept from 2026-09-26
07:50: *"the visible text remains ~centered"*), so a growing line still moves left by half of each
word's ink — the only horizontal motion there is. Tolerances beyond the plan's numbers are written
next to each assertion and every note carries what was measured."""
import time
from harness import *

V_MAX = 700.0
READ_MIN, READ_PER_WORD = 3.0, 0.3   # s: LiveCaptionBand.readMin / readPerWord (also in the state)
PAD, EDGE_GAP = 10.0, 2.0            # pt: backdropPad, edgeGap
DEBOUNCE = 0.25                      # s: dodgeDebounce
JITTER = 0.03          # s: an HTTP read of /test/state is not the app's frame clock
WORDS = ("the quick brown fox jumps over a lazy dog while seven bright wizards quietly juggle heavy "
         "boxes of frozen pizza near an old harbour and nobody seems to notice anything unusual "
         "because everyone is busy watching small boats drift past the long grey pier at sunset "
         "under soft orange clouds that slowly fade into night").split()


# ---------------------------------------------------------------- helpers
def read_time(n):
    return max(READ_MIN, READ_PER_WORD * n)

def mid(s):
    return s["bandWidth"] / 2

def centre_offs(s):
    """|centre − bandWidth/2| per line that has something visible."""
    return [abs(l["centre"] - mid(s)) for l in s["lines"] if l["visibleWidth"] > 1]

def fresh():
    """Band closed and faded (the 0.35 s fade's completion resets the ticker)."""
    caption_off()
    wait_for(lambda: not lc()["open"], 1.0, 0.05)
    time.sleep(0.45)

def show(text, partial="", gentle=False, words=None, timeout=1.0):
    """Push a caption and wait until the band reports it (the route hops to main)."""
    caption(text, partial, gentle)
    n = words if words is not None else len((text + " " + partial).split())
    return wait_for(lambda: (lambda s: s if s["words"] == n else None)(lc()), timeout, 0.02)

def pointer(p):
    post("/test/live-caption", {"pointer": p})

def drive(events, seconds, hz=20):
    """Fire `events` [(at, fn)] when due while sampling `lc()` at `hz`; returns (samples, fired_at)."""
    out, fired, t0, i = [], [], time.time(), 0
    while True:
        now = time.time() - t0
        while i < len(events) and events[i][0] <= now:
            events[i][1](); fired.append(round(time.time() - t0, 3)); i += 1
        if now >= seconds and i >= len(events):
            break
        s = lc(); s["t"] = round(time.time() - t0, 3); out.append(s)
        time.sleep(1.0 / hz)
    return out, fired

def sample_until(cond, timeout, hz=20):
    out, t0 = [], time.time()
    while time.time() - t0 < timeout:
        s = lc(); s["t"] = round(time.time() - t0, 3); out.append(s)
        if cond(s):
            break
        time.sleep(1.0 / hz)
    return out

def motion_faults(S, slack=2.0):
    """Per line id: anchor steps faster than vMax (a jump) and anchor rises (the text moving right —
    a growing centred line only ever moves left)."""
    fast, up = [], []
    for a, b in zip(S, S[1:]):
        la = {l["id"]: l for l in a["lines"]}
        dt = b["t"] - a["t"]
        for l in b["lines"]:
            p = la.get(l["id"])
            if not p:
                continue
            d = l["anchor"] - p["anchor"]
            if abs(d) > V_MAX * (dt + JITTER) + slack:
                fast.append((b["t"], l["id"], round(d, 1), round(dt, 3)))
            if d > slack:
                up.append((b["t"], l["id"], round(d, 1)))
    return fast, up

def verdict(fails, note):
    return ("PASS", note) if not fails else ("FAIL", "; ".join(fails) + " — " + note)

def lift_times(S):
    """(t, lifts) at each sample where `lifts` grew."""
    return [(b["t"], b["lifts"]) for a, b in zip(S, S[1:]) if b["lifts"] > a["lifts"]]


# ---------------------------------------------------------------- cases
@case("LC1", ("lc",), expect="first word enters letter by letter on the top line, centred (2026-09-28 two-line model): reveal "
      "grows monotonically and the word is fully revealed (reveal null) within 1.2 s; one line, slot 0, reason first; "
      "|line centre − bandWidth/2| < 3 on every sample; line |velocity| and the entry front ≤ 320 pt/s; first opacity < 0.1, "
      "settled 0.4 ± 0.03 (provisional)")
def lc1():
    """The first word appears in the middle of the top slot and is swept in by the entry front.

    A 110 pt word takes (110 + 160) / 320 ≈ 0.84 s. Since 2026-09-28 the band holds lines; the first
    one is at slot 0 and centred on the band."""
    fresh()
    caption("", "Hello")
    t_add = time.time()
    S = []
    while time.time() - t_add < 1.8:
        t_req = time.time(); s = lc(); s["t"] = (t_req + time.time()) / 2 - t_add
        S.append(s); time.sleep(0.03)
    S = [s for s in S if s["words"] >= 1]
    if not S:
        return "FAIL", "the band never showed the word"
    if "lines" not in S[0]:
        return "FAIL", "no `lines` in state.liveCaption — the build predates the two-line band"
    s0, bw = S[0], S[0]["bandWidth"]
    rv = [(s["t"], s["reveal"][0]) for s in S if s.get("reveal")]
    series = [(t, r) for t, r in rv if r is not None]
    done = next((t for t, r in rv if r is None), None)
    back = [(round(a[0], 2), a[1], b[1]) for a, b in zip(series, series[1:]) if b[1] < a[1] - 1]
    fast = [(round(b[0], 2), round((b[1] - a[1]) / (b[0] - a[0]))) for a, b in zip(series, series[1:])
            if b[0] > a[0] and b[1] - a[1] > 320 * (b[0] - a[0] + JITTER) + 2]
    offs = [abs(s["lines"][0]["centre"] - mid(s)) for s in S if s["lines"]]
    vmax = max(abs(s["velocity"]) for s in S)
    op0, last = s0["opacity"][0], S[-1]["opacity"][0]
    shape = [(round(s["t"], 2), len(s["lines"]), s["lines"][0]["slot"] if s["lines"] else None) for s in S
             if len(s["lines"]) != 1 or abs(s["lines"][0]["slot"]) > 0.001]
    fails = []
    if back: fails.append(f"reveal went back {back[:2]}")
    if done is None: fails.append(f"not fully revealed after 1.8 s (reveal {rv[-1][1] if rv else None})")
    elif done > 1.2: fails.append(f"fully revealed only at +{done:.2f} s")
    if offs and max(offs) >= 3: fails.append(f"off centre by {max(offs):.1f}")
    if vmax > 320: fails.append(f"line velocity {vmax:.0f} pt/s")
    if fast: fails.append(f"entry front faster than 320 pt/s: {fast[:2]}")
    if op0 >= 0.1: fails.append(f"first opacity {op0}")
    if abs(last - 0.4) > 0.03: fails.append(f"settled opacity {last}")
    if shape: fails.append(f"not one line at slot 0: {shape[:2]}")
    if S[-1]["lines"] and S[-1]["lines"][0]["reason"] != "first": fails.append(f"reason {S[-1]['lines'][0]['reason']}")
    return verdict(fails, f"reveal {series[0][1] if series else None} pt at +{rv[0][0] if rv else float('nan'):.2f} s → in at "
                          f"+{done and round(done, 2)} s; centre off ≤ {max(offs) if offs else 0:.2f} pt; max |velocity| {vmax:.0f}; "
                          f"opacity {op0} → {last}; bandWidth {bw:.0f}, band {s0['bandHeight']:.0f} pt tall, font {s0['fontSize']} {s0['fontWeight']}")


@case("LC2", ("lc",), expect="growth at 0.4 s/word ×50: never more than 2 lines; every line ≤ maxLineWidth (0.8 bandWidth) and centred "
      "±10 pt; no line anchor rises (no text moves right) and no step > 700·Δt; ≥ 1 roll-up, after which the old line 2 is the "
      "top line")
def lc2():
    """Growth: words flow onto two centred lines of at most 80 % of the band; the third rolls the first out.
    No horizontal scroll: a line moves only left, by half of each word's ink, while it grows."""
    fresh()
    n = 50
    ev = [(0.4 * k, (lambda k=k: caption(" ".join((WORDS * 2)[:k + 1])))) for k in range(n)]
    S, _ = drive(ev, 0.4 * n + 0.5)
    S = [s for s in S if s["words"] > 0]
    too_many = [s["t"] for s in S if len(s["lines"]) > 2]
    wide = [(s["t"], round(l["width"]), round(s["maxLineWidth"])) for s in S for l in s["lines"] if l["width"] > s["maxLineWidth"] + 0.5]
    offs = [o for s in S for o in centre_offs(s)]
    fast, up = motion_faults(S)
    lifts = lift_times(S)
    moved_up = []
    for a, b in zip(S, S[1:]):
        if b["lifts"] > a["lifts"] and len(a["lines"]) == 2 and b["lines"]:
            moved_up.append(b["lines"][0]["id"] == a["lines"][1]["id"])
    fails = []
    if too_many: fails.append(f"{len(too_many)} sample(s) with more than 2 lines, first at {too_many[0]}")
    if wide: fails.append(f"{len(wide)} line sample(s) past 80 %, first {wide[0]}")
    if offs and max(offs) > 10: fails.append(f"a line off centre by {max(offs):.1f} pt")
    if fast: fails.append(f"{len(fast)} anchor step(s) over vMax, first {fast[0]}")
    if up: fails.append(f"{len(up)} anchor rise(s) (text moving right), first {up[0]}")
    if not lifts: fails.append("no roll-up in 50 words")
    if moved_up and not all(moved_up): fails.append(f"after a roll-up the top line was not the old line 2: {moved_up}")
    return verdict(fails, f"{len(S)} samples, {S[-1]['lifts']} roll-up(s) at {[t for t, _ in lifts]}, max centre offset "
                          f"{max(offs) if offs else 0:.1f} pt, max velocity {max(s['velocity'] for s in S):.0f}, maxLineWidth "
                          f"{S[-1]['maxLineWidth']:.0f} of {S[-1]['bandWidth']:.0f}")


@case("LC3", ("lc",), expect="pause after 8 words: velocity ≤ 10 pt/s from +1.5 s, centre unchanged; the line rolls out at "
      "readTime = max(3.0, 0.3 × 8) = 3.0 s after the last word (−0.1/+0.3), the band stays open")
def lc3():
    """A pause: the line comes to rest, then rolls up and out after its read time (no eraser since 2026-09-28)."""
    fresh()
    ev = [(0.4 * k, (lambda k=k: caption(" ".join(WORDS[:k + 1])))) for k in range(8)]
    S, fired = drive(ev, 0.4 * 7 + read_time(8) + 1.0)
    t_last = fired[-1]
    lifts = lift_times(S)
    t_up = lifts[0][0] if lifts else None
    rest = [s for s in S if s["t"] >= t_last + 1.5 and (t_up is None or s["t"] < t_up) and s["lines"]]
    fails = []
    if t_up is None:
        fails.append("the line never rolled out")
    elif not read_time(8) - 0.1 <= t_up - t_last <= read_time(8) + 0.3:
        fails.append(f"rolled out {t_up - t_last:.2f} s after the last word (read time {read_time(8)})")
    v = max((s["velocity"] for s in rest), default=0)
    cs = [s["lines"][0]["centre"] for s in rest]
    drift = (max(cs) - min(cs)) if cs else 0
    if v > 10: fails.append(f"velocity {v:.1f} pt/s after +1.5 s")
    if drift > 4: fails.append(f"centre drifted {drift:.1f} pt before the roll-up")
    if not rest: fails.append("no samples between +1.5 s and the roll-up")
    if not S[-1]["open"]: fails.append("band closed after the roll-up")
    return verdict(fails, f"rolled out at +{(t_up - t_last) if t_up else float('nan'):.2f} s (read time {read_time(8)} s), max velocity "
                          f"{v:.1f} pt/s and centre drift {drift:.2f} pt before it; after: lines {len(S[-1]['lines'])}, open {S[-1]['open']}")


@case("LC4", ("lc",), expect="burst of 15 words: every line's anchor eases, no step > 700·Δt, every sample velocity ≤ 700")
def lc4():
    """A burst: taken up elastically, never faster than vMax."""
    fresh()
    show("one two three")
    time.sleep(1.0)
    S, _ = drive([(0.0, lambda: caption("one two three " + " ".join(WORDS[:15])))], 3.0)
    vmax = max(s["velocity"] for s in S)
    fast, _ = motion_faults(S)
    fails = []
    if vmax > V_MAX + 1: fails.append(f"velocity {vmax:.0f}")
    if fast: fails.append(f"{len(fast)} step(s) over vMax, first {fast[0]}")
    return verdict(fails, f"max velocity {vmax:.0f} pt/s, {len(S)} samples, lines {len(S[-1]['lines'])}, lifts {S[-1]['lifts']}")


@case("LC5", ("lc",), expect="\"fix the build today\" → \"fix it today\": corrections +1, ghosts [the, build] within 0.3 s, [] after 0.6 s, correcting [] after 2.7 s, reflowing > 0 then < 0.5 within 1.6 s, the line's centre glides")
def lc5():
    """A correction that shortens the line: ghosts, swap, reflow inside its line, a glide."""
    fresh()
    show("fix the build today")
    time.sleep(1.2)
    c0 = lc()["corrections"]
    S, fired = drive([(0.0, lambda: caption("fix it today"))], 3.2)
    upd = [s for s in S if s["words"] == 3 and s["lines"]]
    if not upd:
        return "FAIL", "the correction never reached the band"
    tu = upd[0]["t"]
    early = [s["ghosts"] for s in S if tu <= s["t"] <= tu + 0.3]
    late_g = [s["ghosts"] for s in S if s["t"] >= tu + 0.6 and s["ghosts"]]
    late_c = [s["correcting"] for s in S if s["t"] >= tu + 2.7 and s["correcting"]]
    rf0 = max((s["reflowing"] for s in S if tu <= s["t"] <= tu + 0.3), default=0)
    rf16 = [s["reflowing"] for s in S if s["t"] >= tu + 1.6]
    c = lambda s: s["lines"][0]["centre"]
    jumps = [(b["t"], round(c(b) - c(a), 1)) for a, b in zip(upd, upd[1:])
             if abs(c(b) - c(a)) > V_MAX * (b["t"] - a["t"] + JITTER) + 5]
    dc = S[-1]["corrections"] - c0
    fails = []
    if dc != 1: fails.append(f"corrections +{dc}")
    if ["the", "build"] not in early: fails.append(f"ghosts within 0.3 s {early[:3]}")
    if late_g: fails.append(f"ghosts still {late_g[0]} after 0.6 s")
    if late_c: fails.append(f"correcting still {late_c[0]} after 2.7 s")
    if rf0 <= 0: fails.append("no reflow")
    if not rf16 or rf16[0] >= 0.5: fails.append(f"reflowing {rf16[:1]} at +1.6 s")
    if jumps: fails.append(f"centre stepped {jumps[:2]}")
    return verdict(fails, f"corrections +{dc}, ghosts {early[:1]}, reflowing {rf0:.1f} → {rf16[:1]} at +1.6 s, update seen {tu - fired[0]:.2f} s after the POST")


@case("LC6", ("lc",), expect="\"500\" → \"five hundred\": corrections +2, ghosts [\"500\"]")
def lc6():
    """A correction that lengthens the line."""
    fresh()
    show("I owe you 500 dollars")
    time.sleep(1.2)
    c0 = lc()["corrections"]
    S, _ = drive([(0.0, lambda: caption("I owe you five hundred dollars"))], 1.0)
    upd = [s for s in S if s["words"] == 6]
    if not upd:
        return "FAIL", "the correction never reached the band"
    early = [s["ghosts"] for s in upd if s["t"] <= upd[0]["t"] + 0.3]
    dc = S[-1]["corrections"] - c0
    fails = []
    if dc != 2: fails.append(f"corrections +{dc}")
    if ["500"] not in early: fails.append(f"ghosts {early[:3]}")
    return verdict(fails, f"corrections +{dc}, ghosts {early[:1]}")


@case("LC7", ("lc",), expect="revision past the rolled-out words: dropped 0, words 3, one line at slot 0 centred at once (velocity 0 on the first sample), ghosts []")
def lc7():
    """A revision that reaches back past what already rolled out: the lines on the band roll out too and
    the new words are a fresh top line."""
    fresh()
    long = " ".join((WORDS * 2)[:45])
    show(long)
    if not wait_for(lambda: lc()["dropped"] >= 3, 4.0, 0.05):
        return "SKIP", f"the 45-word burst never rolled a line out (dropped {lc()['dropped']})"
    d0 = lc()["dropped"]
    caption("brand new line")
    S = sample(0.8)
    upd = [s for s in S if s["words"] == 3]
    if not upd:
        return "FAIL", "the revision never reached the band"
    s0 = upd[0]
    fails = []
    if s0["dropped"] != 0: fails.append(f"dropped {s0['dropped']}")
    if len(s0["lines"]) != 1 or s0["lines"][0]["slot"] != 0: fails.append(f"lines {[(l['id'], l['slot']) for l in s0['lines']]}")
    off = (s0["lines"][0]["centre"] - mid(s0)) if s0["lines"] else float("nan")
    if s0["velocity"] > 0.5: fails.append(f"velocity {s0['velocity']:.0f} on the first sample")
    if not abs(off) < 3: fails.append(f"centre off by {off:.0f} pt on the first sample")
    if s0["ghosts"]: fails.append(f"ghosts {s0['ghosts']}")
    return verdict(fails, f"dropped before {d0}; first sample: dropped {s0['dropped']}, lines {len(s0['lines'])}, leaving "
                          f"{len(s0['leaving'])}, velocity {s0['velocity']:.0f}, centre off {off:.0f}, corrections {s0['corrections']}")


@case("LC7b", ("lc",), expect="change only inside the rolled-out words: corrections unchanged, dropped unchanged, no anchor jump")
def lc7b():
    """A revision confined to words already gone: nothing visible happens."""
    fresh()
    words = (WORDS * 2)[:45]
    show(" ".join(words))
    if not wait_for(lambda: lc()["dropped"] >= 2, 4.0, 0.05):
        return "SKIP", "the 45-word burst never rolled a line out"
    time.sleep(0.5)
    c0 = lc()["corrections"]
    changed = ["THOSE"] + words[1:]
    S, _ = drive([(0.3, lambda: caption(" ".join(changed)))], 1.3)
    fast, up = motion_faults(S)
    dc = S[-1]["corrections"] - c0
    fails = []
    if dc: fails.append(f"corrections +{dc}")
    if S[-1]["dropped"] != S[0]["dropped"]: fails.append(f"dropped {S[0]['dropped']} → {S[-1]['dropped']}")
    if fast or up: fails.append(f"anchor jumped {(fast + up)[:2]}")
    return verdict(fails, f"dropped {S[0]['dropped']} → {S[-1]['dropped']}, corrections +{dc}, lines {[l['text'][:20] for l in S[-1]['lines']]}")


@case("LC8", ("lc",), expect="tail punctuation flicker and mid-line case/punctuation commits: corrections unchanged, ghosts []")
def lc8():
    """Punctuation and capitals are not corrections (LCS on case-folded stems)."""
    fresh()
    show("hello world how are you")
    time.sleep(0.8)
    c0 = lc()["corrections"]
    seq = [("hello world how are you.", ""), ("hello world how are you", ""), ("hello world how are you?", ""),
           ("hello world. How are you?", ""), ("Hello, world.", "How are you?"), ("Hello, world. How are you?", "")]
    ev = [(0.3 * i, (lambda t=t, p=p: caption(t, p))) for i, (t, p) in enumerate(seq)]
    S, _ = drive(ev, 0.3 * len(seq) + 0.8)
    ghosts = [s["ghosts"] for s in S if s["ghosts"]]
    dc = S[-1]["corrections"] - c0
    fails = []
    if dc: fails.append(f"corrections +{dc}")
    if ghosts: fails.append(f"ghosts {ghosts[0]}")
    return verdict(fails, f"{len(seq)} revisions, corrections +{dc}, {len(ghosts)} sample(s) with ghosts")


@case("LC9", ("lc",), expect="append-only ×30 at 2 words/s (letter by letter since 84d420e): corrections 0; per word, reveal "
      "grows monotonically, the word starts at opacity < 0.1 and is fully revealed within 2.0 s of its append; every line "
      "centred ±10 pt; line |velocity| ≤ 320 pt/s; entry front ≤ 0.7 vMax (490, the catch-up cap)")
def lc9():
    """Appending is never a correction; each new word is swept in letter by letter, onto a centred line.

    The entry front runs at 320 pt/s, or faster only to clear a backlog within 0.8 s (never past
    0.7 vMax = 490); a word appended while the one before is still coming in starts one word-width
    behind that word's front, so its reveal may start negative. 2 words/s is his own pace. Since
    2026-09-28 the 30 words fill two lines (no roll-up): the wrap is at 80 % of the band, and each
    line is centred on its own."""
    fresh()
    t_add, first_op, seen, done = {}, {}, {}, {}
    S = []

    def read():
        t_req = time.time(); s = lc(); s["at"] = (t_req + time.time()) / 2
        S.append(s)
        for i in t_add:
            vis = i - s["dropped"]
            if s["words"] <= i or not 0 <= vis < len(s.get("reveal") or []):
                continue
            if i not in first_op and vis < len(s["opacity"]):
                first_op[i] = s["opacity"][vis]
            r = s["reveal"][vis]
            if r is None:
                if i in seen and i not in done:
                    done[i] = s["at"] - t_add[i]
            elif i not in done:
                seen.setdefault(i, []).append((s["at"], r))

    for k in range(30):
        caption(" ".join(WORDS[:k + 1]))
        t_add[k] = time.time()
        end = t_add[k] + 0.5
        while time.time() < end:
            read(); time.sleep(0.03)
    t_tail = time.time()
    while time.time() - t_tail < 1.6:
        read(); time.sleep(0.03)
    corr = S[-1]["corrections"]
    back = {i: v for i, v in ((i, [(round(a[0] - t_add[i], 2), a[1], b[1]) for a, b in zip(ser, ser[1:]) if b[1] < a[1] - 1])
                              for i, ser in seen.items()) if v}
    steps = [(b[1] - a[1]) / (b[0] - a[0]) for ser in seen.values() for a, b in zip(ser, ser[1:]) if b[0] > a[0]]
    fast = [round(v) for v in steps if v > 490 * 1.1 + 2 / 0.03]
    over320 = sum(1 for v in steps if v > 320 * 1.15)
    ups = sorted(v for v in steps if v > 0)
    front_v = ups[len(ups) // 2] if ups else None
    hot = {i: v for i, v in first_op.items() if v >= 0.1}
    # 2.0 s (2026-09-28, coordinator): a word appended while the one before is still coming in
    # starts one word-width behind that word's front — ≈ (prev width + width + 160) / 320.
    slow = {i: round(v, 2) for i, v in done.items() if v > 2.0}
    missing = [i for i in t_add if i not in done]
    offs = [o for s in S for o in centre_offs(s)]
    vmax = max(abs(s["velocity"]) for s in S)
    fails = []
    if corr: fails.append(f"corrections {corr}")
    if back: fails.append(f"{len(back)} word(s) whose reveal went back, e.g. {list(back.items())[:2]}")
    if hot: fails.append(f"{len(hot)} word(s) started at opacity ≥ 0.1, e.g. {list(hot.items())[:3]}")
    if slow: fails.append(f"{len(slow)} word(s) slower than 2.0 s to be fully revealed: {list(slow.items())[:3]}")
    if missing: fails.append(f"{len(missing)} word(s) never fully revealed: {missing[:5]}")
    if offs and max(offs) > 10: fails.append(f"a line off centre by {max(offs):.1f} pt")
    if vmax > 320: fails.append(f"line velocity {vmax:.0f} pt/s")
    if fast: fails.append(f"entry front over 0.7 vMax: {fast[:3]}")
    worst = max(done.values()) if done else float("nan")
    return verdict(fails, f"corrections {corr}; slowest full reveal {worst:.2f} s over {len(done)}/{len(t_add)} words; "
                          f"first opacity max {max(first_op.values()) if first_op else 'n/a'}; front median "
                          f"{front_v and round(front_v)} pt/s, {over320}/{len(steps)} steps over 320 (+15 %, catch-up); "
                          f"centre off ≤ {max(offs) if offs else 0:.1f} pt; max |velocity| {vmax:.0f}; lines at the end "
                          f"{[l['words'] for l in S[-1]['lines']]}, lifts {S[-1]['lifts']}")


@case("LC10", ("lc",), expect="{on:false}: open flips at once, words 0 after 0.6 s; reopen within 0.15 s is not reset by the fade's completion")
def lc10():
    """Close, and close-then-reopen inside the fade."""
    fresh()
    show("one two three")
    time.sleep(0.4)
    caption_off()
    t = wait_for(lambda: not lc()["open"], 0.3, 0.01)
    time.sleep(0.6)
    a = lc()
    show("one two three")
    time.sleep(0.4)
    caption_off()
    time.sleep(0.1)
    caption("four five")
    time.sleep(0.7)
    b = lc()
    fails = []
    if not t: fails.append("open still true 0.3 s after {on:false}")
    if a["words"] != 0: fails.append(f"words {a['words']} 0.6 s after close")
    if not b["open"] or b["words"] != 2: fails.append(f"after reopen: open {b['open']}, words {b['words']}")
    return verdict(fails, f"after close: open {a['open']} words {a['words']}; after reopen at 0.1 s: open {b['open']} "
                          f"words {b['words']} (the panel's alpha is not in describe(): a fade that ends at 0 over a reopened band is invisible here)")


@case("LC11", ("lc",), expect="second display: the band on the screen under the pointer (needs G7 frame)")
def lc11():
    """Two displays — not observable yet."""
    return "SKIP", "needs G7 liveCaption.frame/screen"


@case("LC12", ("lc",), expect="RELAY_SHOOT never shows the band")
def lc12():
    """RELAY_SHOOT — needs a relaunch with the env var."""
    return "SKIP", "needs the app relaunched under RELAY_SHOOT (out of scope: no restarts from the runner)"


@case("LC14", ("lc",), expect="empty text while open: words 0, still open")
def lc14():
    """An empty sentence clears the line but keeps the band."""
    fresh()
    show("a b c")
    time.sleep(0.3)
    caption("")
    s = wait_for(lambda: (lambda x: x if x["words"] == 0 else None)(lc()), 1.0, 0.02)
    if not s:
        return "FAIL", f"words {lc()['words']} after an empty caption"
    return verdict([] if s["open"] else ["band closed"], f"words {s['words']}, open {s['open']}")


@case("LC15", ("lc",), expect="{text:\"a b c.\", partial:\"d e f\"}: committed 3, solidity (opacity / ink) ≈ [1,1,1,0.8,0.6,0.4] within 0.6 s on the words half in, settled opacity ≈ it; commit all → ≈ 1 within 0.8 s, corrections 0")
def lc15():
    """The provisional tail is drawn as a ramp and solidifies when committed."""
    fresh()
    target = [1, 1, 1, 0.8, 0.6, 0.4]
    S, _ = drive([(0.0, lambda: caption("a b c.", "d e f"))], 1.3)
    S = [s for s in S if s["words"] == 6]
    if not S:
        return "FAIL", "the band never showed 6 words"
    t0 = S[0]["t"]
    at06 = next((s for s in S if s["t"] >= t0 + 0.6), S[-1])
    end = S[-1]
    # Solidity, not what the eye sees (2026-09-28): since 84d420e `opacity` is solidity × the entry
    # front's ink, and six words are still being swept in at +0.6 s — the ramp is `opacity / appear`,
    # read on the words at least half in.
    solid = [(o / a, t) for o, a, t in zip(at06["opacity"], at06["appear"], target) if a >= 0.5]
    err06 = max((abs(o - t) for o, t in solid), default=1.0)
    errE = max(abs(a - b) for a, b in zip(end["opacity"], target))
    S2, _ = drive([(0.0, lambda: caption("a b c. d e f"))], 1.0)
    t1 = next((s["t"] for s in S2 if s["committed"] == 6), None)
    at08 = next((s for s in S2 if t1 is not None and s["t"] >= t1 + 0.8), S2[-1])
    fails = []
    if S[0]["committed"] != 3: fails.append(f"committed {S[0]['committed']}")
    if err06 > 0.1: fails.append(f"solidity {[round(o, 2) for o, _ in solid]} at +0.6 s")   # τ 0.22 → 93 % there
    if errE > 0.03: fails.append(f"settled opacity {end['opacity']}")
    if t1 is None: fails.append("the commit never reached the band")
    if min(at08["opacity"]) < 0.95: fails.append(f"opacity {at08['opacity']} 0.8 s after the commit")
    if S2[-1]["corrections"]: fails.append(f"corrections {S2[-1]['corrections']}")
    return verdict(fails, f"+0.6 s solidity {[round(o, 2) for o, _ in solid]} over {len(solid)} word(s) in (max err {err06:.2f}), settled {end['opacity']}; after commit +0.8 s {at08['opacity']}, "
                          f"corrections {S2[-1]['corrections']}")


@case("LC16", ("lc",), expect="silence after two lines: the top line rolls out at readTime(its words) after the last word, the other "
      "glides up to slot 0 (landed ≤ 1.0 s) and rolls out readTime(its words) after that; the band stays open and its backdrop "
      "fades (< 0.05 within 1.2 s); the next word is a fresh top line (slot 0, reason first, centred, at rest)")
def lc16():
    """Silence rolls the lines out one by one, each after its read time; then a fresh line."""
    fresh()
    w = WORDS[:26]
    ev = [(0.25 * k, (lambda k=k: caption(" ".join(w[:k + 1])))) for k in range(len(w))]
    S0, fired = drive(ev, 0.25 * (len(w) - 1) + 0.6)
    s_end = S0[-1]
    if len(s_end["lines"]) != 2:
        return "SKIP", f"26 words made {len(s_end['lines'])} line(s) on a {s_end['bandWidth']:.0f} pt band"
    n1, n2 = s_end["lines"][0]["words"], s_end["lines"][1]["words"]
    t_last = fired[-1]
    S1 = sample_until(lambda s: s["lifts"] >= 2 and not s["leaving"], read_time(n1) + read_time(n2) + 2.0)
    base = S0[-1]["t"]
    for s in S1: s["t"] += base + 0.05
    S = S0 + S1
    lifts = lift_times(S)
    fails, notes = [], []
    if len(lifts) < 2:
        return "FAIL", f"only {len(lifts)} roll-up(s) in silence"
    t1, t2 = lifts[0][0], lifts[1][0]
    notes.append(f"line of {n1} rolled at +{t1 - t_last:.2f} s (read {read_time(n1):.1f}), line of {n2} {t2 - t1:.2f} s later (read {read_time(n2):.1f})")
    if not read_time(n1) - 0.1 <= t1 - t_last <= read_time(n1) + 0.35: fails.append(f"first roll-up at +{t1 - t_last:.2f} s")
    if not read_time(n2) - 0.1 <= t2 - t1 <= read_time(n2) + 0.35: fails.append(f"second roll-up {t2 - t1:.2f} s after the first")
    glide = [s for s in S if t1 <= s["t"] < t2 and s["lines"]]
    landed = next((s["t"] - t1 for s in glide if s["lines"][0]["landed"]), None)
    notes.append(f"line 2 landed in slot 0 after {landed and round(landed, 2)} s")
    if landed is None or landed > 1.0: fails.append(f"line 2 never landed within 1.0 s ({landed})")
    S2 = sample(1.3)
    if S2[-1]["lines"]: fails.append(f"lines left {S2[-1]['lines']}")
    if not S2[-1]["open"]: fails.append("the band closed")
    if S2[-1]["backdropAlpha"] >= 0.05: fails.append(f"backdrop alpha {S2[-1]['backdropAlpha']:.2f} 1.3 s after the last roll-up")
    caption(" ".join(w + ["golf"]))
    s0 = wait_for(lambda: (lambda s: s if s["words"] == len(w) + 1 and s["lines"] else None)(lc()), 1.0, 0.02)
    if not s0:
        fails.append("the word after the roll-ups never reached the band")
        return verdict(fails, "; ".join(notes))
    l0 = s0["lines"][0]
    notes.append(f"fresh line: slot {l0['slot']}, reason {l0['reason']}, centre off {l0['centre'] - mid(s0):.1f}, velocity {s0['velocity']:.0f}")
    if len(s0["lines"]) != 1 or l0["slot"] != 0 or l0["reason"] != "first": fails.append(f"fresh line {[(l['slot'], l['reason']) for l in s0['lines']]}")
    if abs(l0["centre"] - mid(s0)) >= 3: fails.append(f"fresh line off centre by {l0['centre'] - mid(s0):.0f}")
    if s0["velocity"] > 0.5: fails.append(f"fresh line moving at {s0['velocity']:.0f}")
    return verdict(fails, "; ".join(notes))


@case("LC17", ("lc",), expect="gentle correction: corrections +1, and the silence clock is not restarted — the line rolls out "
      "readTime after the last spoken word, not after the correction")
def lc17():
    """A batch correction behind him does not count as him speaking again."""
    fresh()
    show("we deploy on friday")
    t_word = time.time()
    time.sleep(1.5)
    c0 = lc()["corrections"]
    caption("we deploy on Monday", gentle=True)
    t_gentle = time.time()
    S = sample_until(lambda s: s["lifts"] >= 1, read_time(4) + 3.0)
    t_up = next((t_gentle + s["t"] for s in S if s["lifts"] >= 1), None)
    dc = max(s["corrections"] for s in S) - c0
    fails = []
    if dc != 1: fails.append(f"corrections +{dc}")
    if t_up is None:
        fails.append("the line never rolled out")
    elif not read_time(4) - 0.1 <= t_up - t_word <= read_time(4) + 0.35:
        fails.append(f"rolled out {t_up - t_word:.2f} s after the spoken word ({t_up - t_gentle:.2f} s after the gentle one)")
    return verdict(fails, f"corrections +{dc}; rolled out {t_up and round(t_up - t_word, 2)} s after the last spoken word, "
                          f"{t_up and round(t_up - t_gentle, 2)} s after the gentle correction (read time {read_time(4)})")


@case("LC19", ("lc",), expect="line 2 starts at 80 %: maxLineWidth = 0.8 bandWidth; no line ever wider; the word that began "
      "line 2 (reason full) would have taken line 1 past it")
def lc19():
    """The wrap: a word that would take the line past 80 % of the band starts the next line."""
    fresh()
    n = 30
    ev = [(0.15 * k, (lambda k=k: caption(" ".join(WORDS[:k + 1])))) for k in range(n)]
    S, _ = drive(ev, 0.15 * n + 1.5)
    s = S[-1]
    fails = []
    if abs(s["maxLineWidth"] - 0.8 * s["bandWidth"]) > 0.5: fails.append(f"maxLineWidth {s['maxLineWidth']} of {s['bandWidth']}")
    wide = [(x["t"], round(l["width"])) for x in S for l in x["lines"] if l["width"] > x["maxLineWidth"] + 0.5]
    if wide: fails.append(f"{len(wide)} line sample(s) past 80 %, first {wide[0]}")
    if len(s["lines"]) != 2:
        fails.append(f"{len(s['lines'])} line(s) after {n} words")
        return verdict(fails, f"lines {[l['words'] for l in s['lines']]}")
    l0, l1 = s["lines"]
    first = l1["first"] - s["dropped"]
    w = s["widths"][first]
    if l1["reason"] != "full": fails.append(f"line 2 reason {l1['reason']}")
    if not l0["width"] + w > s["maxLineWidth"]: fails.append(f"line 1 {l0['width']:.0f} + next word {w:.0f} fits in {s['maxLineWidth']:.0f}")
    return verdict(fails, f"line 1: {l0['words']} words, {l0['width']:.0f} pt; its next word {w:.0f} pt would make "
                          f"{l0['width'] + w:.0f} > {s['maxLineWidth']:.0f}; line 2: {l1['words']} words")


def overflow_drive(max_words=80, gap=0.5, tail=2.5):
    """Words at `gap` until a third line is needed, sampling as fast as the route answers."""
    fresh()
    S, t0, k, t_lift, added = [], time.time(), 0, None, {}
    while k < max_words and (t_lift is None or time.time() - t_lift < tail):
        if time.time() - t0 >= gap * k:
            caption(" ".join((WORDS * 2)[:k + 1])); added[k + 1] = round(time.time() - t0, 3); k += 1
        s = lc(); s["t"] = round(time.time() - t0, 3); S.append(s)
        if t_lift is None and s["lifts"] >= 1:
            t_lift = time.time()
        time.sleep(0.015)
    return S, added


@case("LC20", ("lc",), expect="line 2 fills: the old line 1 rolls out (leaving), line 2 becomes line 1 with its text intact, "
      "the word that did not fit starts the new line 2 (reason full)")
def lc20():
    """The roll-up on a full second line."""
    S, _ = overflow_drive()
    i = next((j for j, s in enumerate(S) if s["lifts"] >= 1), None)
    if i is None or i == 0:
        return "FAIL", f"no roll-up after {S[-1]['words']} words"
    a, b = S[i - 1], S[i]
    fails = []
    if len(a["lines"]) != 2: fails.append(f"{len(a['lines'])} line(s) before the roll-up")
    else:
        if not b["leaving"] or b["leaving"][-1]["id"] != a["lines"][0]["id"]: fails.append(f"leaving {b['leaving']}, expected line {a['lines'][0]['id']}")
        if not b["lines"] or b["lines"][0]["id"] != a["lines"][1]["id"]: fails.append("line 2 did not become line 1")
        elif not b["lines"][0]["text"].startswith(a["lines"][1]["text"]): fails.append(f"line 2's text changed: {a['lines'][1]['text']!r} → {b['lines'][0]['text']!r}")
        if len(b["lines"]) != 2 or b["lines"][1]["reason"] != "full": fails.append(f"new line {[(l['id'], l['reason']) for l in b['lines']]}")
        else:
            first = b["lines"][1]["first"] - b["dropped"]
            if not b["lines"][0]["width"] + b["widths"][first] > b["maxLineWidth"]:
                fails.append("the word that began the new line would have fitted")
    return verdict(fails, f"roll-up at word {b['words']} (+{b['t']:.2f} s): {a['lines'][0]['words'] if a['lines'] else '?'} words out, "
                          f"line 1 now {b['lines'][0]['words'] if b['lines'] else '?'} words")


@case("LC24", ("lc",), expect="overflow order (Victor 2026-09-28: *\"când ar trebui să apară rândul 3, atunci rândul 1 iese în sus, "
      "și după ce rândul 2 devine 1, atunci începe să apară și rândul '3' pe poziția 2\"*): no roll-up before the overflow word; "
      "on the first sample showing it, line 1 is already leaving (slot ≥ −0.4, ≤ 1 frame + a read in); line 2 lands in slot 0 "
      "within 1.0 s; no letter of the new line appears (reveal ≤ 0) until line 2 has landed; words said during the glide wait, "
      "none dropped")
def lc24():
    """The overflow sequence: out, up, then the new line."""
    S, added = overflow_drive()
    i = next((j for j, s in enumerate(S) if s["lifts"] >= 1), None)
    if i is None:
        return "FAIL", f"no roll-up after {S[-1]['words']} words"
    ov = S[i]
    n_ov = ov["words"]
    first_seen = next(s for s in S if s["words"] >= n_ov)
    fails, notes = [], []
    early = [s["t"] for s in S[:i] if s["lifts"] or s["leaving"]]
    if early: fails.append(f"a line left before the overflow word, at {early[:2]}")
    if first_seen is not ov: fails.append(f"the overflow word was on screen at +{first_seen['t']} s before the roll-up at +{ov['t']} s")
    lv = ov["leaving"][-1]["slot"] if ov["leaving"] else None
    notes.append(f"overflow word {n_ov} added at +{added.get(n_ov)} s, seen at +{ov['t']} s with line 1 leaving at slot {lv and round(lv, 2)}")
    if lv is None or lv < -0.4: fails.append(f"leaving slot {lv} on the first sample")
    new_id = ov["lines"][1]["id"] if len(ov["lines"]) == 2 else None
    after = S[i:]
    t_land = next((s["t"] for s in after if s["lines"] and s["lines"][0]["landed"]), None)
    notes.append(f"line 2 landed after {t_land and round(t_land - ov['t'], 2)} s")
    if t_land is None or t_land - ov["t"] > 1.0: fails.append(f"line 2 landed only at {t_land}")
    leaks, first_rev = [], None
    for s in after:
        if len(s["lines"]) != 2 or s["lines"][1]["id"] != new_id:
            continue
        ks = [k for k, li in enumerate(s["lineOf"]) if li == 1]
        rev = [s["reveal"][k] for k in ks if k < len(s["reveal"])]
        shown_any = any(r is None or r > 0 for r in rev)
        if shown_any and first_rev is None:
            first_rev = s
        if shown_any and not s["lines"][0]["landed"]:
            leaks.append((s["t"], s["lines"][0]["slot"]))
    if leaks: fails.append(f"new line revealed while line 2 was still gliding: {leaks[:2]}")
    if first_rev is None: fails.append("the new line never began")
    else: notes.append(f"new line's first letters at +{first_rev['t'] - ov['t']:.2f} s (line 1 slot {first_rev['lines'][0]['slot']:.3f})")
    glide_words = [n for n, t in added.items() if n > n_ov and t_land and t < t_land]
    end = S[-1]
    if sum(l["words"] for l in end["lines"]) != end["words"] - end["dropped"]: fails.append("words unaccounted for on the lines")
    notes.append(f"{len(glide_words)} word(s) said during the glide, all on the new line at the end: "
                 f"{end['lines'][-1]['words'] if end['lines'] else 0} words there")
    return verdict(fails, "; ".join(notes))


@case("LC21", ("lc",), expect="silence read time scales with the words: a 14-word line rolls out at max(3, 0.3 × 14) = 4.2 s "
      "after its last word (−0.1/+0.35); `liftIn` counts down to it")
def lc21():
    """The read time's per-word term."""
    fresh()
    w = WORDS[:14]
    ev = [(0.25 * k, (lambda k=k: caption(" ".join(w[:k + 1])))) for k in range(len(w))]
    S0, fired = drive(ev, 0.25 * 13 + 0.3)
    if len(S0[-1]["lines"]) != 1:
        return "SKIP", f"14 words made {len(S0[-1]['lines'])} lines on a {S0[-1]['bandWidth']:.0f} pt band"
    t_last = fired[-1]
    li0 = S0[-1]["liftIn"]
    S1 = sample_until(lambda s: s["lifts"] >= 1, 6.0)
    base = S0[-1]["t"]
    t_up = next((base + 0.03 + s["t"] for s in S1 if s["lifts"] >= 1), None)
    fails = []
    if t_up is None: fails.append("never rolled out")
    elif not read_time(14) - 0.1 <= t_up - t_last <= read_time(14) + 0.35: fails.append(f"rolled out at +{t_up - t_last:.2f} s")
    return verdict(fails, f"rolled out {t_up and round(t_up - t_last, 2)} s after the last word (read time {read_time(14):.1f}); "
                          f"liftIn read {li0 and round(li0, 2)} at +{S0[-1]['t'] - t_last:.2f} s")


@case("LC22", ("lc",), expect="a commit ending a sentence starts a new line: \"We deploy today.\" committed, then \"Then\" → lineOf "
      "[0,0,0,1], line 2 reason sentence though line 1 is short; a commit without terminal punctuation (\"Then we\") does not break: "
      "\"test\" stays on line 2")
def lc22():
    """New sentence ⇒ new line."""
    fresh()
    show("", "we deploy", words=2)
    time.sleep(0.4)
    show("We deploy today.")
    time.sleep(0.4)
    s = show("We deploy today.", "Then")
    fails = []
    if not s: return "FAIL", "the partial after the commit never reached the band"
    if s["lineOf"] != [0, 0, 0, 1]: fails.append(f"lineOf {s['lineOf']}")
    if len(s["lines"]) != 2 or s["lines"][1]["reason"] != "sentence": fails.append(f"lines {[(l['text'], l['reason']) for l in s['lines']]}")
    elif s["lines"][0]["width"] > 0.5 * s["maxLineWidth"]: fails.append("line 1 was not short")
    time.sleep(0.4)
    show("We deploy today. Then we")
    time.sleep(0.3)
    s2 = show("We deploy today. Then we", "test")
    if not s2 or s2["lineOf"] != [0, 0, 0, 1, 1, 1]: fails.append(f"after a mid-sentence commit lineOf {s2 and s2['lineOf']}")
    return verdict(fails, f"lineOf {s['lineOf']} ({[l['reason'] for l in s['lines']]}), then {s2 and s2['lineOf']}")


@case("LC23", ("lc",), expect="a gentle correction that merges the sentences keeps the split: \"We deploy today. Then we test\" → "
      "\"We deploy today and then we test\": corrections +1 (\"and\", on line 1), \"then we test\" still on line 2 (lineOf "
      "[0,0,0,0,1,1,1]), no ghosts, line 2 still reason sentence")
def lc23():
    """Line assignment is sticky per word."""
    fresh()
    show("", "we deploy", words=2); time.sleep(0.4)
    show("We deploy today."); time.sleep(0.4)
    show("We deploy today.", "Then we"); time.sleep(0.4)
    show("We deploy today. Then we test"); time.sleep(1.0)
    c0 = lc()["corrections"]
    S, _ = drive([(0.0, lambda: caption("We deploy today and then we test", gentle=True))], 1.5)
    s = S[-1]
    fails = []
    dc = s["corrections"] - c0
    if dc != 1: fails.append(f"corrections +{dc}")
    if s["lineOf"] != [0, 0, 0, 0, 1, 1, 1]: fails.append(f"lineOf {s['lineOf']}")
    gh = [x["ghosts"] for x in S if x["ghosts"]]
    if gh: fails.append(f"ghosts {gh[0]}")
    if len(s["lines"]) != 2 or s["lines"][1]["reason"] != "sentence": fails.append(f"lines {[(l['text'], l['reason']) for l in s['lines']]}")
    return verdict(fails, f"corrections +{dc}, lineOf {s['lineOf']}, lines {[l['text'] for l in s['lines']]}")


@case("LC25", ("lc",), expect="backdrop: settled, it is the union of the lines' text boxes grown by 10 pt on every side (±1 pt), "
      "alpha > 0.95 — for two lines and for one")
def lc25():
    """The grey backdrop hugs the text block."""
    def check(label):
        s = lc()
        boxes = s["lineBoxes"]
        if not boxes: return [f"{label}: no line boxes"], ""
        x0 = min(b["x"] for b in boxes) - PAD; x1 = max(b["x"] + b["w"] for b in boxes) + PAD
        y0 = min(b["y"] for b in boxes) - PAD; y1 = max(b["y"] + b["h"] for b in boxes) + PAD
        d = s["backdrop"]
        err = max(abs(d["x"] - x0), abs(d["x"] + d["w"] - x1), abs(d["y"] - y0), abs(d["y"] + d["h"] - y1))
        f = []
        if err > 1: f.append(f"{label}: backdrop {d} vs text ± 10 = {(round(x0), round(y0), round(x1 - x0), round(y1 - y0))} (err {err:.1f})")
        if s["backdropAlpha"] < 0.95: f.append(f"{label}: alpha {s['backdropAlpha']:.2f}")
        return f, f"{label}: {len(boxes)} line(s), backdrop {d['w']:.0f}×{d['h']:.0f} pt, edge error {err:.2f} pt"
    fresh()
    show(" ".join(WORDS[:26]))
    # a 26-word burst is swept in at the catch-up cap (≤ 490 pt/s): ~5 s; then 1 s to settle
    wait_for(lambda: all(r is None for r in lc()["reveal"]), 8.0, 0.1)
    time.sleep(1.0)
    f2, n2 = check("two lines")
    fresh()
    show("hello there")
    time.sleep(1.5)
    f1, n1 = check("one line")
    return verdict(f2 + f1, f"{n2}; {n1}")


@case("LC26", ("lc",), expect="dodge (Victor: *\"flip top/bottom should be without pan, sudden\"*): pointer into the backdrop → "
      "position bottom on the first frame after the pointer reaches the band (flipLagMs ≤ one frame + 5 ms; ≤ 0.3 s over "
      "HTTP), the panel at only two y's (no pan), backdrop 2 pt above the bottom edge; pointer 6 pt outside (inside the 12 pt "
      "slack) keeps it down; pointer away → back up after the 0.25 s debounce (flipLagMs 250 … 250 + two frames + 5), again in one step")
def lc26():
    """The band gets out of the pointer's way, in one frame each way."""
    fresh()
    show(" ".join(WORDS[:10]))
    time.sleep(1.5)
    s = lc()
    top_y, b, scr = s["frame"]["y"], s["backdrop"], s["screen"]
    try:
        pointer({"x": b["x"] + b["w"] / 2, "y": b["y"] + b["h"] / 2}); t0 = time.time()
        D = []
        while time.time() - t0 < 0.6:
            x = lc(); x["t"] = time.time() - t0; D.append(x); time.sleep(0.005)
        pointer({"x": b["x"] + b["w"] / 2, "y": b["y"] - 6})   # below the top backdrop, inside the slack
        time.sleep(0.6)
        held = lc()["position"]
        pointer({"x": scr["x"] + scr["w"] / 2, "y": scr["y"] + scr["h"] / 2}); t1 = time.time()
        U = []
        while time.time() - t1 < 0.8:
            x = lc(); x["t"] = time.time() - t1; U.append(x); time.sleep(0.005)
    finally:
        pointer(None)
    fails, notes = [], []
    t_down = next((x["t"] for x in D if x["position"] == "bottom"), None)
    bot = D[-1]
    bot_y = bot["frame"]["y"]
    gap = bot["backdrop"]["y"] - scr["y"]
    frame = max(x["frameMs"] for x in D + U)
    lag_down = bot.get("flipLagMs")
    lag_up = U[-1].get("flipLagMs") if U else None
    notes.append(f"down {lag_down} ms after the pointer reached the band (seen over HTTP at {t_down and round(t_down, 3)} s; frame "
                 f"{frame} ms), frame y {top_y:.0f} → {bot_y:.0f}, backdrop {gap:.1f} pt above the bottom")
    if t_down is None or t_down > 0.3: fails.append(f"flipped down only at {t_down} s over HTTP")
    if lag_down is None or lag_down > frame + 5: fails.append(f"flip lag {lag_down} ms > one frame ({frame} ms)")
    mids = [round(x["frame"]["y"]) for x in D + U if abs(x["frame"]["y"] - top_y) > 1 and abs(x["frame"]["y"] - bot_y) > 1]
    if mids: fails.append(f"panned through {mids[:4]}")
    if abs(gap - EDGE_GAP) > 1: fails.append(f"backdrop {gap:.1f} pt above the bottom edge")
    if held != "bottom": fails.append(f"6 pt outside (inside the slack) it went {held}")
    t_up = next((x["t"] for x in U if x["position"] == "top"), None)
    notes.append(f"6 pt outside: {held}; up {lag_up} ms after the pointer left (debounce {DEBOUNCE * 1000:.0f}; over HTTP {t_up and round(t_up, 3)} s)")
    if t_up is None or not DEBOUNCE - 0.03 <= t_up <= DEBOUNCE + 0.3: fails.append(f"back up at {t_up} s over HTTP")
    if lag_up is None or not DEBOUNCE * 1000 <= lag_up <= DEBOUNCE * 1000 + 2 * frame + 5:
        fails.append(f"up flip lag {lag_up} ms")   # the first tick starts the debounce, the tick after it ends it
    if U and abs(U[-1]["frame"]["y"] - top_y) > 1: fails.append(f"frame y {U[-1]['frame']['y']} at the end, top is {top_y}")
    return verdict(fails, "; ".join(notes))


@case("LC18", ("lc",), expect="timing precision needs G8's server-side script/trace, two displays G7's frame")
def lc18():
    """Frame-accurate timing — not observable yet."""
    return "SKIP", "needs G8 (/test/live-caption script + trace)"
