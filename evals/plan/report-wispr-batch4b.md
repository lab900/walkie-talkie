# Test plan run — 2026-09-29 03:34

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 2

ElevenLabs: **2172** credits used this month before the run, **7828** of 10000 left; cap 3000 → real cases allowed. Engine for the run: `whisper` (was `eleven-live`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 61324 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW42 | **PASS** | 45 | item 3: Wispr quitting mid-sentence (fakeExit + its microphone closing) is not his stop — the relay's own recording goes on (`ownTake` ≤ 0.6 s), his stop closes it, the WHOLE take is decoded locally into the witness; the exit a beat after the close (≤ 0.3 s) is caught too; a close with Wispr alive still ends the sentence at once (control) | (a) held True in 0.04 s, listening 2 s on True, delivery ('local-fallback', 'terminal:ttys000'), voiced 4.4 s, witness 265 chars; (b) close then exit: held True, delivery ('local-fallback', 'terminal:ttys000'); (c) Wispr alive: closed True in 0.39 s, ownTake None, row delivered True |
| TA6 | **PASS** | 76 | Wispr Flow's process 3 s old (faked age; the relay did not launch it) → a start on Engine = Wispr borrows the local model (`its process is 3.0 s old`), delivered via local-whisper into the witness; with the real (old) age the next start is Wispr's, not borrowed | borrow 🔁 Whisper (local) for this sentence — Wispr Flow is still starting (its process is 3.0 s old) (POST /test/loca; flash True; delivery ('local-whisper', 'terminal:ttys000'); witness 227 chars; real age: opened True, not borrowed True (processAge 19280.726328849792) |

ElevenLabs credits after the run: **2172** — this run used **0** (ElevenLabs' daily buckets can lag by minutes; the dashboard is the final word).

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
