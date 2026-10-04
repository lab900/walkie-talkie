# The temperature ladder, and why it now climbs only on a loop (2026-10-04)

Trigger: 16:28:10, a 90 s take decoded in **32.6 s** (predicted 2.4 s) and came back with
669 × "AM" (`cr 39.3`). Replayed: a near-silent window decoded fine at T=0 (cr 0.7) but under
`avg_logprob` −1.0, so mlx_whisper climbed 0.2…1.0 and kept the **last** rung — the 1.0 one,
which looped for 224 tokens. The relay's no-prompt retry then climbed the same ladder again.

Correlation, from `~/.walkie-talkie/decode-rate.jsonl` (warm, local): 549 normal decodes at a
median **0.096×** the audio, 5 looped ones at **0.36×**.

## Configs

- **A** — as shipped until today: mlx's ladder (0.0…1.0, climb on cr > 2.4 *or* logprob < −1,
  keep the last rung) + one no-prompt retry on a loop.
- **C** — greedy only, `temperature=0.0`.
- **D** — shipped now: `_install_ladder` in `helpers/whisper_helper.py` — greedy, climb to 0.2 /
  0.4 **only when the rung loops**, keep the least looped; then the retry; then `cut_loops`.

## Pass 1 — `ladder_eval.py` (`pass1-313-clips.jsonl`)

The newest 313 of the 1,269 Wispr-labelled corpus clips (`asr` present, `text` = reference),
model `whisper-turbo-victor`, words off. Stopped at 313 (≈ 85 min for all): the ladder fired on
9 (2.9 %), and on a clip where it does not fire D is byte-for-byte A by construction (both keep
the greedy rung of every window).

## Pass 2 — `fired_eval.py` (`pass2-fired-and-looped.jsonl`)

| over the 9 fired clips | total decode | looped | mean WER (capped 1.5) |
|---|---|---|---|
| A (old) | **111.9 s** | 8 | 1.283 |
| C (greedy) | 10.7 s | 2 | 0.793 |
| D (new) | **21.0 s** | **0** | **0.659** |

A loops on 8 of the 9 clips it climbs on: once the ladder fires, it nearly always ends in a
loop. C is fastest but keeps a greedy loop twice (`c304b2e1` cr 8.7, `8b3852c8` cr 11.8) — the
two clips where climbing is worth it.

The 12 local decodes with `compression > 2.4` in `decode-rate.jsonl` (2026-09-16 → today),
re-decoded with D: **none loops**, 1.1–3.3 s plain, 1.7–5.8 s with words (today's: 32.6 s live → 3.3 s).
`cut_loops` did not fire once on either pass — it is the backstop for a loop every rung keeps.

`pass1-…jsonl`'s `B` is an intermediate version (the ladder kept its logprob climb, stopped on
a loop): no loops, but 3–8 s a clip for the same words as C, which is why D dropped that climb.
`ladder_eval.py` now runs D in that slot, since it execs the helper as it is.
