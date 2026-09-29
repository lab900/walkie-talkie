# Test plan run — 2026-09-29 04:40

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 1 · FAIL 1 · PASS 3

ElevenLabs: credits unreadable (no ELEVENLABS_API_KEY); cap 3000 → cases that would spend real credits **SKIP**. Engine for the run: `whisper` (was `wispr`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 54042 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW4 | **BUG** | 20 | a cold Wispr: the first 3 s he says reach the witness; the chip names the warming | 0/152 samples listening+warming+no row (0.0 s); first-5-words hit 0/5; chip named it False; still listening at the stop True |
| TX3 | **PASS** | 38 | relaunch Wispr, 🔼→ at once, stop: 30 s later wisprLive.micOpen is false with no capture; no /test/state answer slower than 2.5 s | relaunch 0.4 s; first sentence opened True, 📦×1 local-whisper; copies 1.0 recall 1.00; rows +0 (); clipboard writes 1; mic with no capture first at never, at +30 s closed; state answers > 2.5 s: 0 (max 0.0 s) |
| TX6b | **FAIL** | 92 | raw chords start/stop 0.4 s/start 0.2 s, 4 s speech, stop (state + wire): the second sentence's words delivered once, the first ends quietly, no stuck isRecording, no ghost mic | the speech after the double chord was not delivered (said so, but lost): 📦×0 -; copies 0.0 recall 0.00; rows +2 (); Recover staged; 0.0 s voiced; failure: No words heard; clipboard writes 0; dwell-guard swallows 0; Wispr mic 10 s after OPEN |
| TX9 | **PASS** | 54 | 3 sentences each 1 s after a Wispr relaunch: all delivered with their head (first 5 words), or said why — losses counted | losses 0/3 (silent 0), head losses 0; <br>#0 opened True ok head-miss 1/5; 📦×1 local-whisper; copies 1.0 recall 0.48; rows +0 (); clipboard writes 1<br>#1 opened True ok head-miss 1/5; 📦×1 local-whisper; copies 1.0 recall 0.48; rows +0 (); clipboard writes 2<br>#2 opened True ok head-miss 1/5; 📦×1 local-whisper; copies 1.0 recall 0.48; rows +0 (); clipboard writes 3 |
| TX13 | **PASS** | 101 | Wispr frozen with the row in flight: relay-restart.sh's gate holds; after cancel + restart + thaw, the late row is never delivered, the next sentence carries only its own words | gate held True; row 487 processing at the freeze; dry-run gate exit 3; restart exit 0; app pid 6042 → None; Wispr 7379 thawed; late row 487 → formatted (33 chars); stray deliveries after the restart before the next sentence none; old words in the witness after the restart 0.0 (before it 1.5); next: 📦×1 wispr-history; copies 1.0 recall 1.00; rows +2 (formatted); 2.0 s voiced; clipboard writes 1 |

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
