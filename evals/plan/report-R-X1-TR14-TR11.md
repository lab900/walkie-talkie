# Test plan run — 2026-09-26 21:44

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 2

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TR11 | **PASS** | 62 | slow failure (transport after 19 s, twice) passes the 30 s settle ceiling → expected to fail today: the settle times out before the fallback | settle timed out at None s, ↪️ at 50.1 s, end at 50.1 s, via local-fallback, to terminal:ttys000 |
| TR14 | **PASS** | 30 | helper killed mid-decode → the sentence is kept (.failed with the audio) or, since batch 1 e, revived and delivered; app alive, helper restarts, the next sentence delivers | failed line False, recoverable False, revived and asked again True (the killed sentence via local-fallback), app pid 60677 → 60677, helper pid 83709 → 89643 alive True, next sentence via local-fallback |
