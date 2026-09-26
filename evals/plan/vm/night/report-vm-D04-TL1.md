# Test plan run — 2026-09-26 19:33

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 1

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TL1 | **PASS** | 125 | orphan flush 121 s after /test/area mid-sentence: dictationStartedAt stays non-null (today: null + 'releasing 1 shot(s)' while listening) | bound ttys001; area at t=0, flush seen at — s; at 121 s listening=True dictationStartedAt=2026-09-26T19:33:30.453Z released=no witness got 0 chars; invariants ok |
