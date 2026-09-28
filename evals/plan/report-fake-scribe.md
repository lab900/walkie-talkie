# Test plan run — 2026-09-28 07:15

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

FAIL 2 · PASS 10

ElevenLabs: **10033** credits used this month before the run, **-33** of 10000 left; cap 3000 → cases that would spend real credits **SKIP**. Engine for the run: `whisper` (was `eleven-live`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 49539 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| LC1 | **PASS** | 3 | first word enters letter by letter, centred (2026-09-27, 84d420e): reveal grows monotonically and the word is fully revealed (reveal null) within 1.2 s; \|centre − bandWidth/2\| < 3 on every sample; anchor \|velocity\| and the entry front ≤ 320 pt/s; first opacity < 0.1, settled 0.4 ± 0.03 (provisional); never anchor ≥ bandWidth − 5 | reveal 0 pt at +0.01 s → in at +0.88 s (front median 327 pt/s over 15 samples); centre off ≤ 0.00 pt; max \|velocity\| 99; opacity 0 → 0.4; bandWidth 1728 |
| LC2 | **PASS** | 22 | growth at 0.4 s/word for 20 s: centre ±80 until line > bandWidth − 96, then anchor + shownWidth ≤ bandWidth − 48 + 2; \|Δanchor\| ≤ 700·Δt + 2; anchor rises only by a drop | 167 samples, wide from t=6.6, max centre offset 0.0 pt while narrow, dropped 31, max velocity 483 |
| LC3 | **PASS** | 10 | pause: velocity → 0 within 1.5 s of the last word, centre unchanged until the eraser starts at 5.0 s | eraser at +5.10 s, max velocity 0.0 pt/s and centre drift 0.00 pt in [+1.5 s, eraser), velocity exactly 0 from +1.22 s |
| LC9 | **FAIL** | 20 | append-only ×30 at 2 words/s (letter by letter since 84d420e): corrections 0; per word, reveal grows monotonically, the word starts at opacity < 0.1 and is fully revealed within 1.2 s of its append; centre ±10 pt while the line is narrower than bandWidth − 96; anchor \|velocity\| ≤ 320 pt/s; entry front ≤ 0.7 vMax (490, the catch-up cap) | 10 word(s) slower than 1.2 s to be fully revealed: [(5, 1.34), (13, 1.35), (14, 1.34)] — corrections 0; slowest full reveal 1.64 s over 30/30 words; first opacity max 0.02; front median 273 pt/s, 29/278 steps over 320 (+15 %, catch-up); centre off ≤ 0.0 pt over 96 narrow samples; max \|velocity\| 320 |
| TL29 | **PASS** | 19 | live socket drop mid-sentence (fault live:drop) → ≤ 1 'send failed' line (today ~11/s); batch still delivers | [eleven-live → fake Scribe] drop injected True, 1 'send failed' lines (~0.1/s over ~8 s), batch via elevenlabs-scribe |
| TL30 | **PASS** | 13 | live socket that never opens (live:never-open stands in for no key) → the band never opens, `pending` stays ≤ 64; the batch delivers (was: band open and empty the whole sentence, `pending` unbounded — §3.14, F13) | [eleven-live → fake Scribe] band open 0/26 samples, max words 0, socket {'connecting'}, pending [0] → [64], batch via elevenlabs-scribe |
| LC13 | **PASS** | 14 | live integration: band words > 0 while isRecording; the band closes when listening goes false | [eleven-live → fake Scribe] max band words while recording 11; after stop: listening false at 0.069 s, band closed at 0.069 s |
| B1 | **PASS** | 12 | first live caption word ≤ 2 s after speech starts in the recording (plan: ≤ 1.5 s) | [eleven-live → fake Scribe] first band word 0.33 s after the speech in the recording (onset 1.8 s into it); 1.18 s by the old clock (play() + 0.5); cold, caught up 1 chunk(s) at session open; handshake 0.31 s (upgrade 0.00 s) on its own URLSession; chunks 21 |
| B2 | **PASS** | 12 | a VAD commit → '💬 live correction: … → scribe_v2', live.corrections ≥ 1, elevenCost.total grows, band corrections ≥ 0 | [eleven-live → fake Scribe] correction started True, applied True (0.32 s), live.corrections 1, cost 0.39408 → 0.39445, band corrections 0 words 11 |
| B3 | **PASS** | 19 | stop while a correction is in flight (500 after 4 s, then the real retry) → no update after close, no crash (pid unchanged), the sentence delivers | [eleven-live → fake Scribe] fault taken True, retry after close True, correction applied after close False, pid 25001 → 25001, delivered via elevenlabs-scribe (no discard line exists in the code) |
| B4 | **PASS** | 20 | correction failure (500 ×2, the call and its retry) → 'after 5 s' hold, cut unchanged, the next upload ≥ 5 s later covers the longer span | [eleven-live → fake Scribe] hold 5.35 s, cut after the failure 0, spans [6.2, 12.4] |
| B5 | **FAIL** | 222 | elevenCost.total grows by (live s × 0.39 × (1 + 0.2 with keyterms) + batch s × 0.22)/3600 (±25 %) | [eleven-live → fake Scribe] Δ $0.000350 vs expected $0.000348 (recording 0.0 s, corrections 5.7 s, keyterms 50); label $0.40 → $0.40 |

ElevenLabs credits after the run: **10033** — this run used **0** (ElevenLabs' daily buckets can lag by minutes; the dashboard is the final word).

Fake Scribe: 8 live session(s), 2054 chunks (204.531 s), 80 partials, 5 commits, 12 batch upload(s), 0 error(s) sent.

B5 rerun 2026-09-28 07:5x (alone, fake Scribe): **PASS** — Δ $0.001849 vs expected $0.001876 (recording 7.8 s, corrections 6.3 s, keyterms 50). The FAIL above lost its stop chord: the tap was blind at 07:18–07:20 (Secure Input, fixed/diagnosed in 84ea080), not the fake.
