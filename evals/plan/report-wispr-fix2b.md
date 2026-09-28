# Test plan run — 2026-09-28 10:05

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 2

ElevenLabs: **530** credits used this month before the run, **9470** of 10000 left; cap 3000 → real cases allowed. Engine for the run: `whisper` (was `eleven-live`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 60248 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW5 | **PASS** | 65 | while Wispr has no row and no microphone, the chip does not say Listening (or names the warming) | 42/42 samples listening while warming with no row; chip rows then: ['Opening Wispr Flow...', 'bind to send', '⌘⇧'] |
| TW14 | **PASS** | 11 | 🔼→ during Wispr's settle is refused on the chip (the wait named), not only in the log | second sentence opened False; chip named the wait True; refusal logged True |

ElevenLabs credits after the run: **530** — this run used **0** (ElevenLabs' daily buckets can lag by minutes; the dashboard is the final word).

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
