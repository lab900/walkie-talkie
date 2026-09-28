# Test plan run — 2026-09-28 07:53

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 4 · PASS 3

ElevenLabs: **530** credits used this month before the run, **9470** of 10000 left; cap 3000 → real cases allowed. Engine for the run: `whisper` (was `wispr`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 54481 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW4 | **BUG** | 33 | a cold Wispr: the first 3 s he says reach the witness; the chip names the warming | 60/332 samples listening+warming+no row (3.0 s); first-5-words hit 0/5; chip named it True; still listening at the stop False |
| TW6c | **PASS** | 17 | the relay's WAV reaches Recover; no orphan wispr-*.wav | recoverable False; 'nothing had been recorded' False; wispr-*.wav 0→0; lastFailure {'why': 'Wispr Flow quit', 'engine': 'wispr', 'at': '2026-09-28T07:54:10.540Z'}; local-fallback delivery True, witness 456 chars |
| TW6d | **PASS** | 17 | the relay's WAV reaches Recover; no orphan wispr-*.wav; no bare screenshot message | recoverable False; 'nothing had been recorded' False; wispr-*.wav 0→0; lastFailure {'why': 'Wispr Flow quit', 'at': '2026-09-28T07:54:27.746Z', 'engine': 'wispr'}; bare screenshot message False; local-fallback delivery True, witness 758 chars |
| TW8a | **BUG** | 26 | his own ptt sentence 1 s after the relay's lands at the caret, not in the witness or the outbox | outbox +1 (the relay's sentence is 1); rescue/drop line False; Wispr's own paste passed False |
| TW9 | **PASS** | 7 | 🔼→ during his own Wispr sentence (his ptt held): 'one engine at a time', no chord posted | refused True; relay opened a sentence False |
| TW15 | **BUG** | 1 | with Wispr quit, 🔼↑ leaves no spawnPending and no folder menu; ⌘⌃D flashes 'not running' | spawnPending True; 'not running' True |
| TW20 | **BUG** | 32 | Wispr killed mid-sentence: listening/settling down within 0.6 s, a flash; the next 🔼→ delivers | down in 0.34 s (True); next sentence delivered False; capture False |

ElevenLabs credits after the run: **530** — this run used **0** (ElevenLabs' daily buckets can lag by minutes; the dashboard is the final word).

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
