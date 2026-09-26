# Test plan run — 2026-09-26 19:32

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

FAIL 1

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TD12 | **FAIL** | 21 | a bind made while a quit is deferred survives the relaunch (restore binds B, not the A read before SIGTERM) | A=ttys001 B=ttys002; bound-tty before SIGTERM=['ttys001'], after the exit=['ttys002']; quit deferred=True; restore ttys002 /bind 200; bound after=None |
