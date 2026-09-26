# Test plan run — 2026-09-26 20:05

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 1

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TD22-299.5 | **PASS** | 312 | bind at 299.5 s after the hold → exactly one outcome (delivered xor expired), nothing left held | bind posted at +299.65s, done +300.10s; released=False expired=True delivered=False rows=0 awaitingBind=False |
