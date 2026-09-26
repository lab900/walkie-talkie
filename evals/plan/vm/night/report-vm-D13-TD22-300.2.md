# Test plan run — 2026-09-26 20:11

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 1

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TD22-300.2 | **PASS** | 312 | bind at 300.2 s after the hold → exactly one outcome (delivered xor expired), nothing left held | bind posted at +300.31s, done +300.98s; released=False expired=True delivered=False rows=0 awaitingBind=False |
