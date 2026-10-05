#!/usr/bin/env python3
"""A/B: the live caption band from the local model vs ElevenLabs + Live (2026-10-05).

For each WAV of Victor's corpus:

- **ref**: ElevenLabs batch (`scribe_v1`) with word timings — the reference text,
  and every word's end on the WAV's clock (cached in runs/ref-*.json).
- **eleven**: `scribe_v2_realtime` over the websocket with the app's own query
  (`ElevenLabsLive.connect`: pcm_16000, VAD commit after 1.5 s, his 50 keyterms,
  ro + secondary en), the audio sent in real time in 100 ms chunks. The caption
  at any moment = committed segments + the open partial. (The app also swaps in
  a batch correction after 3 s of pause — not modelled here.)
- **local**: `LocalLiveCaption`'s policy on a virtual clock with real decode
  times — a window at every 0.5 s pause or every 2.5 s of steady speech, from
  the last settled segment to the voice's end + 0.25 s, LocalAgreement on
  segments (settle 1 s), 28 s overflow — on a `whisper_helper.py` of its own,
  with the weights the app uses.

Metrics, per engine: **lag** of each reference word = first moment it is on the
band (difflib alignment of the normalised words) − its end in the audio, p50/p90;
**shown** = share of reference words that were ever on the band; **final WER** of
the band at the end of the audio (+1.5 s) against the reference; **updates**.

    python3 ab.py <wav>…            # writes runs/<stem>.json and prints a table
"""
import asyncio, base64, difflib, json, os, re, subprocess, sys, time, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs")
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
HOME = os.path.expanduser("~/.walkie-talkie")
R = 16000


def key():
    if os.environ.get("ELEVENLABS_API_KEY"):
        return os.environ["ELEVENLABS_API_KEY"]
    for line in open(os.path.join(HOME, "elevenlabs.env")):
        if line.startswith("ELEVENLABS_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    sys.exit("no ELEVENLABS_API_KEY")


def norm_words(s):
    return re.sub(r"[^\w\s]", " ", s.lower()).split()


def wer(ref, hyp):
    a, b = norm_words(ref), norm_words(hyp)
    d = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(b) + 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (a[i - 1] != b[j - 1]))
    return d[len(b)] / max(1, len(a))


# ---------------------------------------------------------------- reference
def reference(wav):
    os.makedirs(RUNS, exist_ok=True)
    cache = os.path.join(RUNS, "ref-" + os.path.basename(wav) + ".json")
    if os.path.exists(cache):
        return json.load(open(cache))
    import urllib.request, uuid
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"model_id\"\r\n\r\nscribe_v1\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"a.wav\"\r\n"
            f"Content-Type: audio/wav\r\n\r\n").encode() + open(wav, "rb").read() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request("https://api.elevenlabs.io/v1/speech-to-text", data=body, method="POST",
                                 headers={"xi-api-key": key(), "Content-Type": f"multipart/form-data; boundary={boundary}"})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    out = {"text": r["text"], "words": [{"text": w["text"], "end": w["end"]} for w in r.get("words", []) if w.get("type") == "word"]}
    json.dump(out, open(cache, "w"), ensure_ascii=False)
    return out


# ---------------------------------------------------------------- ElevenLabs live
def keyterms():
    try:
        lines = open(os.path.join(HOME, "vocab.txt")).read().splitlines()
    except OSError:
        return []
    terms = [l.split(":", 1)[0].strip() for l in lines if l.strip() and not l.strip().startswith("#")]
    return [t for t in terms if t][:50]


