# Re-run the helper as it is now (D) on the clips where the old ladder fired.
import os, sys, json, time
H = os.path.expanduser("~/workspace/walkie-talkie/helpers/whisper_helper.py")
os.environ["RELAY_WHISPER_MODEL"] = os.path.expanduser("~/.walkie-talkie/models/whisper-turbo-victor")
g = {"__name__": "helper", "__file__": H}
exec(compile(open(H).read().split("_install_ladder()\n\ntry:")[0] + "\n_install_ladder()\n", H, "exec"), g)
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "wer.py")).read(), g)
rows = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.expanduser("~/.walkie-talkie/voice-corpus/corpus.jsonl"))}
extra = [l.strip() for l in open(sys.argv[2])] if len(sys.argv) > 2 else []
for l in open(sys.argv[1]):
    r = json.loads(l)
    if "B" not in r: continue
    row = rows[r["id"]]; wav = os.path.expanduser("~/.walkie-talkie/voice-corpus/" + row["wav"])
    t0 = time.monotonic(); d = g["transcribe"](wav, words=False); td = time.monotonic() - t0
    r["D"] = {"s": round(td, 2), "cr": round(g["_worst_ratio"](d), 1), "cut": d.get("cut", 0),
              "wer": round(g["wer"](g["tokens"](row["text"]), g["tokens"](d["text"])), 3), "text": d["text"][:300]}
    print(json.dumps(r, ensure_ascii=False), flush=True)
for wav in extra:  # unlabelled looped clips: time and text only
    for words in (False, True):
        t0 = time.monotonic(); d = g["transcribe"](wav, words=words); td = time.monotonic() - t0
        print(json.dumps({"wav": wav, "words": words, "s": round(td, 2), "cr": round(g["_worst_ratio"](d), 1),
                          "cut": d.get("cut", 0), "text": d["text"][:400]}, ensure_ascii=False), flush=True)
