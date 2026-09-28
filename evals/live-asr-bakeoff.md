# Live subtitle band: a local, bilingual RO+EN streaming recogniser

*28 Sep 2026. Question: which local engine can feed the live band while Victor dictates
(ElevenLabs `scribe_v2_realtime` is out of credits), in Romanian and English mixed inside one
sentence? The final transcript stays on the existing engines. This is only the band, so
latency and stability count for more than accuracy here.*

Machine: M1 Max, 64 GB, macOS 15.7.7. Nothing was installed. Every engine ran from
`voice-distill/.venv`, which already had parakeet-mlx 0.5.2, mlx-whisper 0.4.3, NeMo 3.0,
transformers 5.17 and torch 2.14. The only new download was the Nemotron weights, into the HF cache.
No walkie-talkie code was changed. `corpus.db` and the held-out set were only read.

## TL;DR

**Use Parakeet TDT 0.6B v3 (parakeet-mlx) and re-decode the whole utterance every 0.5 s.** It
is not true streaming, but one decode takes 0.13–0.2 s. On this test it showed the first word
0.7 s after speech started, and the text lagged the voice by 0.8 s at p50 and 2.6 s at p90. It
takes one language-free model for RO and EN, uses about 1 GB RSS plus about 2.4 GB of Metal
memory with a cache cap, and runs next to the Whisper helper at a 10–25 % cost.
Its weak point is the words themselves: 33 % WER on mixed RO+EN, 37 % on pure RO, and it
Romanian-ises or anglicises his English terms (9/27 hits).
Whisper turbo with LocalAgreement writes much better words (23 % on mixed, 21/27 terms), but it
keeps the GPU about 80 % busy. It showed 1.5–2.6 s of lag on an idle GPU and 3.7–6.5 s once
another process was using the GPU, and it sometimes loops or gets stuck.
**Nemotron 3.5 ASR streaming** is the only true cache-aware streaming model that lists Romanian,
and it runs on MPS through transformers. On Victor's voice it scores 44–46 % WER, both
streamed and offline, so it is not ready.

## Phase 1: what exists (checked online, 28 Sep 2026)

