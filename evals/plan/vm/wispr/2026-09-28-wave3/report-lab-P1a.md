# Test plan run — 2026-09-28 18:21

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 1 · PASS 9

ElevenLabs: credits unreadable (no ELEVENLABS_API_KEY); cap 3000 → cases that would spend real credits **SKIP**. Engine for the run: `whisper` (was `wispr`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 49228 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW1 | **BUG** | 69 | right ⌘⌥ held 3 s on Engine=Wispr stays one sentence: no 🧼 release before the real one, listening ≥ 2.5 s | held seen True; listening from 1.78 s for 0.9 s; release line before the case's cancel True; other cancel: None |
| TW2 | **PASS** | 2 | a stamped flagsChanged [] under a held right ⌘⌥ is not its release | the stamped tail was ignored; the pair stayed held |
| TW5 | **PASS** | 66 | while Wispr has no row and no microphone, the chip does not say Listening (or names the warming) | 43/43 samples listening while warming with no row; chip rows then: ['Opening Wispr Flow...', 'bind to send', '🎙️ Wispr Flow'] |
| TW6a | **PASS** | 85 | the relay's WAV reaches Recover; no orphan wispr-*.wav | recoverable True; 'nothing had been recorded' False; wispr-*.wav 2→2; lastFailure None |
| TW6b | **PASS** | 75 | the relay's WAV reaches Recover; no orphan wispr-*.wav | recoverable True; 'nothing had been recorded' False; wispr-*.wav 2→2; lastFailure None |
| TW6c | **PASS** | 61 | the relay's WAV reaches Recover; no orphan wispr-*.wav | recoverable False; 'nothing had been recorded' False; wispr-*.wav 2→2; lastFailure {'engine': 'wispr', 'why': 'Wispr Flow quit', 'at': '2026-09-28T18:47:50.578Z'}; local-fallback delivery True, witness 221 chars |
| TW6d | **PASS** | 61 | the relay's WAV reaches Recover; no orphan wispr-*.wav; no bare screenshot message | recoverable False; 'nothing had been recorded' False; wispr-*.wav 2→2; lastFailure {'engine': 'wispr', 'why': 'Wispr Flow quit', 'at': '2026-09-28T18:48:53.288Z'}; bare screenshot message False; local-fallback delivery True, witness 381 chars |
| TW7 | **PASS** | 73 | a cancelled / abandoned Wispr sentence leaves its WAV to Recover, no orphan file, no false 'nothing recorded' | (a) recoverable True, 'nothing had been recorded' False, wav 2→2; (b) recoverable True, wav 2→2; (c) 'the sentence is lost' False, recoverable True, wav 2→2 |
| TW9 | **PASS** | 7 | 🔼→ during his own Wispr sentence (his ptt held): 'one engine at a time', no chord posted | refused True; relay opened a sentence False |
| TW10 | **PASS** | 48 | a stop 1 s into a cold Wispr leaves no ghost dictation: no row with words, nothing delivered for 40 s | new row with words False; lastDelivery changed False; witness 0 chars |

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
