# Test plan run — 2026-09-26 20:25

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 1

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TR14 | **PASS** | 62 | helper killed mid-decode → the sentence is kept (.failed with the audio) or, since batch 1 e, revived and delivered; app alive, helper restarts, the next sentence delivers | failed line False, recoverable False, revived and asked again True (the killed sentence via local-fallback), app pid 5095 → 5095, helper pid 8013 → 8590 alive True, next sentence via local-fallback |
