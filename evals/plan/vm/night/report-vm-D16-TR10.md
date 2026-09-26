# Test plan run — 2026-09-26 20:20

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 1

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TR10 | **PASS** | 45 | fallback with a cold model (helper SIGKILLed first) → delivered before fallbackCeiling (180 s) | delivered 34.5 s after stop via local-fallback, 'did not come up' False, helper now alive True pid 8013 |
