# Test plan run — 2026-09-29 03:17

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 1 · FAIL 1 · PASS 2

ElevenLabs: **2172** credits used this month before the run, **7828** of 10000 left; cap 3000 → real cases allowed. Engine for the run: `whisper` (was `eleven-live`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 57516 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW41 | **PASS** | 86 | F1: after a cancelled caret sentence, a bound relay sentence Wispr never answers (no row, no microphone) is NOT ended at 12 s — the relay's own recording carries it (listening, `ownTake`); his stop 🔼→ at ~15 s closes it and latches the witness; the Q14 answer lands in the witness via local-fallback, never at the caret | at 13 s: listening True, ownTake {'why': 'Wispr Flow did not answer the chord', 'for': 1.1202329397201538}; delivered before the stop False; delivery ('local-fallback', 'terminal:ttys000'); witness 265 chars; voiced 4.2 s; stuck line False; caret False |
| TW42 | **BUG** | 105 | item 3: Wispr quitting mid-sentence (fakeExit + its microphone closing) is not his stop — the relay's own recording goes on (`ownTake` ≤ 0.6 s), his stop closes it, the WHOLE take is decoded locally into the witness; the exit a beat after the close (≤ 0.3 s) is caught too; a close with Wispr alive still ends the sentence at once (control) | (a) held True in 0.04 s, listening 2 s on True, delivery ('local-fallback', 'terminal:ttys000'), voiced 4.3 s, witness 265 chars; (b) close then exit: held True, delivery ('local-fallback', 'terminal:ttys000'); (c) Wispr alive: closed False in 2.02 s, ownTake None, row delivered True — failed a,c |
| TW43 | **PASS** | 15 | item 5: Wispr's process exiting while the relay's words are in flight is told at once — the capture lets go ≤ 0.3 s after the exit (not at the next WAL commit / 1 s tick) and the take goes to Q14: `local-fallback → terminal`, before the auto p98 budget | capture let go 0.05 s after the exit; exit line True; delivery ('local-fallback', 'terminal:ttys000'); auto p98 fired first False; witness 223 chars |
| TA6 | **FAIL** | 79 | Wispr Flow's process 3 s old (faked age; the relay did not launch it) → a start on Engine = Wispr borrows the local model (`its process is 3.0 s old`), delivered via local-whisper into the witness; with the real (old) age the next start is Wispr's, not borrowed | borrow 🔁 Whisper (local) for this sentence — Wispr Flow is still starting (its process is 3.0 s old) (POST /test/loca; flash True; delivery ('local-whisper', 'terminal:ttys000'); witness 227 chars; real age: opened True, not borrowed False (processAge 18913.053703904152) |

ElevenLabs credits after the run: **2172** — this run used **0** (ElevenLabs' daily buckets can lag by minutes; the dashboard is the final word).

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
