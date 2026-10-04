#!/usr/bin/env python3
"""How well the local model's word timings place a screenshot marker (2026-10-04).

    python3 evals/local-word-timing/eval.py pick   [N]      # choose the clips
    /tmp/pk-venv/bin/python evals/local-word-timing/eval.py ref   # parakeet reference
    python3 evals/local-word-timing/eval.py hyp              # helper runs, every config
    python3 evals/local-word-timing/eval.py pauses           # real pauses, cut-halves truth
    python3 evals/local-word-timing/eval.py report           # → results.txt

Clips: the corpus' ElevenLabs dictations (`-11l`, recorded by the relay's own
microphone). Scribe's `words[]` were never stored (not in the outbox, the corpus
or the log), so the reference is an independent recogniser with its own clock:
**parakeet-tdt-0.6b-v3** (NVIDIA, multilingual incl. Romanian; TDT token
durations, 80 ms frames) via `parakeet-mlx`. Neither side is ground truth; the
boundary numbers are a disagreement between two aligners.

Configs, all through `helpers/whisper_helper.py` itself (the same prompt, LID
pin and loop guard as the app):
  victor-official   whisper-turbo-victor, OpenAI's six turbo alignment heads
  victor-default    whisper-turbo-victor, mlx_whisper's default (40 heads)
  orig-official     mlx-community/whisper-large-v3-turbo, six heads
Each also `+snap`: the same words through `helpers/word_onsets.snap_starts`.

**Read the pause numbers from `pauses`, not from parakeet.** Parakeet's own
"pauses" are often voiced on the meter (its word after a gap starts late), so
the parakeet-pause line understates both. The truth that trusts no aligner: in
each clip the longest stretch our VAD calls silent (≥ 0.25 s), the clip cut at
its middle, both halves decoded alone — the press at the cut must land in front
of the right half's first word. Raw Whisper: 45.7 %; snapped: 88.6 %.

Latency: in the victor-official process each clip is decoded with words off
and on, order alternating, so both halves share the machine's load.
"""
import difflib, json, os, random, re, statistics, subprocess, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CORPUS = os.path.expanduser("~/.walkie-talkie/voice-corpus")
LORA = os.path.expanduser("~/.walkie-talkie/models/whisper-turbo-victor")
ORIG = "mlx-community/whisper-large-v3-turbo"
OUT = os.path.join(HERE, "out")
CONFIGS = {"victor-official": (LORA, "official"),
           "victor-default": (LORA, "default"),
           "orig-official": (ORIG, "official")}


def jl(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def pick(n=60):
    rows = []
    for d in jl(os.path.join(CORPUS, "corpus.jsonl")):
        i = d.get("id") or ""
        if "-11l" in i and 3 <= d.get("duration", 0) <= 40 and d.get("text"):
            if os.path.exists(os.path.join(CORPUS, d["wav"])):
                rows.append({"id": i, "wav": os.path.join(CORPUS, d["wav"]), "duration": d["duration"]})
    random.Random(4).shuffle(rows)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "clips.jsonl"), "w") as f:
        for r in rows[:n]:
            f.write(json.dumps(r) + "\n")
    print(f"{min(n, len(rows))} of {len(rows)} -11l clips")


def ref():
    from parakeet_mlx import from_pretrained
    m = from_pretrained("mlx-community/parakeet-tdt-0.6b-v3")
    with open(os.path.join(OUT, "ref.jsonl"), "w") as f:
        for c in jl(os.path.join(OUT, "clips.jsonl")):
            r = m.transcribe(c["wav"])
            words = []
            for s in r.sentences:
                for t in s.tokens:
                    if not words or t.text.startswith(" "):
                        words.append({"text": t.text, "start": t.start, "end": t.end})
                    else:
                        words[-1]["text"] += t.text
                        words[-1]["end"] = t.end
            f.write(json.dumps({"id": c["id"], "text": r.text, "words": words}) + "\n")
            print(c["id"], len(words), flush=True)


def helper(model, alignment):
    env = dict(os.environ, RELAY_WHISPER_MODEL=model, RELAY_WHISPER_ALIGNMENT=alignment)
    env["PATH"] = env.get("PATH", "") + ":/opt/homebrew/bin"
    p = subprocess.Popen([sys.executable, os.path.join(REPO, "helpers/whisper_helper.py")],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         text=True, env=env)
    hello = json.loads(p.stdout.readline())
    assert hello.get("ready"), hello

    def ask(wav, words):
        p.stdin.write(json.dumps({"wav": wav, "words": words}) + "\n"); p.stdin.flush()
        return json.loads(p.stdout.readline())
    return p, ask


