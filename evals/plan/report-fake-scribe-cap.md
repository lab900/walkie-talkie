# Test plan run — 2026-09-28 07:39

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 2 · SKIP 5

ElevenLabs: **10033** credits used this month before the run, **-33** of 10000 left; cap 999999 → cases that would spend real credits **SKIP**. Engine for the run: `whisper` (was `eleven-live`, put back at exit); only `eleven`-tagged cases switch. fake Scribe off (`WT_FAKE_SCRIBE=0`): ElevenLabs cases go to the real service.

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| LC1 | **PASS** | 2 | first word enters letter by letter, centred (2026-09-27, 84d420e): reveal grows monotonically and the word is fully revealed (reveal null) within 1.2 s; \|centre − bandWidth/2\| < 3 on every sample; anchor \|velocity\| and the entry front ≤ 320 pt/s; first opacity < 0.1, settled 0.4 ± 0.03 (provisional); never anchor ≥ bandWidth − 5 | reveal 0 pt at +0.01 s → in at +0.87 s (front median 318 pt/s over 17 samples); centre off ≤ 0.00 pt; max \|velocity\| 99; opacity 0 → 0.4; bandWidth 1728 |
| TL11 | **PASS** | 127 | R2 local (through the fallback, engine unchanged): helper SIGSTOP, stop, cancel, SIGCONT → today delivered after 'Cancelled' | [eleven → real ElevenLabs] after cancel + SIGCONT: delivery False, 'audio kept' True, recoverable True |
| TL16 | **SKIP** | 0 | 3 s of silence → 'returned no words', the WAV kept for Recover, nothing delivered (fixed 2026-09-26, §3.8: an empty answer is `.failed(heardNothing)` with the audio, no local fallback — Q8: under 1.5 s voiced (Q13); batch 7: the same on ANY Scribe failure, so a 401/quota on silence is not decoded either; the BUG branch is the old loss) | credit cap (-33 left) |
| TL25 | **SKIP** | 0 | 10-min ceiling on real audio at 600±1 s; record `via` (the 20 s request timeout on a 19 MB WAV) | credit cap (-33 left) |
| LC13 | **SKIP** | 0 | live integration: band words > 0 while isRecording; the band closes when listening goes false | credit cap (-33 left) |
| B1 | **SKIP** | 0 | first live caption word ≤ 2 s after speech starts in the recording (plan: ≤ 1.5 s) | credit cap (-33 left) |
| B2 | **SKIP** | 0 | a VAD commit → '💬 live correction: … → scribe_v2', live.corrections ≥ 1, elevenCost.total grows, band corrections ≥ 0 | credit cap (-33 left) |

ElevenLabs credits after the run: **10033** — this run used **0** (ElevenLabs' daily buckets can lag by minutes; the dashboard is the final word).
