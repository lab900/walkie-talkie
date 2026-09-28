# Test plan run — 2026-09-28 19:02

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 2 · ERROR 1 · PASS 4

ElevenLabs: credits unreadable (no ELEVENLABS_API_KEY); cap 3000 → cases that would spend real credits **SKIP**. Engine for the run: `whisper` (was `wispr`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 53817 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW4 | **BUG** | 128 | a cold Wispr: the first 3 s he says reach the witness; the chip names the warming | 17/540 samples listening+warming+no row (0.9 s); first-5-words hit 0/5; chip named it True; still listening at the stop False |
| TW8a | **BUG** | 25 | his own ptt sentence 1 s after the relay's lands at the caret, not in the witness or the outbox | outbox +1 (the relay's sentence is 1); rescue/drop line False; Wispr's own paste passed False |
| TW8b | **PASS** | 30 | his sentence 5 s after the relay's delivery (the 10 s tail) is Wispr's paste, no 🛡️ rescue | outbox +1 (the relay's sentence is 1); rescue/drop line False; Wispr's own paste passed True |
| TW11 | **PASS** | 65 | relay 🔼→ A (with a shot) then relay 🔽 B 0.3 s after A's stop, during A's settle: A in the witness, B delivered or held, never lost | outbox +1; 📦 lines 1; held False; witness 379 chars; lost-line False; B refused True (B refused out loud while A settles — not silent) |
| TW15 | **PASS** | 1 | with Wispr quit, 🔼↑ leaves no spawnPending and no folder menu; ⌘⌃D flashes 'not running' | spawnPending False; 'not running' True |
| TW20 | **PASS** | 89 | Wispr killed mid-sentence: listening/settling down within 0.6 s, a flash; the next 🔼→ delivers | down in 0.34 s (True); next sentence delivered True; capture False |
| TW32 | **ERROR** | 0 | in the relay's 10 s tail: a Wispr ⌘V with no newer row is the relay's (dropped, said so); once his newer row exists, his ⌘V passes (B / Q19) — never dropped silently | not started — relay busy for 600s: ["Wispr Flow's microphone open"] |

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