def hyp():
    clips = jl(os.path.join(OUT, "clips.jsonl"))
    for name, (model, alignment) in CONFIGS.items():
        p, ask = helper(model, alignment)
        with open(os.path.join(OUT, f"hyp-{name}.jsonl"), "w") as f:
            for k, c in enumerate(clips):
                row = {"id": c["id"], "duration": c["duration"]}
                if name == "victor-official":
                    order = (False, True) if k % 2 == 0 else (True, False)
                    for w in order:
                        r = ask(c["wav"], w)
                        row["off" if not w else "on"] = r
                else:
                    row["on"] = ask(c["wav"], True)
                f.write(json.dumps(row) + "\n")
                print(name, c["id"], flush=True)
        p.stdin.close(); p.wait()


def pauses():
    """Real pauses as ground truth: in each clip, the longest stretch our own
    VAD calls silent (≥ 0.25 s, ≥ 0.5 s of voice on either side); the clip is cut
    at its middle and both halves decoded alone, so the words before the pause
    are known without trusting any aligner."""
    import wave
    import numpy as np
    sys.path.insert(0, os.path.join(REPO, "helpers"))
    from word_onsets import FRAME
    p, ask = helper(LORA, "official")
    tmp = os.path.join(OUT, "halves"); os.makedirs(tmp, exist_ok=True)
    with open(os.path.join(OUT, "pauses.jsonl"), "w") as f:
        for c in jl(os.path.join(OUT, "clips.jsonl")):
            x = samples_of(c["wav"])
            hop = int(FRAME * 16000); n = len(x) // hop
            rms = np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9
            db = 20 * np.log10(rms)
            voiced = (db > np.percentile(db, 10) + 12) & (rms > 180 / 32768)
            best, k = None, 0
            while k < n:
                if voiced[k]:
                    k += 1; continue
                j = k
                while j < n and not voiced[j]:
                    j += 1
                if (j - k) * FRAME >= 0.25 and voiced[:k].sum() * FRAME >= 0.5 and voiced[j:].sum() * FRAME >= 0.5:
                    if best is None or j - k > best[1] - best[0]:
                        best = (k, j)
                k = j
            if not best:
                continue
            cut = (best[0] + best[1]) / 2 * FRAME
            halves = []
            for name, part in (("L", x[:int(cut * 16000)]), ("R", x[int(cut * 16000):])):
                path = os.path.join(tmp, f"{c['id']}-{name}.wav")
                with wave.open(path, "wb") as w:
                    w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
                    w.writeframes((np.clip(part, -1, 1) * 32767).astype(np.int16).tobytes())
                halves.append(ask(path, False)["text"])
            f.write(json.dumps({"id": c["id"], "cut": cut, "pause": (best[1] - best[0]) * FRAME,
                                "left": halves[0], "right": halves[1]}) + "\n")
            print(c["id"], round(cut, 2), flush=True)
    p.stdin.close(); p.wait()


def norm(w):
    w = unicodedata.normalize("NFC", w.lower()).replace("ş", "ș").replace("ţ", "ț")
    return re.sub(r"[^\w]", "", w)


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else float("nan")


