# Test plan run — 2026-09-26 18:22

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 2

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TL6 | **PASS** | 4 | dead helper (SIGKILL) → the app survives, 'it died' at the kill, and /test/local-fallback either refuses fast {ok:false} or (since batches 1e/3) brings a helper up and answers; restart brings it back | route 3.27 s → {'seconds': 3.2709879875183105, 'text': 'If I dictate now, how good is this dictation, I wonder.', 'ok': True, 'via': 'local-fallback', 'engine': 'whisper-local', 'warning': '⚠️ a test was unavailable — transcribed on this Mac'}; app pid 96476→96476; 'it died' line: yes; ready after=True; restart up in 0.0 s (helper pid 67984→8706) — revived and answered (batch 1 e / batch 3) |
| TL27 | **PASS** | 4 | held sentence released by POST /bind {"tty"} within 1 s | released 0.32 s after the bind; words in the witness: yes; lastDelivery.to=terminal:ttys032; invariants ok |