async def eleven_live(pcm):
    import websockets
    from urllib.parse import urlencode
    q = [("model_id", "scribe_v2_realtime"), ("audio_format", "pcm_16000"), ("commit_strategy", "vad"),
         ("vad_silence_threshold_secs", "1.5")] + [("keyterms", t) for t in keyterms()] + \
        [("language_code", "ro"), ("secondary_languages", "en")]
    url = "wss://api.elevenlabs.io/v1/speech-to-text/realtime?" + urlencode(q)
    snaps, committed, partial = [], [], ""
    async with websockets.connect(url, additional_headers={"xi-api-key": key()}, max_size=None) as ws:
        t0 = None

        async def recv():
            nonlocal partial
            async for raw in ws:
                m = json.loads(raw)
                kind = m.get("message_type")
                if kind == "partial_transcript":
                    partial = m.get("text", "")
                elif kind in ("committed_transcript", "committed_transcript_with_timestamps"):
                    if m.get("text", "").strip():
                        committed.append(m["text"].strip())
                    partial = ""
                else:
                    continue
                if t0 is not None:
                    snaps.append((time.monotonic() - t0, " ".join(committed + ([partial] if partial else []))))

        task = asyncio.create_task(recv())
        await asyncio.sleep(0.5)                       # session_started
        t0 = time.monotonic()
        step = R // 10
        for i in range(0, len(pcm), step):
            chunk = pcm[i:i + step].tobytes()
            await ws.send(json.dumps({"message_type": "input_audio_chunk",
                                      "audio_base_64": base64.b64encode(chunk).decode(), "sample_rate": R}))
            target = t0 + (i + step) / R
            await asyncio.sleep(max(0, target - time.monotonic()))
        await asyncio.sleep(1.5)
        task.cancel()
    return snaps


# ---------------------------------------------------------------- local live
class Helper:
    def __init__(self):
        model = os.environ.get("RELAY_WHISPER_MODEL") or os.path.join(HOME, "models", "whisper-turbo-victor")
        env = dict(os.environ, PATH=os.environ["PATH"] + ":/opt/homebrew/bin", RELAY_WHISPER_MODEL=model)
        self.p = subprocess.Popen([sys.executable, os.path.join(REPO, "helpers", "whisper_helper.py")],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  text=True, env=env)
        hello = json.loads(self.p.stdout.readline())
        assert hello.get("ready"), hello
        self.model = hello["model"]

    def window(self, path):
        self.p.stdin.write(json.dumps({"pcm": path, "segments": True}) + "\n"); self.p.stdin.flush()
        return json.loads(self.p.stdout.readline())


def same(a, b):
    return norm_words(a) == norm_words(b)


def local_live(pcm, helper):
    """`LocalLiveCaption` on a virtual clock: the meter's quiet clock, the take's
    ruler, real decode times. Returns [(t, caption)]."""
    hop = 1024
    x = pcm.astype(np.float64)
    rms = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop + 1, hop)])
    floor = np.percentile(rms, 10)
    voiced = rms > max(180, floor * 2.818)            # MicRecorder.meter's bar, roughly
    path = os.path.join(RUNS, "window.pcm")
    committed, pending = [], []
    anchor = decoded = 0
    last = 0.0
    quiet = 0.0
    snaps = []
    clock = 0.0                                        # the helper is busy until here
    for i, v in enumerate(voiced):
        quiet = 0.0 if v else quiet + hop / R
        now = (i + 1) * hop
        t = now / R
        if t < clock:
            continue
        end_speech = max(anchor, now - int(quiet * R))
        if end_speech - decoded < 0.3 * R:
            continue
        paused = quiet >= 0.5
        if not (paused or t - last >= 2.5):
            continue
        to = min(now, end_speech + int(0.25 * R))
        if (to - anchor) / R > 28:
            keep_from = (to - anchor) / R - 20
            k = len([s for s in pending if s["end"] <= keep_from])
            if k:
                committed += [s["text"] for s in pending[:k]]
                shift = pending[k - 1]["end"]
                anchor += int(shift * R)
                pending = [dict(s, start=s["start"] - shift, end=s["end"] - shift) for s in pending[k:]]
            else:
                committed += [s["text"] for s in pending]
                pending = []
                anchor = to
                decoded = end_speech
                continue
        if to - anchor < R // 2:
            continue
        pcm[anchor:to].tofile(path)
        t1 = time.monotonic(); r = helper.window(path); dt = time.monotonic() - t1
        decoded, last, clock = end_speech, t, t + dt
        if not r.get("ok") or (r.get("compression_ratio") or 0) > 2.4:
            continue
        speech = (end_speech - anchor) / R
        segs = [s for s in r["segments"] if s["text"].strip() and s["start"] < speech]
        k = 0
        while k + 1 < len(segs) and k < len(pending) and same(segs[k]["text"], pending[k]["text"]) \
                and segs[k]["end"] <= speech - 1.0:
            k += 1
        if k:
            committed += [s["text"] for s in segs[:k]]
            shift = segs[k - 1]["end"]
            anchor += int(shift * R)
            pending = [dict(s, start=s["start"] - shift, end=s["end"] - shift) for s in segs[k:]]
        else:
            pending = segs
        snaps.append((t + dt, " ".join(s.strip() for s in committed + [p["text"] for p in pending])))
    return snaps


