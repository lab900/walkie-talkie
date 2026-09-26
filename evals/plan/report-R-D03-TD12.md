# Test plan run — 2026-09-26 18:40

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 1

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TD12 | **PASS** | 7 | a bind made while a quit is deferred survives the relaunch (restore binds B, not the A read before SIGTERM) | A=ttys038 B=ttys039; bound-tty before SIGTERM=['ttys038'], after the exit=['ttys039']; quit deferred=True; restore ttys039 /bind 200; bound after=ttys039 |
