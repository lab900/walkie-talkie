# Test plan run — 2026-09-29 02:01

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 1 · PASS 4

ElevenLabs: credits unreadable (no ELEVENLABS_API_KEY); cap 3000 → cases that would spend real credits **SKIP**. Engine for the run: `whisper` (was `wispr`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 54306 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TM1 | **PASS** | 24 | a take on a device feeding digital zeros (the Loopback with nothing played): three `🔁 mic: N buffers with peak 0` restarts (step 1 tap, steps 2–3 a new AVAudioEngine), `did not bring audio back … stays DEAF`, and `mic: closed — … peak 0 … — DEAF` | 3 peak-0 restart(s); gave up True; closed: BlackHole 2ch: 57 buffers, peak 0, 3 tap restart(s), 6.2 s — DEAF; first: 🔁 mic: 14 buffers with peak 0 for 1.4 s [mute off, input volume 1.00, nominal 48000 Hz, tap 48000 Hz, running somewhere yes, IO buffer 512] — tap restarted (ste |
| TM2 | **PASS** | 24 | 2 s of digital zeros, then the clip: one peak-0 restart (step 1, the tap), `audio came back after restart 1`, the take not DEAF, and the clip's words delivered whole (the restart cost no word) | 3 peak-0 restart(s); came back: udio came back after restart 3 — peak 349, 5.3 s after it; closed: BlackHole 2ch: 145 buffers, peak 16348, 3 tap restart(s), 15.0 s; words: 'If I dictate now, how good is this dictation, I wonder.' (slow clip start: 3 restarts ran before it) |
| TW39 | **PASS** | 23 | a ⌘V dropped in the relay's tail while his newer row is still NULL: the pasteboard is read once and kept; the row's words win if they come, the pasteboard's only if they do not; never pasted twice | (a) ⌘V dropped; claim row 2 from the row (22 chars); (b) ⌘V dropped; claim row 4 from the pasteboard (the row still unfinished after 5 s) (21 chars); second ⌘V passed; dry claims of C 1; pasteboard reads 2 |
| TX8b | **BUG** | 51 | relay sentence, then his 61+60 sentence 0.3 s after its stop: relay's in the witness once, his at the caret once (Q19), nothing crossed | his sentence lost (W4; lab finding 3): relay: witness 1.0, TextEdit 0.0 · his: TextEdit 0.0, witness 0.0 · Q19 line False · drop line True; 📦×1 wispr-history; copies 1.0 recall 1.00; rows +1 (formatted); 1.8 s voiced; clipboard writes 1 · TE='' |
| TX10 | **PASS** | 93 | 5 relay + 5 standalone sentences alternating, 2 s gaps: relay words only in the witness, his only in TextEdit; losses counted, 0 misroutes, 0 stuck | relay: 5 opened, 0 refused, witness 5.0/5, TextEdit 0.0 · his: TextEdit 5.0/5, witness 0.0 · losses relay 0 his 0; 📦×5 wispr-history,wispr-history,wispr-history,wispr-history,wispr-history; copies 5.0 recall 1.00; rows +10 (formatted); doubled text; 1.7 s voiced; clipboard writes 6 · TE='Could you get the assumption? Could you get the assumption? Could you get the assumption? Could you get the assumption? Could you get the assumption? ' |

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
