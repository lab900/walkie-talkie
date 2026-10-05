# Live caption band: local model vs ElevenLabs + Live

*5 Oct 2026. Victor: "poți compara A/B test cu Eleven Labs + Live". The local live caption
(`LocalLiveCaption`, the same day) against `scribe_v2_realtime`, on the same 12 dictations of his.*

## Set-up

- **Clips**: his 12 most recent corpus dictations of 15–55 s (6.6 min of audio, 4–5 Oct 2026,
  Romanian with English terms), `~/.walkie-talkie/voice-corpus/`.
- **Reference**: ElevenLabs batch `scribe_v1`, with word end times. Same vendor as one of the
  contestants, so if anything it favours ElevenLabs.
- **ElevenLabs + Live**: the app's own socket query (`pcm_16000`, VAD commit after 1.5 s, his 50
  keyterms, `ro` + secondary `en`), the WAV streamed **in real time** in 100 ms chunks. Band =
  committed segments + the open partial. The app's batch correction after 3 s of pause
  (`ElevenLabsLive.correctIfPaused`) is **not** modelled.
- **Local**: `LocalLiveCaption`'s policy replayed on a virtual clock with **real decode times** from
  a `whisper_helper.py` of its own with the app's weights (`whisper-turbo-victor`), idle GPU.
- **Metrics**: *lag* = when a reference word first shows on the band (difflib alignment) − when it
  ended in the audio; *shown* = share of reference words ever on the band; *WER* = the band at the
  end of the audio (+1.5 s) against the reference.

`python3 ab.py <wav>…` (the helper's python, which has `numpy` and `websockets`); raw runs go to
`runs/`, which is git-ignored: the repo is public and they hold his words.

## Result

| | lag p50 | lag p90 | WER, pooled | WER, median clip | shown | updates / clip |
|---|---|---|---|---|---|---|
| **ElevenLabs + Live** | **1.0 s** | **1.6 s** | 37 % | 31 % | 0.83 | 28 |
| **Local (LocalLiveCaption)** | 1.9 s | 2.8 s | **16 %** | **15 %** | **0.89** | 13 |

(Lag columns are the median over clips of each clip's p50 / p90.)

- **ElevenLabs is about twice as fast**, as it should be: it streams partials ~1/s, while the local
  band only moves at a pause (0.5 s) plus a decode (~0.9 s).
- **The local band is right more than twice as often.** Local WER was lower on 10 of the 12 clips.
  ElevenLabs' worst clips are not misheard words: the realtime model **switches to English and
  translates** his Romanian despite `language_code=ro`. On one clip the whole band read *"Perfect,
  all the dust is too opaque and it doesn't let me see what's under the mouse…"* (WER 0.97). On
  another the first sentence came out in English. In the app, the 3 s batch correction would
  later put those back, so these numbers understate what the band shows after a long pause.
- Per clip, ElevenLabs lag p50 ranged 0.8–1.2 s (one outlier at 3.0 s, the translated clip). Local
  lag p50 ranged 1.6–2.1 s.

## Not verified

- **The GPU while recording.** The local replay had an idle GPU. In the app the live helper shares
  it only with the halo, since the sentence's own decode starts after the close and the live window
  is killed there. That share is not measured.
- **The close.** A window still decoding at the stop is killed (`LocalWhisper.killNow`). The
  final decode's timing with and without a kill has not been measured in the app yet.
- **How it looks.** The local band rewrites its whole moving tail (often 10–20 s of text) at every
  pause, until a segment settles. That flicker has not been judged by eye.
- 12 clips, one speaker, one day's topics.
