# Test plan run — 2026-09-26 19:59

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 1

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TD22-298.5 | **PASS** | 315 | bind at 298.5 s after the hold → exactly one outcome (delivered xor expired), nothing left held | bind posted at +298.55s, done +303.60s; released=False expired=True delivered=False rows=0 awaitingBind=False |
