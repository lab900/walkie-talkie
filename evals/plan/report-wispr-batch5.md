# Test plan run — 2026-09-29 06:43

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 3

ElevenLabs: **2172** credits used this month before the run, **7828** of 10000 left; cap 3000 → real cases allowed. Engine for the run: `whisper` (was `eleven-live`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 58348 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW42 | **PASS** | 51 | item 3: Wispr quitting mid-sentence (fakeExit + its microphone closing) is not his stop — the relay's own recording goes on (`ownTake` ≤ 0.6 s), his stop closes it, the WHOLE take is decoded locally into the witness; the exit a beat after the close (inside the grace) is caught too; a close with Wispr alive still ends the sentence when the 1.0 s grace runs out (control) | (a) held True in 0.04 s, listening 2 s on True, delivery ('local-fallback', 'terminal:ttys000'), voiced 4.4 s, witness 265 chars; (b) close then exit: held True, delivery ('local-fallback', 'terminal:ttys000'); (c) Wispr alive: closed True in 1.15 s, ownTake None, row delivered True |
| TW44 | **PASS** | 65 | batch 5: the real kill's order — the 100 ms POLL sees Wispr's microphone close FIRST and the exit comes 0.15 / 0.3 / 0.4 s later: held (`ownTake`), the phase never left listening (no `listening → transcribing — the 100 ms poll`), his stop after the clip → the WHOLE take `local-fallback → terminal` (≥ 3 s voiced); control: the poll's close with Wispr alive closes at the 1.0 s grace, no hold | (a) exit 0.15 s after the poll's close: held True 0.24 s after the close, grace line True, phase moved by the poll False, listening 1.5 s on True, delivery ('local-fallback', 'terminal:ttys000'), voiced 4.2 s, witness 265 chars; (b) exit 0.30 s after the poll's close: held True 0.37 s after the close, grace line True, phase moved by the poll False, listening 1.5 s on True, delivery ('local-fallback', 'terminal:ttys000'), voiced 4.4 s, witness 265 chars; (c) exit 0.40 s after the poll's close: held True 0.46 s after the close, grace line True, phase moved by the poll False, listening 1.5 s on True, delivery ('local-fallback', 'terminal:ttys000'), voiced 4.5 s, witness 265 chars; (d) Wispr alive: closed True in 1.13 s (outlived line True), ownTake None, row delivered True |
| TW43 | **PASS** | 13 | item 5: Wispr's process exiting while the relay's words are in flight is told at once — the capture lets go ≤ 0.3 s after the exit (not at the next WAL commit / 1 s tick) and the take goes to Q14: `local-fallback → terminal`, before the auto p98 budget | capture let go 0.07 s after the exit; exit line True; delivery ('local-fallback', 'terminal:ttys000'); auto p98 fired first False; witness 266 chars |

ElevenLabs credits after the run: **2172** — this run used **0** (ElevenLabs' daily buckets can lag by minutes; the dashboard is the final word).

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
