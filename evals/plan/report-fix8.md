# Test plan run — 2026-09-27 11:57

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 4

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TL13 | **PASS** | 23 | transport error retried once: 'attempt 1 failed … retrying', failure ≤ 2 s after stop, fallback delivers | retries 1, failure → fallback 0.82 s after stop, via local-fallback |
| TL14 | **PASS** | 40 | blackhole (fake timeout after 20 s): failure at 20±1 s, no retry, 'still uploading — 8 s in', fallback delivers | failure 20.0 s after stop, retries 0, 'still uploading — 8 s in' True, via local-fallback (the fake's delay, not URLSession's own timeout — G13 for that) |
| TL16 | **PASS** | 99 | 3 s of silence → 'returned no words', the WAV kept for Recover, nothing delivered (fixed 2026-09-26, §3.8: an empty answer is `.failed(heardNothing)` with the audio, no local fallback — Q8: under 1.5 s voiced (Q13); batch 7: the same on ANY Scribe failure, so a 401/quota on silence is not decoded either; the BUG branch is the old loss) | no-words line False, ↪️ False, audio kept True, recoverable True, delivered False |
| TR13 | **PASS** | 28 | empty Scribe answer on 20 s of speech → (Q8, batch 6) ≥ 1.5 s voiced (Q13), so the local model stands in and delivers it; before batch 6: WAV staged, Recover returns it | 'returned no words' on speech → local fallback delivered via local-fallback (Q8) |
