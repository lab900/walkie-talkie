# Test plan run — 2026-09-28 23:31

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 3 · PASS 1

ElevenLabs: credits unreadable (no ELEVENLABS_API_KEY); cap 3000 → cases that would spend real credits **SKIP**. Engine for the run: `whisper` (was `wispr`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 58563 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW4 | **BUG** | 105 | a cold Wispr: the first 3 s he says reach the witness; the chip names the warming | 41/271 samples listening+warming+no row (2.1 s); first-5-words hit 0/5; chip named it True; still listening at the stop False |
| TX8b | **BUG** | 21 | relay sentence, then his 61+60 sentence 0.3 s after its stop: relay's in the witness once, his at the caret once (Q19), nothing crossed | his sentence lost (W4; lab finding 3): relay: witness 1.0, TextEdit 0.0 · his: TextEdit 0.0, witness 0.0 · Q19 line True · drop line True; 📦×1 wispr-history; copies 1.0 recall 1.00; rows +2 (formatted); 1.9 s voiced; clipboard writes 1 · TE='Could you get the assumption? ' |
| TX9 | **PASS** | 176 | 3 sentences each 1 s after a Wispr relaunch: all delivered with their head (first 5 words), or said why — losses counted | losses 0/3 (silent 0), head losses 0; <br>#0 opened True ok head-miss 1/5; 📦×1 local-fallback; copies 1.0 recall 0.48; rows +1 (); Q14 fallback; 2.5 s voiced; failure: Wispr Flow never opened its microphone; clipboard writes 1<br>#1 opened True ok head-miss 1/5; 📦×1 local-fallback; copies 1.0 recall 0.48; rows +2 (); Q14 fallback; 2.7 s voiced; failure: Wispr Flow never opened its microphone; clipboard writes 2<br>#2 opened True ok head-miss 1/5; 📦×1 local-fallback; copies 1.0 recall 0.48; rows +3 (); Q14 fallback; 2.6 s voiced; failure: Wispr Flow never opened its microphone; clipboard writes 3 |
| TX10 | **BUG** | 94 | 5 relay + 5 standalone sentences alternating, 2 s gaps: relay words only in the witness, his only in TextEdit; losses counted, 0 misroutes, 0 stuck | relay: 5 opened, 0 refused, witness 5.0/5, TextEdit 0.0 · his: TextEdit 0.0/5, witness 0.0 · losses relay 0 his 5; 📦×5 wispr-history,wispr-history,wispr-history,wispr-history,wispr-history; copies 5.0 recall 1.00; rows +10 (formatted); doubled text; 1.7 s voiced; clipboard writes 7 · TE='Would you get the assumption? Could you get the assumption? Could you get the assumption? Could you get the assumption? Could you get the assumption? ' |

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
