# Test plan run — 2026-09-27 09:12

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 3

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TD1 | **PASS** | 0 | POST /bind {tty: ttys999} (no such tty) → 409; nothing bound, no sentence lost | 409 no terminal on ttys999 |
| TD14 | **PASS** | 1 | restoring a tty that is no Terminal.app tab (IDE-like pty) → /bind refuses (409); no sentence lost | 409 for ttys000 (no terminal on ttys000); ps: Ss+  cat |
| TD21 | **PASS** | 24 | a bound tab closed and its tty reused by a new tab within 10 s → the binding does not move to the stranger | tty ttys000 reused by the new tab; bound after 11 s=None; to=held; landed in the new tab=False |

## Notes (2026-09-27, batch 7)

**TD21 BUG → PASS**: the binding is the tab's `login` (pid + start time), not the tty number; the
poll saw `ttys000` handed to a new tab and let go, the sentence was held, not typed into the
stranger. TD1/TD14 (bind refusal) still PASS. TR20 is gesture-tagged — it ran under the locks in
`report-fix7b.md` (PASS).