| candidate | RO? | streaming kind | runs on this Mac? | size / license | sources |
|---|---|---|---|---|---|
| **Parakeet TDT 0.6B v3** | yes, 1 of 25 EU languages, auto language detection | NeMo: chunked/buffered (`chunk_secs=2, right_context_secs=2`), not cache-aware. parakeet-mlx has `transcribe_stream` (local attention + rotating KV cache) | yes, **parakeet-mlx** | 0.6B, CC-BY-4.0; parakeet-mlx is Apache-2.0 | [card](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3), [parakeet-mlx](https://github.com/senstella/parakeet-mlx) |
| **Nemotron 3.5 ASR streaming 0.6B** | yes, in the "broad-coverage" tier; the card gives FLEURS ro-RO 25.9 % at 1.12 s chunks | **true cache-aware** RNNT, chunks 80 ms–1.12 s, `target_lang=auto` or a pinned locale | card lists NVIDIA GPUs only; **ran here on MPS via transformers ≥ 5.13** (measured below) | 0.6B, OpenMDW-1.1, not gated | [card](https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b) |
| Whisper (tiny…large-v3-turbo) | yes | none built in. whisper.cpp `stream` re-decodes a rolling window every `--step` ms and its own README calls it "naive". ufal whisper_streaming uses LocalAgreement (~2–3 s reported) | mlx-whisper and whisper.cpp (Metal) | MIT | [whisper.cpp stream](https://github.com/ggml-org/whisper.cpp/blob/master/examples/stream/README.md), [whisper_streaming](https://github.com/ufal/whisper_streaming) |
| WhisperKit (Argmax) | yes (Whisper) | the open-source core has no real-time streaming pipeline. The real-time WebSocket product is the paid Pro SDK | Swift, native | MIT core, Pro closed | [README](https://github.com/argmaxinc/WhisperKit/blob/main/README.md) |
| Canary-1B-v2 | yes (25 EU) | attention encoder-decoder, chunked long-form, no streaming mode found | NeMo only (CPU/MPS). No MLX port found | 1B, CC-BY-4.0 | [card](https://huggingface.co/nvidia/canary-1b-v2) |
| Jackrabbit 110M RO streaming | **RO only** | true cache-aware, ~1 s lookahead | NeMo; no Mac mention | CC-BY-**NC**-4.0 | [card](https://huggingface.co/surogate/jackrabbit-110m-ro-streaming) |
| SpeD ParakeetRo 110M | **RO only** | offline | NeMo CPU (ran here) | - | [repo](https://github.com/gabitza-tech/SpeD-RoASR) |
| Distil-Whisper (incl. large-v3.5) | **no**, English only | - | - | - | [card](https://huggingface.co/distil-whisper/distil-large-v3.5) |
| Moonshine v1/v2 | **no**, English only (v2 does stream) | - | - | - | [v2 paper](https://arxiv.org/abs/2602.12241) |
| Voxtral Realtime (Mistral) | **no**, not among its 13 languages | real streaming | no MLX port verified | 4B, Apache-2.0 | [Mistral](https://mistral.ai/news/voxtral-transcribe-2/) |
| Kyutai STT | **no** (en, en_fr) | real streaming | - | - | [repo](https://github.com/kyutai-labs/delayed-streams-modeling/) |
| Vosk / sherpa-onnx zipformer | **no Romanian model** (Vosk issue still open) | real streaming | - | - | [vosk #1963](https://github.com/alphacep/vosk-api/issues/1963), [sherpa](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/online-transducer/zipformer-transducer-models.html) |

Code-switching: no paper or benchmark on **Romanian–English** code-switched ASR was found for
any of these models. The only evidence is the mixed column below.

Claims that did not hold up: Parakeet v3's "streaming" means buffered re-decode, and the
parakeet-mlx streaming mode is broken on RO (see below). WhisperKit's real-time mode is the paid
tier. Distil-Whisper is English only. Moonshine, Voxtral Realtime, Kyutai and Vosk all stream,
but none of them does Romanian.

## Phase 2: bake-off on Victor's voice

**Clips.** 40 from the voice-distill held-out set, 5–20 s each, 7.8 min of audio in total, seed
20260928, drawn by the scratchpad script `pick.py`:
- **20 mixed**: RO clips with ≥ 3 English tech words from `~/.walkie-talkie/vocab.txt`. That is
  every eligible clip.
- **10 EN.** One of them is really mixed, but Wispr labelled it EN.
- **10 pure RO**, with no vocabulary words.

**Reference.** `ref_asr` (Wispr's raw recogniser). WER uses `eval/common.py` (`norm_words`,
`levenshtein`, `term_hits`) and is pooled over words. Wispr's raw text sometimes drops
diacritics, so a diacritics-folded WER was computed as well. It differs by ≤ 1.5 points on
every row, so it is not shown.

**Live simulation.** Audio arrives in 200 ms chunks on a virtual clock. Each step's real
compute time advances the clock, so a slow engine builds a backlog exactly as it would live.
- **Speech clock:** word end times from whisper large-v3 word timestamps on the full clip.
- **Lag:** the moment the displayed text first covers a word (prefix alignment), minus the
  moment that word ended in speech.
- **TTFW (time to first word):** the first non-empty display, minus speech onset.
- **Flicker:** words already on screen that a later update drops or changes (LCS), per 100
  final words.
- **Final after end:** how long after the audio ends the final text appears.

### Results (40 clips unless noted)

| engine / policy | streaming kind | WER all | mixed | EN | RO | terms | TTFW | lag p50 / p90 | flicker /100 w | step (compute) | RAM (RSS + Metal) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Parakeet v3, re-decode whole utterance / 0.5 s** | pseudo (full re-decode) | **28.9 %** | 33.0 % | **10.7 %** | 36.9 % | 9/27 | **0.67 s** | **0.76 / 2.59 s** | 173 | 0.13 s | 1.0 + 2.4 GB¹ |
| Parakeet v3, same + freeze words older than 2 s | pseudo, stable prefix | 32.0 % | 37.2 % | 13.8 % | 36.4 % | 7/27 | 0.71 s | 0.92 / 3.39 s | 73 | 0.21 s | same |
| Parakeet v3, same + freeze at 1.2 s | pseudo, stable prefix | 35.4 % | 39.6 % | 15.6 % | 45.1 % | 8/27 | 0.72 s | 0.90 / 3.45 s | 54 | 0.18 s | same |
| Whisper turbo, LocalAgreement-2, 1 s cadence, {ro,en} LID, vocabulary prompt, temp 0, loop guard | pseudo (LocalAgreement) | 24.7 % | **23.3 %** | 24.4 % | **29.7 %** | **21/27** | 3.84 s² | 3.71 / 6.47 s² | 36 | 2.0 s² | 2.1 GB RSS; Metal ≈2.4 GB capped (helper's own figure, not measured here)¹ |
| … same, first 11 mixed clips, **GPU still idle** (no loop guard) | | 20.5 % (mixed) | | | | 13/19 | 2.15 s | **1.47 / 2.55 s** | - | 0.83 s | |
| … same without loop guard / RO bias, 40 clips | | 67.3 % | 21.9 % | 64.4 % | 216.9 % | 21/27 | 2.97 s | 2.41 / 5.06 s | 120 | 1.34 s | |
| **Nemotron 3.5 streaming, ro-RO pinned, 1.12 s chunks** (transformers, MPS, fp32) | **true cache-aware** | 43.8 % | 47.8 % | 21.3 % | 56.9 % | 8/27 | 2.30 s | 1.77 / 6.89 s³ | **0** | 0.10 s | 0.7 + 3.3 GB |
| Nemotron, 560 ms chunks | true cache-aware | 46.0 % | 48.6 % | 29.8 % | 56.4 % | 8/27 | 1.73 s | 1.53 / 6.95 s | 0 | 0.08 s | same |
| SpeD RO 110M, re-decode / 0.5 s (NeMo, CPU): RO reference | pseudo, RO only | 48.8 % | 38.3 % | 93.8 % | **30.8 %** | 2/27 | 1.69 s | 1.64 / 6.08 s | 175 | 0.57 s (CPU) | 3.0 GB |
| parakeet-mlx `transcribe_stream` (256,256), 10 mixed clips | local attention + cache | **99.5 %** | | | | 0/17 | - | - | - | 0.14 s | - |

The same 40 clips transcribed **offline** (voice-distill's runs, plus Nemotron run here), for scale:

| offline | all | mixed | EN | RO |
|---|---|---|---|---|
| turbo-C | 14.7 | 15.0 | 8.4 | 21.0 |
| large-C | 15.7 | 13.4 | 20.4 | 17.4 |
| canary-v2 | 19.6 | 20.6 | 11.6 | 25.6 |
| parakeet-v3 | 28.9 | 33.0 | 10.7 | 36.9 |
| Nemotron | 46.4 | 49.0 | 27.6 | 60.0 |

The Parakeet re-decode ends on exactly its offline text, which serves as a sanity check.

¹ MLX's buffer pool grows without limit if nothing caps it. It reached 13.7 GB Metal peak for
Parakeet and 10 GB for Whisper. With `mx.set_cache_limit(256 MB)`, Parakeet peaks at 2.4 GB
with identical output. whisper_helper.py already caps its pool at 512 MB.

² **These timings are contaminated.** About 4 minutes into the first Whisper run, another
process started using the GPU. `ioreg` showed Device Utilization at 15–56 % while this run was
idle, and a VM process was at 228 % CPU. The same turbo 6 s decode went from 0.69 s to
1.5–2.7 s. The row marked "GPU still idle" is the only uncontended Whisper measurement.
Parakeet re-decode and both Nemotron runs finished before the contention started.

³ Nemotron's p90 comes from clips where it never prints the opening words. For example,
"Rulează Human Review Skill pe acest branch…" comes out as "și produima cel HML…". Offline it
does the same, so the cause is the model, not the harness.

### Running next to the Whisper helper

A stand-in for `whisper_helper.py` decoded 6 s of audio with turbo back to back while a
candidate streamed 10 mixed clips:

| | step | lag p50 / p90 | helper's decode |
|---|---|---|---|
| Parakeet re-decode alone | 0.20 s | 0.83 / 1.79 s | 0.97 s alone |
| Parakeet re-decode with helper | 0.24 s | 1.08 / 2.52 s | 1.07 s (+10 %) |
| Nemotron with helper | 0.17 s (was 0.10) | 2.29 s p50 | 0.94 s |

Both fit next to it comfortably. Whisper-LA against the helper would be two turbo models
competing for one GPU, and the contaminated rows above show what that does to its lag.

### Three mixed clips (final text, and what the band showed 4 s in)

| | "Scoate din Agents MD partea specifică de Java Coding Style și fă o skill în acest proiect cu commit push după" |
|---|---|
| Whisper-LA | Scoate din agents Partea specifică de Java Coding Style și fă o skill în acest proiect. Cu commit, push, după. · *@4s:* "Squat it." |
| Parakeet re-decode | Scoate din agents mod, partea specifică de Java Coding style și făo skill în acest proiect, cu cumit puși după. · *@4s:* "Scoate din Agenți Mâ, partea specifică." |
| Nemotron | Squate din Agent MD, partea specifică de Java Coding style și f-o skill în acest proiect cu comit puși după. · *@4s:* "Squate din Agent MD," |

| | "Rulează Human Review Skill pe acest branch și producem acel HTML cu diagrame imbricate" |
|---|---|
| Whisper-LA | Rulează Human Review skill pe acest branch și produc acel HTML cu diagome imbricate. · *@4s:* "Rulaf." |
| Parakeet re-decode | Ulează Human Review Skill pe acest branch și prodăm acel HTML cu diagrame imbricate. · *@4s:* "Rule of the human review skill pay at" |
| Nemotron | și produima cel HML cu diagramme imbricat. · *@4s:* (nothing) |

| | "Scoate din Victor skills skill-ul de grilling. Mai mult mă încurcă. Comet push pe GitHub" |
|---|---|
| Whisper-LA | Scoate din Victor's skills skill -ul de grilling, mă mânc, mă încurcă, commit, push, pe ghitul ăla. |
| Parakeet re-decode | Squatted in Victor Skills, Skill of the Grilling, Mamun Mâncurka. Commit puis pe ghitor. |
| Nemotron | Squated in Victor the grilling kurkă, commit push peggiora |

Parakeet's mid-sentence display switches language for a few words ("Rule of the human review
skill pay at…") until more Romanian context arrives, and then it corrects itself. That accounts
for most of its flicker.

## Recommendation and integration shape

**Parakeet TDT 0.6B v3 via parakeet-mlx, with the whole utterance re-decoded every 0.5 s.**
Freeze words that ended more than 2 s ago if the flicker is annoying on screen.
- **Why it wins:** lowest lag (0.8 s p50), a quick first word (0.7 s), and cheap compute
  (0.13–0.2 s per step), so the GPU stays free for the final Whisper pass. It also needs no
  language decision: it auto-detects on every decode and copes with RO+EN inside one sentence.
  The band's text is replaced by the final transcript anyway.
- **What it costs:** the words are worse than the final engine's (mixed 33 % vs turbo-C 15 %
  offline), and English terms often come out mangled.

Shape, as a sibling of `whisper_helper.py`: a `helpers/live_helper.py` daemon, one JSON object
per line each way, stdout reserved for protocol lines:

```
←  {"ready": true, "model": "mlx-community/parakeet-tdt-0.6b-v3"}
→  {"begin": "<dictation id>"}
→  {"pcm": "<base64 int16 LE, 16 kHz mono>"}        # ~200 ms per message, as captured
←  {"partial": "…", "frozen_words": 12}              # at most every 0.5 s, only if the text changed
→  {"end": "<dictation id>"}
←  {"final": "…"}                                    # one more decode over the whole buffer
```

- **Cadence:** re-decode when ≥ 0.5 s of new audio has arrived and the previous decode has
  finished. Never queue decodes; always take the newest audio, which is exactly what the
  simulation did.
- **Buffer:** the whole utterance. A decode stays around 0.2 s up to 20 s of audio. Past about
  30 s, drop audio before the last frozen word that is at least 20 s old (untested; parakeet's
  own long-audio mode uses local attention, and that mode is what broke streaming here).
- **Display:** frozen words in the normal colour and the tail in grey. A frozen word is one that
  ended more than 2 s before now (token timestamps come with `AlignedResult`).
- **Memory:** call `mx.set_cache_limit(256 MB)` at start-up. Without it the pool balloons to
  more than 13 GB.
- **Warm-up:** loading takes about 1 s, and the first decode compiles kernels. Decode 1 s of
  silence at `ready`.

If Victor would rather have the band show the right words than fast words, and can accept
1.5–2.5 s of lag on an otherwise idle GPU, the alternative is Whisper turbo with LocalAgreement
at a 1 s cadence. It needs {ro,en} LID with an RO bias, the vocabulary prompt, `temperature=0`
and a repetition guard. Even then, 1 of 40 clips got stuck on "Oh," after the guard cut a loop.

Don't use `transcribe_stream` in parakeet-mlx. With local attention it produces English-like
gibberish on his Romanian ("Um it's back Romagas one Monamin"). That held at (256,256),
(256,16) and (64,64), even though offline decoding of the same audio is fine. Nemotron is worth
watching (true streaming, zero flicker, 0.1 s steps) but is not usable at 44–60 % WER.

## Not verified

- **Timings under contention.** The Whisper-LA timings for 29 of 40 clips, parakeet
  freeze/window, and the concurrency test all ran with another process loading the GPU (15–56 %).
  Parakeet's steps barely moved, but its lag in the concurrency table has a noisy baseline.
- **Sample size.** 40 clips is a small sample, and the 20 mixed clips are every eligible one in
  the held-out set. One "EN" clip is actually mixed.
- **Speech clock.** Lag depends on large-v3 DTW word timestamps (error of a few hundred ms,
  not measured). On outputs with high WER, the prefix alignment behind "lag" is loose.
- **Real audio path.** Not tested: mic → AudioQueue → helper, VAD, silence, background noise,
  and utterances longer than 20 s.
- **How flicker looks on screen.** Not judged by eye.
- **Engines not run.** WhisperKit, whisper.cpp `stream`, ufal SimulStreaming, Canary live
  (offline it is 19.6 % on these clips, but at RTF 0.4 on NeMo CPU with no MLX port), and
  Jackrabbit streaming (RO only, non-commercial licence).
- **Nemotron setup.** Ran only in fp32 on MPS through transformers. bf16, the GGUF/C++ runtime,
  and `target_lang=auto` over all 40 clips were not tried. On 8 clips, auto mode produced
  Cyrillic on RO clips.
- **Parakeet streaming failure.** It could be specific to parakeet-mlx's local-attention path.
  NeMo's own buffered streaming script was not tried on the Mac.

Scripts and raw runs (virtual-clock simulator `sim.py`, scorer `score.py`, `runs/*.jsonl`) are in
this session's scratchpad and are not committed.
