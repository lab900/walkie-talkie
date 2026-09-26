# Test plan run — 2026-09-26 19:31

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 1

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TD25 | **PASS** | 10 | busy stays true from the spawn's first busy until the new window is bound (spawn is a restart blocker) | 110 samples; first busy +0.046s ('prompt on screen',); bound ttys001 at +8.21s; idle-while-unbound samples=0 |
