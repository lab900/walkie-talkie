# Test plan run — 2026-09-26 20:21

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 1

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TR11 | **PASS** | 67 | slow failure (transport after 19 s, twice) passes the 30 s settle ceiling → expected to fail today: the settle times out before the fallback | settle timed out at None s, ↪️ at 50.1 s, end at 50.2 s, via local-fallback, to terminal:ttys001 |