# ---------------------------------------------------------------- scoring
def score(ref, snaps, duration):
    rw = [norm_words(w["text"]) for w in ref["words"]]
    flat, owner = [], []
    for i, ws in enumerate(rw):
        for w in ws:
            flat.append(w); owner.append(i)
    first = {}
    for t, cap in snaps:
        sm = difflib.SequenceMatcher(None, flat, norm_words(cap), autojunk=False)
        for blk in sm.get_matching_blocks():
            for j in range(blk.a, blk.a + blk.size):
                first.setdefault(owner[j], t)
    lags = [first[i] - ref["words"][i]["end"] for i in first]
    final = ""
    for t, cap in snaps:
        if t <= duration + 1.5:
            final = cap
    return {
        "lag_p50": round(float(np.percentile(lags, 50)), 2) if lags else None,
        "lag_p90": round(float(np.percentile(lags, 90)), 2) if lags else None,
        "shown": round(len(first) / max(1, len(rw)), 3),
        "wer": round(wer(ref["text"], final), 3),
        "updates": len(snaps),
        "final": final,
    }


def main(wavs):
    os.makedirs(RUNS, exist_ok=True)
    helper = Helper()
    print("local model:", helper.model)
    rows = []
    for wav in wavs:
        with wave.open(wav) as w:
            assert w.getframerate() == R and w.getnchannels() == 1
            pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").copy()
        duration = len(pcm) / R
        ref = reference(wav)
        el = asyncio.run(eleven_live(pcm))
        lo = local_live(pcm, helper)
        res = {"wav": wav, "duration": round(duration, 1), "ref": ref["text"],
               "eleven": score(ref, el, duration), "local": score(ref, lo, duration),
               "eleven_snaps": el, "local_snaps": lo}
        json.dump(res, open(os.path.join(RUNS, os.path.basename(wav) + ".json"), "w"), ensure_ascii=False, indent=1)
        rows.append(res)
        e, l = res["eleven"], res["local"]
        print(f"{os.path.basename(wav):28s} {duration:5.1f}s | eleven lag {e['lag_p50']}/{e['lag_p90']} shown {e['shown']:.2f} "
              f"WER {e['wer']:.2f} n{e['updates']} | local lag {l['lag_p50']}/{l['lag_p90']} shown {l['shown']:.2f} "
              f"WER {l['wer']:.2f} n{l['updates']}", flush=True)
    for name in ("eleven", "local"):
        print(name, "lag p50 (median of clips)", np.median([r[name]["lag_p50"] for r in rows if r[name]["lag_p50"] is not None]),
              "p90", np.median([r[name]["lag_p90"] for r in rows if r[name]["lag_p90"] is not None]),
              "WER (median)", np.median([r[name]["wer"] for r in rows]),
              "WER (pooled)", round(sum(r[name]["wer"] * len(norm_words(r["ref"])) for r in rows) /
                                    sum(len(norm_words(r["ref"])) for r in rows), 3))


if __name__ == "__main__":
    main(sys.argv[1:])
