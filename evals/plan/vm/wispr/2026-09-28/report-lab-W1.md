# Test plan run — 2026-09-28 07:17

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 7 · PASS 6 · SKIP 3

ElevenLabs: **530** credits used this month before the run, **9470** of 10000 left; cap 3000 → real cases allowed. Engine for the run: `whisper` (was `wispr`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 50217 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW3 | **SKIP** | 0 | standalone OFF, right ⌘⌥ held 2 s: a Wispr row within 1 s, or a flash — never a 12 s ring | needs Q9 standalone OFF (state.wisprStandalone) |
| TW4 | **BUG** | 108 | a cold Wispr: the first 3 s he says reach the witness; the chip names the warming | 40/309 samples listening+warming+no row (2.0 s); first-5-words hit 0/5; chip named it False |
| TW6a | **PASS** | 74 | the relay's WAV reaches Recover; no orphan wispr-*.wav | recoverable True; 'nothing had been recorded' False; wispr-*.wav 0→0; lastFailure None |
| TW6b | **PASS** | 72 | the relay's WAV reaches Recover; no orphan wispr-*.wav | recoverable True; 'nothing had been recorded' False; wispr-*.wav 0→0; lastFailure None |
| TW6c | **BUG** | 73 | the relay's WAV reaches Recover; no orphan wispr-*.wav | recoverable False; 'nothing had been recorded' False; wispr-*.wav 0→1; lastFailure {'why': 'Wispr Flow quit', 'engine': 'wispr', 'at': '2026-09-28T07:39:07.869Z'} |
| TW6d | **BUG** | 21 | the relay's WAV reaches Recover; no orphan wispr-*.wav; no bare screenshot message | recoverable False; 'nothing had been recorded' False; wispr-*.wav 0→0; lastFailure {'at': '2026-09-28T07:44:23.266Z', 'why': 'Wispr Flow quit', 'engine': 'wispr'}; bare screenshot message False |
| TW7 | **PASS** | 74 | a cancelled / abandoned Wispr sentence leaves its WAV to Recover, no orphan file, no false 'nothing recorded' | (a) recoverable True, 'nothing had been recorded' False, wav 0→0; (b) recoverable True, wav 0→0; (c) 'the sentence is lost' False, recoverable True, wav 0→0 |
| TW8a | **BUG** | 26 | his own ptt sentence 1 s after the relay's lands at the caret, not in the witness or the outbox | outbox +1 (the relay's sentence is 1); rescue/drop line True; Wispr's own paste passed False |
| TW8b | **PASS** | 29 | his sentence 5 s after the relay's delivery (the 10 s tail) is Wispr's paste, no 🛡️ rescue | outbox +1 (the relay's sentence is 1); rescue/drop line False; Wispr's own paste passed True |
| TW9 | **BUG** | 7 | 🔼→ during his own Wispr sentence (his ptt held): 'one engine at a time', no chord posted | refused False; relay opened a sentence False |
| TW10 | **PASS** | 47 | a stop 1 s into a cold Wispr leaves no ghost dictation: no row with words, nothing delivered for 40 s | new row with words False; lastDelivery changed False; witness 0 chars |
| TW11 | **SKIP** | 0 | two overlapping Wispr sentences: A with its own shot in the witness, B delivered or held, never lost | needs Q9 standalone OFF (state.wisprStandalone) |
| TW15 | **BUG** | 1 | with Wispr quit, 🔼↑ leaves no spawnPending and no folder menu; ⌘⌃D flashes 'not running' | spawnPending True; 'not running' True |
| TW16 | **SKIP** | 0 | only Wispr's helper alive: ⌘⌃D says 'not running', never 'the sentence is lost' | no helper survived the main process |
| TW17 | **PASS** | 47 | a Wispr corpus row is written only when Wispr's micDevice is the relay's device | new wispr corpus rows 0; micOpened {'at': '2026-09-28T07:51:40.152Z', 'rate': 48000, 'device': 'BlackHole 2ch', 'channels': 2}; Wispr's mic [] |
| TW20 | **BUG** | 33 | Wispr killed mid-sentence: listening/settling down within 0.6 s, a flash; the next 🔼→ delivers | down in 0.66 s (True); next sentence delivered False; capture False |

ElevenLabs credits after the run: **530** — this run used **0** (ElevenLabs' daily buckets can lag by minutes; the dashboard is the final word).

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
