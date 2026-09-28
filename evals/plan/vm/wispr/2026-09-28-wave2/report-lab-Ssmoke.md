# Test plan run — 2026-09-28 16:18

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

ERROR 1 · PASS 2

ElevenLabs: **1682** credits used this month before the run, **8318** of 10000 left; cap 3000 → real cases allowed. Engine for the run: `whisper` (was `wispr`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 53132 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TS2 | **ERROR** | 11 | 20 standalone sentences (Wispr's ptt 61+60, TextEdit in front): rows created, ≥ 95 % at the caret, 0 into the terminal | TextEdit would not open a document (osascript) |
| TS4 | **PASS** | 141 | 10 min idle: Wispr's mic never open (sampled every 30 s); then one relay sentence: row ≤ 12 s, delivered | idle 120 s, 4 samples · Wispr mic open in 0 (at []) · relay busy in 0 · Wispr pid(s) [4707] · then: row True (11.7 s after the gesture) · landed True · delivered True · via wispr-history · recall 0.82 · close→landed 5.5 s · start: mic closed · /tmp/wt-plan/soak-TS4-20260928-162119.json |
| TS5 | **PASS** | 214 | 10 relay sentences each 5 s after a Wispr relaunch: delivered ≥ 80 % (informational: W11 head loss, ghost mic) | 2/2 · delivered 2 (100.0 %) · truncated 0 · lost 0 (silent 0) · rows 1/2 (NULL 0) · via local-fallback 2 · recall mean 0.54 min 0.52 · close→landed p50 3.6 s p90 4.6 s · doubled 0 · stuck 1 · 154 s · head words missing (of 8) [1, 1], mean 1.0 · ghost mic after 1 sentence(s) [2] · relaunch→ready p50 5.7 s · relaunch failures 0 · /tmp/wt-plan/soak-TS5-20260928-162353.json<br>#01 relay speech12.wav row ✗ landed 3.6 s via local-fallback recall 0.57 head-missing 1<br>#02 relay speech12.wav row ✓ landed 4.6 s via local-fallback recall 0.52 STUCK head-missing 1 GHOST@0.1s |

ElevenLabs credits after the run: **1682** — this run used **0** (ElevenLabs' daily buckets can lag by minutes; the dashboard is the final word).

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
