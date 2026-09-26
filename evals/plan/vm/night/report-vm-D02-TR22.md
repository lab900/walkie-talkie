# Test plan run — 2026-09-26 19:31

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 1 · SKIP 1

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TR22 | **SKIP** | 0 | a spawn that fails re-offers the sentence; no spawn: receipt before the window exists | no route or fault switch fails a spawn (SpawnTerminal has no test hook) — needs a new gap |
| TR22 | **PASS** | 10 | no `spawn:` receipt before the new window exists (and a failed spawn re-offers the sentence) | spawn rows=['spawn:/Users/admin/workspace']; first outbox row at +8.20s; bound ttys001 at +8.20s; failure/re-offer not injectable |
