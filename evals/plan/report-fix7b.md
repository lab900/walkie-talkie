# Test plan run — 2026-09-27 09:12

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

FAIL 1 · PASS 5

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TR20 | **PASS** | 8 | terminal closed mid-sentence → the sentence is pasted at the caret (Victor's Q4, 2026-09-26), no 'delivered' row for the dead tty | B=ttys001 closed while listening; to=caret; rows=[]; gone logged=True; bound after=None; awaitingBind=False; pasted into the sink=True |
| TL12 | **FAIL** | 120 | 401 → 'HTTP 401', '↪️ … on this Mac instead', via local-fallback (no retry); next sentence back on ElevenLabs | 401 True, ↪️ True, retries 0, via local-fallback in 2.7 s; next sentence via None; the stale-warning half needs G5 (prompt state) |
| TL13 | **PASS** | 21 | transport error retried once: 'attempt 1 failed … retrying', failure ≤ 2 s after stop, fallback delivers | retries 1, failure → fallback 0.81 s after stop, via local-fallback |
| TL14 | **PASS** | 40 | blackhole (fake timeout after 20 s): failure at 20±1 s, no retry, 'still uploading — 8 s in', fallback delivers | failure 20.0 s after stop, retries 0, 'still uploading — 8 s in' True, via local-fallback (the fake's delay, not URLSession's own timeout — G13 for that) |
| TL16 | **PASS** | 99 | 3 s of silence → 'returned no words', the WAV kept for Recover, nothing delivered (fixed 2026-09-26, §3.8: an empty answer is `.failed(heardNothing)` with the audio, no local fallback — Q8: under 2 s voiced; batch 7: the same on ANY Scribe failure, so a 401/quota on silence is not decoded either; the BUG branch is the old loss) | no-words line False, ↪️ False, audio kept True, recoverable True, delivered False |
| TR13 | **PASS** | 29 | empty Scribe answer on 20 s of speech → (Q8, batch 6) ≥ 2 s voiced, so the local model stands in and delivers it; before batch 6: WAV staged, Recover returns it | 'returned no words' on speech → local fallback delivered via local-fallback (Q8) |

## Notes (2026-09-27, batch 7)

ElevenLabs had **0 credits**: every real upload answered `HTTP 401 quota_exceeded`. **TL16 PASS** is
batch 7 item 1 live: 3 s of silence → the real 401 → `only 0.0 s voiced (under 2 s): no local
fallback, the audio is kept for Recover`, nothing delivered (FAIL this morning, `↪️` + delivered).
TL12/13/14 play `CLIP_SPEECH` now (logged 3.3–3.6 s voiced) and fall back as before. **TL12 FAIL is
its second half only**: *next sentence back on ElevenLabs* cannot pass with no credits — the real
401 on `CLIP_EN` (1.5 s voiced, under the floor) ended *No words heard*; the first half passed
(401, ↪️, no retry, local-fallback in 2.7 s). TR20 (Q4: tab closed mid-sentence → caret) re-run
because `deliver` now checks the tab's owner first: PASS.
