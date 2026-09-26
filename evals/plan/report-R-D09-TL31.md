# Test plan run — 2026-09-26 19:02

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 1

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TL31 | **PASS** | 314 | a hung helper (SIGSTOP) no longer wedges the app: the 300 s decode budget kills it, a new helper comes up, the sentence ends failed with its WAV staged for Recover, phase leaves `transcribing`, busy goes false and the restart gate opens — without a SIGCONT. Before: at 35 s phase transcribing, busy, the gate blocked until the helper was resumed by hand | at 35 s: settling=True phase=transcribing/ (the settle waits); 'timed out' at 300.1 s after the stop; then phase=done settling=False busyWhy=[]; failed-with-budget line=True; WAV staged for Recover=True; dry-run exit 0 in 0.2 s; helper 49006→13826 ready=True; invariants ok |
