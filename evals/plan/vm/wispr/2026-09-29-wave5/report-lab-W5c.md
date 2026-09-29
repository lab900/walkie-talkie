# Test plan run — 2026-09-29 01:43

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 1 · PASS 1

ElevenLabs: credits unreadable (no ELEVENLABS_API_KEY); cap 3000 → cases that would spend real credits **SKIP**. Engine for the run: `whisper` (was `wispr`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 52006 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TQ2 | **BUG** | 78 | Wispr SIGKILLed 3 s into the sentence: the relay's own audio decoded locally, delivered once, close→words a few seconds; the next start does not wait for Wispr | nothing delivered, said so (Recover / failure / refusal); SEC TQ2 close→words - s via - budget 2.2 (100 samples on wispr-flow) fired no voiced 0.0 DEAF; 📦×0 -; copies 0.0 recall 0.00; rows +1 (); Q14 fallback; Recover staged; 0.0 s voiced; failure: The relay's recording got no audio from the microphone (Blac; clipboard writes 0 \|\| next: SEC TQ2.next close→words 1.35 s via local-whisper budget - (- samples on -) fired no voiced -; 📦×1 local-whisper; copies 1.0 recall 1.00; rows +0 (); clipboard writes 1 |
| TQ4 | **PASS** | 58 | Wispr killed, then 🔼→: the local model borrowed at once (`Wispr Flow is starting`), delivered once, Wispr launched by the relay; sentences at +2 s and +15 s after Wispr is up voiced and delivered once | cold: SEC TQ4.cold close→words 1.74 s via local-whisper budget - (- samples on -) fired no voiced -; borrowed True; 📦×1 local-whisper; copies 1.0 recall 1.00; rows +0 (); clipboard writes 1 \| Wispr up True (0 s after the sentence) \| TQ4.+2s: SEC TQ4.+2s close→words 0.54 s via wispr-history budget 2.9 (100 samples on wispr-flow) fired no voiced 1.7; 📦×1 wispr-history; copies 1.0 recall 1.00; rows +1 (formatted); 1.7 s voiced; clipboard writes 1 \| TQ4.+15s: SEC TQ4.+15s close→words 0.51 s via wispr-history budget 2.9 (100 samples on wispr-flow) fired no voiced 1.7; 📦×1 wispr-history; copies 1.0 recall 1.00; rows +1 (formatted); 1.7 s voiced; clipboard writes 1 |

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
