# Test plan run — 2026-09-29 01:37

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 1 · PASS 4

ElevenLabs: credits unreadable (no ELEVENLABS_API_KEY); cap 3000 → cases that would spend real credits **SKIP**. Engine for the run: `whisper` (was `wispr`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 51168 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW4 | **BUG** | 56 | a cold Wispr: the first 3 s he says reach the witness; the chip names the warming | 0/276 samples listening+warming+no row (0.0 s); first-5-words hit 0/5; chip named it False; still listening at the stop True |
| TX3 | **PASS** | 39 | relaunch Wispr, 🔼→ at once, stop: 30 s later wisprLive.micOpen is false with no capture; no /test/state answer slower than 2.5 s | relaunch 1.2 s; first sentence opened True, 📦×1 local-whisper; copies 1.0 recall 1.00; rows +0 (); clipboard writes 1; mic with no capture first at never, at +30 s closed; state answers > 2.5 s: 0 (max 0.0 s) |
| TX6b | **PASS** | 22 | raw chords start/stop 0.4 s/start 0.2 s, 4 s speech, stop (state + wire): the second sentence's words delivered once, the first ends quietly, no stuck isRecording, no ghost mic | delivered once: 📦×1 local-forced; copies 1.0 recall 1.00; rows +2 (formatted); 2.0 s voiced; clipboard writes 1; dwell-guard swallows 0; Wispr mic 10 s after closed |
| TX9 | **PASS** | 59 | 3 sentences each 1 s after a Wispr relaunch: all delivered with their head (first 5 words), or said why — losses counted | losses 0/3 (silent 0), head losses 0; <br>#0 opened True ok head-miss 1/5; 📦×1 local-whisper; copies 2.0 recall 0.48; rows +0 (formatted); clipboard writes 1<br>#1 opened True ok head-miss 1/5; 📦×1 local-whisper; copies 2.0 recall 0.48; rows +0 (formatted); clipboard writes 2<br>#2 opened True ok head-miss 1/5; 📦×1 local-whisper; copies 2.0 recall 0.48; rows +0 (formatted); clipboard writes 3 |
| TX13 | **PASS** | 170 | Wispr frozen with the row in flight: relay-restart.sh's gate holds; after cancel + restart + thaw, the late row is never delivered, the next sentence carries only its own words | gate held True; row 351 processing at the freeze; dry-run gate exit 3; restart exit 0; app pid 965 → None; Wispr 2638 thawed; late row 351 → formatted (33 chars); stray deliveries after the restart before the next sentence none; old words in the witness after the restart 0.0 (before it 3.0); next: 📦×1 local-fallback; copies 1.0 recall 1.00; rows +2 (formatted); Q14 fallback; 1.9 s voiced; failure: Wispr Flow will not finish row 352; clipboard writes 1 |

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
