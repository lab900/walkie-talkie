# Test plan run — 2026-09-28 15:45

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 2 · ERROR 1 · PASS 2

ElevenLabs: **1617** credits used this month before the run, **8383** of 10000 left; cap 3000 → real cases allowed. Engine for the run: `whisper` (was `wispr`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 49256 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW12 | **BUG** | 65 | two Wispr sentences overlapping on an ungated path: both delivered, in spoken order | A at 10, B at -1 in the witness; 'No words came back' False |
| TW13 | **ERROR** | 130 | a Wispr sentence does not force-send a held panel being edited; A then B, in order | RuntimeError: fake row 1 was not adopted (captureRow 1)<br>Traceback (most recent call last):<br>  File "/Users/admin/wt-lab/evals/plan/harness.py", line 677, in run<br>    verdict, note = c["fn"]()<br>  File "/Users/admin/wt-lab/evals/plan/cases_wispr.py", line 572, in tw13<br>    rb = open_sentence(db); time.sleep(0.8)<br>RuntimeError: fake row 1 was not adopted (captureRow 1)<br> |
| TW14 | **PASS** | 13 | 🔼→ during Wispr's settle is refused on the chip (the wait named), not only in the log | second sentence opened False; chip named the wait True; refusal logged True |
| TW19 | **PASS** | 15 | /engine refused while listening / settling; accepted in state X with the swallow standing and nothing delivered | L: engine→wispr, source Wispr Flow; S: engine→wispr, source Wispr Flow; X: switched True, capture still open True (discarding True); late row delivered False |
| TW22 | **BUG** | 73 | a NULL row with no microphone behind it gives up within ~3 s of the close and the relay's own recording (≥ 1.5 s voiced) is transcribed by the local model and delivered (Q14), not a 30 s wait | gave up False 12.1 s after the stop; fallback line True; delivered True (223 chars, via local-fallback); 'No words came back' False |

ElevenLabs credits after the run: **1617** — this run used **0** (ElevenLabs' daily buckets can lag by minutes; the dashboard is the final word).

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
