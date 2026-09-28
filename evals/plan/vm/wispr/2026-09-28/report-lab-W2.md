# Test plan run — 2026-09-28 08:01

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 4

ElevenLabs: **530** credits used this month before the run, **9470** of 10000 left; cap 3000 → real cases allowed. Engine for the run: `whisper` (was `wispr`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 55732 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW1 | **PASS** | 66 | right ⌘⌥ held 3 s on Engine=Wispr stays one sentence: no 🧼 release before the real one, listening ≥ 2.5 s | held seen True; listening from 0.15 s for 2.4 s; release line before the case's cancel False; other cancel: None |
| TW2 | **PASS** | 2 | a stamped flagsChanged [] under a held right ⌘⌥ is not its release | the stamped tail was ignored; the pair stayed held |
| TW5 | **PASS** | 65 | while Wispr has no row and no microphone, the chip does not say Listening (or names the warming) | 39/39 samples listening while warming with no row; chip rows then: ['Opening Wispr Flow...', 'bind to send', '🎙️ Wispr Flow'] |
| TW7 | **PASS** | 73 | a cancelled / abandoned Wispr sentence leaves its WAV to Recover, no orphan file, no false 'nothing recorded' | (a) recoverable True, 'nothing had been recorded' False, wav 0→0; (b) recoverable True, wav 0→0; (c) 'the sentence is lost' False, recoverable True, wav 0→0 |

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
