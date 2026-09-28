# Test plan run — 2026-09-28 19:26

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 2 · PASS 2 · SKIP 1

ElevenLabs: credits unreadable (no ELEVENLABS_API_KEY); cap 3000 → cases that would spend real credits **SKIP**. Engine for the run: `whisper` (was `wispr`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 56725 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW1 | **BUG** | 65 | right ⌘⌥ held 3 s on Engine=Wispr stays one sentence: no 🧼 release before the real one, listening ≥ 2.5 s | held seen True; listening from 0.76 s for 2.0 s; release line before the case's cancel False; other cancel: None |
| TW32 | **PASS** | 13 | in the relay's 10 s tail: a Wispr ⌘V with no newer row is the relay's (dropped, said so); once his newer row exists, his ⌘V passes (B / Q19) — never dropped silently | idle True; relay's tail ⌘V dropped (the relay's tail (5.1 s after idle), no newer row of his seen); said relay's own True; his row 2 noted True; his ⌘V passed (row 2 is newer than the relay's — his own sentence); pass line True; still inside the tail window True |
| TW33 | **BUG** | 280 | sentence A's Wispr row never moves → Q14 local fallback; 🔼→ B 1 s into that decode: A is parked, not closed; both in the witness, A first; no 'which is over — dropped' | B opened True (row adopted True); A parked True; B refused False; A 494 chars before B at -1; 'dropped' False |
| TW34 | **PASS** | 154 | a relay sentence opened +1/+3/+5 s after a Wispr relaunch records the clip (≥ 1.5 s voiced, never DEAF, never 'No speech was heard'); any mid-take device change restarts the tap, logged | +1s: 2.2 s voiced (BlackHole 2ch: 74 buffers, peak 16366, 0 tap restart(s), 7.5 s); opened BlackHole 2ch 48000 Hz × 2; restarts 0; 'No speech' False \| +3s: 2.2 s voiced (BlackHole 2ch: 79 buffers, peak 16366, 0 tap restart(s), 8.0 s); opened BlackHole 2ch 48000 Hz × 2; restarts 0; 'No speech' False \| +5s: 2.1 s voiced (BlackHole 2ch: 71 buffers, peak 16345, 0 tap restart(s), 7.6 s); opened BlackHole 2ch 48000 Hz × 2; restarts 0; 'No speech' False |
| TN4 | **SKIP** | 2 | Scribe 401 → the local model decodes sentence A (45 s); a new sentence B 1 s into that decode parks A (D, wave 3): both delivered, A first, no 'which is over — dropped' | [eleven → fake Scribe] BlackHole 2ch pass-thru is dead (440 Hz check) — toggle the device in Loopback |

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
