# Test plan run — 2026-09-28 10:11

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 1

ElevenLabs: **530** credits used this month before the run, **9470** of 10000 left; cap 3000 → real cases allowed. Engine for the run: `whisper` (was `eleven-live`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 62116 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW22 | **PASS** | 18 | a NULL row with no microphone behind it gives up within ~3 s of the close and the relay's own recording (≥ 1.5 s voiced) is transcribed by the local model and delivered (Q14), not a 30 s wait | gave up True 3.3 s after the stop; fallback line True; delivered True (450 chars, via local-fallback); 'No words came back' False |

ElevenLabs credits after the run: **530** — this run used **0** (ElevenLabs' daily buckets can lag by minutes; the dashboard is the final word).

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
