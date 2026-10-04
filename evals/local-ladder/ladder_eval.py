import os, sys, json, time
H = os.path.expanduser("~/workspace/walkie-talkie/helpers/whisper_helper.py")
os.environ["RELAY_WHISPER_MODEL"] = os.path.expanduser("~/.walkie-talkie/models/whisper-turbo-victor")
from mlx_whisper.whisper import Whisper
ORIG = Whisper.decode
g = {"__name__": "helper", "__file__": H}
exec(compile(open(H).read().split("_install_ladder()\n\ntry:")[0] + "\n_install_ladder()\n", H, "exec"), g)
NEW = Whisper.decode
exec(open(os.path.join(os.path.dirname(__file__), "wer.py")).read(), g)
import mlx_whisper
temps = []
def counting(self, mel, options=None, **kw):
    temps.append(options.temperature); return ORIG(self, mel, options, **kw)

def shipped(samples, lang, prompt):
    """The helper as it was: mlx's ladder, keep the last rung, one no-prompt retry."""
    Whisper.decode = counting
    def dec(p):
        with g["quiet"]():
            return mlx_whisper.transcribe(samples, path_or_hf_repo=g["MODEL"], language=lang, initial_prompt=p,
                                          verbose=None, condition_on_previous_text=False)
    try:
        r = dec(prompt); first = g["_worst_ratio"](r)
        if first > g["LOOP_CEILING"]:
            r2 = dec(None)
            if g["_worst_ratio"](r2) < first: r = r2
        return r
    finally:
        Whisper.decode = NEW

def greedy(samples, lang, prompt):
    Whisper.decode = ORIG
    try:
        with g["quiet"]():
            return mlx_whisper.transcribe(samples, path_or_hf_repo=g["MODEL"], language=lang, initial_prompt=prompt,
                                          verbose=None, condition_on_previous_text=False, temperature=0.0)
    finally:
        Whisper.decode = NEW

rows = [json.loads(l) for l in open(os.path.expanduser("~/.walkie-talkie/voice-corpus/corpus.jsonl"))]
rows = [r for r in rows if r.get("asr") and r.get("text")][-int(sys.argv[1]):]
out = open(sys.argv[2], "a")
for i, row in enumerate(rows):
    wav = os.path.expanduser("~/.walkie-talkie/voice-corpus/" + row["wav"])
    if not os.path.exists(wav): continue
    samples = g["A"].load_audio(wav); lang = g["pick_language"](samples)
    prompt = g["VOCABULARY_RO"] if lang == "ro" else g["VOCABULARY"]
    ref = g["tokens"](row["text"])
    temps.clear(); t0 = time.monotonic(); a = shipped(samples, lang, prompt); ta = time.monotonic() - t0
    fired = any(t > 0 for t in temps)
    rec = {"id": row["id"], "dur": round(len(samples) / 16000, 1), "fired": fired,
           "A": {"s": round(ta, 2), "cr": round(g["_worst_ratio"](a), 1), "wer": round(g["wer"](ref, g["tokens"](a["text"])), 3)}}
    if fired or rec["A"]["cr"] > 2.4:
        rec["ref"] = row["text"][:300]; rec["A"]["text"] = a["text"][:300]
        t0 = time.monotonic(); b = g["transcribe"](wav, words=False); tb = time.monotonic() - t0
        rec["B"] = {"s": round(tb, 2), "cr": round(g["_worst_ratio"](b), 1), "cut": b.get("cut", 0),
                    "wer": round(g["wer"](ref, g["tokens"](b["text"])), 3), "text": b["text"][:300]}
        t0 = time.monotonic(); c = greedy(samples, lang, prompt); tc = time.monotonic() - t0
        rec["C"] = {"s": round(tc, 2), "cr": round(g["_worst_ratio"](c), 1),
                    "wer": round(g["wer"](ref, g["tokens"](c["text"])), 3), "text": c["text"][:300]}
    out.write(json.dumps(rec, ensure_ascii=False) + "\n"); out.flush()
    print(i, rec["id"], rec["fired"], file=sys.stderr, flush=True)
