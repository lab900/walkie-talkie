# Test plan run — 2026-09-29 03:40

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 1 · PASS 7

ElevenLabs: **2172** credits used this month before the run, **7828** of 10000 left; cap 3000 → real cases allowed. Engine for the run: `whisper` (was `eleven-live`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 62603 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW22 | **PASS** | 20 | a NULL row with no microphone behind it gives up within ~3 s of the close and the relay's own recording (≥ 1.5 s voiced) is transcribed by the local model and delivered (Q14), not a 30 s wait | gave up True 3.1 s after the stop; fallback line True; delivered True (225 chars, via local-auto); 'No words came back' False |
| TW32 | **PASS** | 7 | in the relay's 10 s tail: a Wispr ⌘V with no newer row is the relay's (dropped, said so); once his newer row exists, his ⌘V passes (B / Q19) — never dropped silently | idle True; relay's tail ⌘V dropped (the relay's tail (2.4 s after idle), no newer row of his seen); said relay's own True; his row 2 noted True; his ⌘V passed (row 2 is newer than the relay's — his own sentence); pass line True; still inside the tail window True |
| TW35 | **PASS** | 86 | raw_transcript with no words ends the sentence at once (Q14 path, not an 8 s wait); `fallback` with words is delivered at once from the row (it used to be an unknown status → failure) | (a) raw_transcript empty: capture let go 0.07 s after the write, line True; (b) fallback: let go 0.07 s, witness True, via wispr-history, unknown-status line False |
| TW36 | **PASS** | 83 | the relay's row still `processing` when a newer row appears (his own dictation) is dead at once: the sentence ends through Q14 within ~1 s, no 'waiting on (Q2)', and Wispr's ⌘V is not held for 5 min | capture let go 0.04 s after the newer row; dead line True; late-row hold let go True; Q2 wait False; a later ⌘V: passed (past the relay's tail (Q9)) |
| TW37 | **PASS** | 67 | a cancel during the settle (the relay's own ⌃Escape) with the row still `processing`: the discard capture closes ~1 s after the dismiss, not at the 30 s capture timeout | discard capture closed 1.20 s after the cancel; line True |
| TW38 | **PASS** | 16 | WAL watch: every row change the capture reads is seen ≤ 50 ms after the fake's commit (Wispr's journal mode), woken by `flow.sqlite-wal`, not the 1 s tick | 6/6 changes seen; latency ms [35, 19, 13, 7, 12, 18] (max 35); watching ['flow.sqlite', 'flow.sqlite-wal']; file events +13, queries 100, cache hits 14121 |
| TW39 | **BUG** | 24 | a ⌘V dropped in the relay's tail while his newer row is still NULL: the pasteboard is read once and kept; the row's words win if they come, the pasteboard's only if they do not; never pasted twice | (a) ⌘V dropped; claim row None from None (None chars); (b) ⌘V dropped; claim row None from None (None chars); second ⌘V dropped; dry claims of C 0; pasteboard reads 0 |
| TW40 | **PASS** | 27 | A's Wispr row never moves → Q14 local decode, parked by B; B's row formatted BEFORE A's decode ends: when A is delivered, B follows at once — both in the witness, A first; no 'wait for the one before' past A | helper stopped True; B waited its turn True; B in the witness True 6.2 s after the resume; A 254 chars before B at 255; 'wait for the one before' ×0; dropped False; queue after the resume [] |

ElevenLabs credits after the run: **2172** — this run used **0** (ElevenLabs' daily buckets can lag by minutes; the dashboard is the final word).

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
