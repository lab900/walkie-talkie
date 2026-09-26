# Test plan run — 2026-09-26 19:37

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

FAIL 1

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TR14 | **FAIL** | 32 | helper killed mid-decode → .failed with the audio, app alive, helper restarts, the next sentence delivers | failed line False, recoverable False, app pid 71414 → 71414, helper pid 39604 → 80441 alive True, next sentence via local-fallback |
