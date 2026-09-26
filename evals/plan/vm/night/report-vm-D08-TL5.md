# Test plan run — 2026-09-26 19:45

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 1

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TL5 | **PASS** | 360 | helper hang (SIGSTOP): the 300 s decode budget is enforced ('timed out after 300s', the helper killed and replaced), the control surface answers while /test/local-fallback waits, the next decode is in sync. Before: only the route's 180 s semaphore answered, /up was blocked behind it, no timeout ever | route answered after 180.01 s (False); control surface at +5 s: 0.01 s; 'timed out after' by 305 s: yes; after SIGCONT stale answer consumed: yes; next decode 3.55 s ok=True in sync |
