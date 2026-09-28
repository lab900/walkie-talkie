# Test plan run — 2026-09-28 23:28

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 1 · PASS 4

ElevenLabs: **2172** credits used this month before the run, **7828** of 10000 left; cap 3000 → real cases allowed. Engine for the run: `whisper` (was `eleven-live`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 50456 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW35 | **BUG** | 86 | raw_transcript with no words ends the sentence at once (Q14 path, not an 8 s wait); `fallback` with words is delivered at once from the row (it used to be an unknown status → failure) | (a) raw_transcript empty: capture let go 0.05 s after the write, line True; (b) fallback: let go 0.04 s, witness True, via None, unknown-status line False |
| TW36 | **PASS** | 83 | the relay's row still `processing` when a newer row appears (his own dictation) is dead at once: the sentence ends through Q14 within ~1 s, no 'waiting on (Q2)', and Wispr's ⌘V is not held for 5 min | capture let go 0.04 s after the newer row; dead line True; late-row hold let go True; Q2 wait False; a later ⌘V: passed (past the relay's tail (Q9)) |
| TW37 | **PASS** | 65 | a cancel during the settle (the relay's own ⌃Escape) with the row still `processing`: the discard capture closes ~1 s after the dismiss, not at the 30 s capture timeout | discard capture closed 1.18 s after the cancel; line True |
| TW38 | **PASS** | 14 | WAL watch: every row change the capture reads is seen ≤ 50 ms after the fake's commit (Wispr's journal mode), woken by `flow.sqlite-wal`, not the 1 s tick | 6/6 changes seen; latency ms [33, 8, 16, 38, 16, 18] (max 38); watching ['flow.sqlite', 'flow.sqlite-wal']; file events +10, queries 45, cache hits 6702 |
| TW39 | **PASS** | 18 | a ⌘V dropped in the relay's tail while his newer row is still NULL: the pasteboard is read once and kept; the row's words win if they come, the pasteboard's only if they do not; never pasted twice | (a) ⌘V dropped; claim row 2 from the row (22 chars); (b) ⌘V dropped; claim row 4 from the pasteboard (the row still unfinished after 5 s) (21 chars); second ⌘V passed; dry claims of C 1; pasteboard reads 2 |

ElevenLabs credits after the run: **2172** — this run used **0** (ElevenLabs' daily buckets can lag by minutes; the dashboard is the final word).

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