def samples_of(wav):  # noqa: E302
    import wave
    import numpy as np
    with wave.open(wav) as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def report():
    sys.path.insert(0, os.path.join(REPO, "helpers"))
    from word_onsets import snap_starts
    refs = {r["id"]: r for r in jl(os.path.join(OUT, "ref.jsonl"))}
    clips = {c["id"]: c for c in jl(os.path.join(OUT, "clips.jsonl"))}
    rng = random.Random(7)
    lines = []
    lat = jl(os.path.join(OUT, "hyp-victor-official.jsonl"))
    off = [r["off"]["decode_s"] for r in lat]; on = [r["on"]["decode_s"] for r in lat]
    ratio = [b / a for a, b in zip(off, on) if a > 0]
    same = sum(r["off"]["text"] == r["on"]["text"] for r in lat)
    audio = sum(r["duration"] for r in lat)
    lines.append(f"latency (whisper-turbo-victor, {len(lat)} clips, {audio:.0f} s audio): "
                 f"words off {sum(off):.1f} s, on {sum(on):.1f} s → total +{(sum(on)/sum(off)-1)*100:.1f} %, "
                 f"median per-clip ratio {statistics.median(ratio):.3f} (p90 {pct(ratio, .9):.3f}); "
                 f"text identical on {same}/{len(lat)}")
    variants = [(n, n, False) for n in CONFIGS] + [(n + "+snap", n, True) for n in CONFIGS]
    for name, src, snap in variants:
        rows = jl(os.path.join(OUT, f"hyp-{src}.jsonl"))
        ds, de, gaps, near, scored, total = [], [], 0, 0, 0, 0
        signed, pgaps, pscored = [], 0, 0
        for row in rows:
            rf = refs.get(row["id"])
            hw = row["on"].get("words") or []
            if snap and hw:
                hw = snap_starts(hw, samples_of(clips[row["id"]]["wav"]))
            if not rf or not hw or not rf["words"]:
                continue
            rw = rf["words"]
            a, b = [norm(w["text"]) for w in hw], [norm(w["text"]) for w in rw]
            pairs = {}
            for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
                for k in range(blk.size):
                    pairs[blk.a + k] = blk.b + k
            for i, j in pairs.items():
                if a[i]:
                    signed.append(hw[i]["start"] - rw[j]["start"])
                    ds.append(abs(hw[i]["start"] - rw[j]["start"]))
                    de.append(abs(hw[i]["end"] - rw[j]["end"]))
            # A press in a pause he left: the middle of every reference gap ≥ 0.25 s
            # between two words both sides matched.
            inv = {j: i for i, j in pairs.items()}
            for j in range(1, len(rw)):
                if rw[j]["start"] - rw[j - 1]["end"] < 0.25 or j not in inv or j - 1 not in inv:
                    continue
                t = (rw[j - 1]["end"] + rw[j]["start"]) / 2
                h = sum(w["start"] < t for w in hw)
                pscored += 1
                pgaps += (h == inv[j])
            lo, hi = rw[0]["start"], rw[-1]["end"]
            for _ in range(20):
                t = rng.uniform(lo, hi)
                total += 1
                r = sum(w["start"] < t for w in rw)
                h = sum(w["start"] < t for w in hw)
                # the hypothesis' gap h, mapped onto the reference's word indices
                left = pairs.get(h - 1, -1 if h == 0 else None)
                right = pairs.get(h, len(rw) if h == len(hw) else None)
                if left is None or right is None or right != left + 1:
                    continue
                scored += 1
                gaps += (right == r)
                near += abs(right - r) <= 1
        lines.append(f"{name}: {len(ds)} matched words — |Δstart| median {statistics.median(ds)*1000:.0f} ms, "
                     f"p90 {pct(ds, .9)*1000:.0f} ms; |Δend| median {statistics.median(de)*1000:.0f} ms, "
                     f"p90 {pct(de, .9)*1000:.0f} ms; markers in the same gap {gaps}/{scored} = "
                     f"{gaps/scored*100:.1f} % (±1 word {near/scored*100:.1f} %; {total-scored} of {total} unscorable); "
                     f"signed Δstart median {statistics.median(signed)*1000:+.0f} ms; "
                     f"a press in one of his pauses (≥ 0.25 s) lands in that pause {pgaps}/{pscored} = {pgaps/pscored*100:.1f} %")
    # Ground truth from the cut halves: the press at the middle of a real pause
    # must land in front of the first word of the right half.
    cuts = {r["id"]: r for r in jl(os.path.join(OUT, "pauses.jsonl"))}
    for name, src, snap in variants:
        ok = scored = 0
        for row in jl(os.path.join(OUT, f"hyp-{src}.jsonl")):
            cut = cuts.get(row["id"]); hw = row["on"].get("words") or []
            if not cut or not hw:
                continue
            if snap:
                hw = snap_starts(hw, samples_of(clips[row["id"]]["wav"]))
            lw = [norm(w) for w in cut["left"].split()]; rw_ = [norm(w) for w in cut["right"].split()]
            a = [norm(w["text"]) for w in hw]
            pairs = {}
            for blk in difflib.SequenceMatcher(None, a, lw + rw_, autojunk=False).get_matching_blocks():
                for k in range(blk.size):
                    pairs[blk.a + k] = blk.b + k
            # the boundary: a hyp word matched to the left's last, the next to the right's first
            bound = next((i + 1 for i in range(len(hw) - 1)
                          if pairs.get(i) == len(lw) - 1 and pairs.get(i + 1) == len(lw)), None)
            if bound is None:
                continue
            scored += 1
            ok += sum(w["start"] < cut["cut"] for w in hw) == bound
        lines.append(f"{name}: a press in the middle of a real pause (cut-halves truth) lands in it "
                     f"{ok}/{scored} = {ok/max(1,scored)*100:.1f} %")
    print("\n".join(lines))
    with open(os.path.join(HERE, "results.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "pick":
        pick(int(sys.argv[2]) if len(sys.argv) > 2 else 60)
    else:
        {"ref": ref, "hyp": hyp, "report": report, "pauses": pauses}[cmd]()
