# Test plan run — 2026-09-28 16:12

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 3 · PASS 2

ElevenLabs: **1617** credits used this month before the run, **8383** of 10000 left; cap 3000 → real cases allowed. Engine for the run: `whisper` (was `wispr`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 52472 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW4 | **BUG** | 53 | a cold Wispr: the first 3 s he says reach the witness; the chip names the warming | 21/397 samples listening+warming+no row (1.1 s); first-5-words hit 0/5; chip named it True; still listening at the stop False |
| TW8a | **BUG** | 31 | his own ptt sentence 1 s after the relay's lands at the caret, not in the witness or the outbox | outbox +1 (the relay's sentence is 1); rescue/drop line False; Wispr's own paste passed False |
| TW11 | **PASS** | 77 | relay 🔼→ A (with a shot) then relay 🔽 B 0.3 s after A's stop, during A's settle: A in the witness, B delivered or held, never lost | outbox +1; 📦 lines 1; held False; witness 367 chars; lost-line False; B refused True (B refused out loud while A settles — not silent) |
| TW15 | **BUG** | 2 | with Wispr quit, 🔼↑ leaves no spawnPending and no folder menu; ⌘⌃D flashes 'not running' | spawnPending True; 'not running' True |
| TW20 | **PASS** | 44 | Wispr killed mid-sentence: listening/settling down within 0.6 s, a flash; the next 🔼→ delivers | down in 0.34 s (True); next sentence delivered True; capture False |

ElevenLabs credits after the run: **1682** — this run used **65** (ElevenLabs' daily buckets can lag by minutes; the dashboard is the final word).

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
