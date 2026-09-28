# Test plan run — 2026-09-28 08:57

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 5 · PASS 4

ElevenLabs: **530** credits used this month before the run, **9470** of 10000 left; cap 3000 → real cases allowed. Engine for the run: `whisper` (was `eleven-live`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 58375 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW1 | **PASS** | 66 | right ⌘⌥ held 3 s on Engine=Wispr stays one sentence: no 🧼 release before the real one, listening ≥ 2.5 s | held seen True; listening from 0.16 s for 2.3 s; release line before the case's cancel False; other cancel: None |
| TW2 | **PASS** | 2 | a stamped flagsChanged [] under a held right ⌘⌥ is not its release | the stamped tail was ignored; the pair stayed held |
| TW5 | **PASS** | 5 | while Wispr has no row and no microphone, the chip does not say Listening (or names the warming) | 40/40 samples listening while warming with no row; chip rows then: ['Prompting to ￼ → ￼...', 'bind to send', '⌘⇧'] |
| TW7 | **BUG** | 8 | a cancelled / abandoned Wispr sentence leaves its WAV to Recover, no orphan file, no false 'nothing recorded' | (a) recoverable False, 'nothing had been recorded' True, wav 1944→1944; (b) recoverable False, wav 1944→1945; (c) not run — kills his Wispr: WT_ALLOW_WISPR_KILL=1 or the lab |
| TW12 | **BUG** | 43 | two Wispr sentences overlapping on an ungated path: both delivered, in spoken order | A at 32, B at -1 in the witness; 'No words came back' False |
| TW13 | **BUG** | 10 | a Wispr sentence does not force-send a held panel being edited; A then B, in order | A in the witness before its send True; panel held True; prompt text 'tw thirteen wispr bee' |
| TW14 | **BUG** | 8 | 🔼→ during Wispr's settle is refused on the chip (the wait named), not only in the log | second sentence opened False; chip named the wait False; refusal logged False |
| TW19 | **PASS** | 15 | /engine refused while listening / settling; accepted in state X with the swallow standing and nothing delivered | L: engine→wispr, source Wispr Flow; S: engine→wispr, source Wispr Flow; X: switched True, capture still open True (discarding True); late row delivered False |
| TW21 | **BUG** | 70 | after /test/dictation/start {clock} + cancel, a real sentence's marker cue is on the recorder's ruler | [eleven → fake Scribe] cue 1.38 s; wall-clock offset 1.38 s; recorder offset ≈ 1.22 s (±0.1) |

ElevenLabs credits after the run: **530** — this run used **0** (ElevenLabs' daily buckets can lag by minutes; the dashboard is the final word).

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 1 batch upload(s), 0 error(s) sent.
