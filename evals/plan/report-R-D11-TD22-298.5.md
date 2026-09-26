# Test plan run — 2026-09-26 19:10

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 1

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TD22-298.5 | **PASS** | 307 | bind at 298.5 s after the hold → exactly one outcome (delivered xor expired), nothing left held | bind posted at +298.44s, done +298.90s; released=True expired=False delivered=True rows=1 awaitingBind=False |
