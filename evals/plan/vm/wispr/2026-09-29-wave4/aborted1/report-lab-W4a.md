# Test plan run — 2026-09-28 22:00

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 1 · ERROR 1 · SKIP 2

ElevenLabs: credits unreadable (no ELEVENLABS_API_KEY); cap 3000 → cases that would spend real credits **SKIP**. Engine for the run: `whisper` (was `wispr`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 49240 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TM1 | **SKIP** | 4 | a take on a device feeding digital zeros (the Loopback with nothing played): three `🔁 mic: N buffers with peak 0` restarts (step 1 tap, steps 2–3 a new AVAudioEngine), `did not bring audio back … stays DEAF`, and `mic: closed — … peak 0 … — DEAF` | BlackHole 2ch pass-thru is dead (440 Hz check) — toggle the device in Loopback |
| TM2 | **SKIP** | 2 | 2 s of digital zeros, then the clip: one peak-0 restart (step 1, the tap), `audio came back after restart 1`, the take not DEAF, and the clip's words delivered whole (the restart cost no word) | BlackHole 2ch pass-thru is dead (440 Hz check) — toggle the device in Loopback |
| TW1 | **BUG** | 7 | right ⌘⌥ held 3 s on Engine=Wispr stays one sentence: no 🧼 release before the real one, listening ≥ 2.5 s | held seen True; listening from 1.03 s for 2.3 s; release line before the case's cancel True; other cancel: None; dropped back to not-listening False |
| TW4 | **ERROR** | 0 | a cold Wispr: the first 3 s he says reach the witness; the chip names the warming | not started — prompt panel paused by the pointer for 20 s (autosend held) — needs ⎋ by hand |

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
