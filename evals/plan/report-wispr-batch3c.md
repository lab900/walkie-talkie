# Test plan run — 2026-09-29 00:35

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 3

ElevenLabs: **2172** credits used this month before the run, **7828** of 10000 left; cap 3000 → real cases allowed. Engine for the run: `whisper` (was `eleven-live`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 50179 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW22 | **PASS** | 23 | a NULL row with no microphone behind it gives up within ~3 s of the close and the relay's own recording (≥ 1.5 s voiced) is transcribed by the local model and delivered (Q14), not a 30 s wait | gave up True 3.3 s after the stop; fallback line True; delivered True (225 chars, via local-auto); 'No words came back' False |
| TW38 | **PASS** | 17 | WAL watch: every row change the capture reads is seen ≤ 50 ms after the fake's commit (Wispr's journal mode), woken by `flow.sqlite-wal`, not the 1 s tick | 6/6 changes seen; latency ms [-17506, 40, 19, 36, 6, 8] (max 40); watching ['flow.sqlite', 'flow.sqlite-wal']; file events +11, queries 20, cache hits 421 |
| TW39 | **PASS** | 19 | a ⌘V dropped in the relay's tail while his newer row is still NULL: the pasteboard is read once and kept; the row's words win if they come, the pasteboard's only if they do not; never pasted twice | (a) ⌘V dropped; claim row 2 from the row (22 chars); (b) ⌘V dropped; claim row 4 from the pasteboard (the row still unfinished after 5 s) (21 chars); second ⌘V passed; dry claims of C 1; pasteboard reads 2 |

ElevenLabs credits after the run: **2172** — this run used **0** (ElevenLabs' daily buckets can lag by minutes; the dashboard is the final word).

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
