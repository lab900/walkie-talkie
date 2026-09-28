# Test plan run — 2026-09-28 22:49

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 2 · PASS 5

ElevenLabs: credits unreadable (no ELEVENLABS_API_KEY); cap 3000 → cases that would spend real credits **SKIP**. Engine for the run: `whisper` (was `wispr`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 54256 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TX2 | **PASS** | 73 | Wispr killed 5 s into an 8 s sentence: Q14 delivers the relay's own recording once; relaunched, Wispr's mic stays closed for 30 s with no capture (no ghost) | listening down 0.61 s after the kill (True); 📦×0 -; copies 0.0 recall 0.00; rows +1 (); Q14 fallback; Recover staged; 0.0 s voiced; failure: The relay's recording got no audio from the microphone (Blac; clipboard writes 0; mic after 30 s closed |
| TX3 | **PASS** | 42 | relaunch Wispr, 🔼→ at once, stop: 30 s later wisprLive.micOpen is false with no capture; no /test/state answer slower than 2.5 s | relaunch 1.0 s; first sentence opened True, 📦×1 local-auto; copies 1.0 recall 1.00; rows +0 (); 1.7 s voiced; clipboard writes 1; mic with no capture first at never, at +30 s closed; state answers > 2.5 s: 0 (max 0.0 s) |
| TX6b | **PASS** | 61 | raw chords start/stop 0.4 s/start 0.2 s, 4 s speech, stop (state + wire): the second sentence's words delivered once, the first ends quietly, no stuck isRecording, no ghost mic | delivered once: 📦×1 local-forced; copies 1.0 recall 1.00; rows +2 (processing); 1.9 s voiced; clipboard writes 1; dwell-guard swallows 0; Wispr mic 10 s after closed |
| TX8a | **PASS** | 66 | his 61+60 held 6 s over speech, 🔼→ at +1.5 s: the relay refuses (or runs its own sentence to the witness); his words land in TextEdit once, never in the witness | relay opened False, refused True; his words: TextEdit 1.0 (recall 0.36), witness 0.0; 📦×0 -; copies 0.0 recall 0.00; rows +1 (formatted); refusal; clipboard writes 0 |
| TX8b | **BUG** | 50 | relay sentence, then his 61+60 sentence 0.3 s after its stop: relay's in the witness once, his at the caret once (Q19), nothing crossed | his sentence lost (W4; lab finding 3): relay: witness 1.0, TextEdit 0.0 · his: TextEdit 0.0, witness 0.0 · Q19 line False · drop line True; 📦×1 wispr-history; copies 1.0 recall 1.00; rows +1 (formatted); 2.0 s voiced; clipboard writes 1 |
| TX10 | **BUG** | 94 | 5 relay + 5 standalone sentences alternating, 2 s gaps: relay words only in the witness, his only in TextEdit; losses counted, 0 misroutes, 0 stuck | relay: 5 opened, 0 refused, witness 5.0/5, TextEdit 0.0 · his: TextEdit 0.0/5, witness 0.0 · losses relay 0 his 5; 📦×5 wispr-history,wispr-history,wispr-history,wispr-history,wispr-history; copies 5.0 recall 1.00; rows +10 (formatted); doubled text; 1.9 s voiced; clipboard writes 5 |
| TX13 | **PASS** | 109 | Wispr frozen with the row in flight: relay-restart.sh's gate holds; after cancel + restart + thaw, the late row is never delivered, the next sentence carries only its own words | gate held True; row 248 processing at the freeze; dry-run gate exit 3; restart exit 0; app pid 1598 → None; Wispr 3362 thawed; late row 248 → formatted (33 chars); stray deliveries after the restart before the next sentence none; old words in the witness after the restart 0.0 (before it 4.0); next: 📦×1 wispr-history; copies 1.0 recall 1.00; rows +2 (formatted); 1.6 s voiced; clipboard writes 1 |

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
