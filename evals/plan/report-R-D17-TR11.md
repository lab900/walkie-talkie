# Test plan run — 2026-09-26 19:34

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

ERROR 1

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TR11 | **ERROR** | 12 | slow failure (transport after 19 s, twice) passes the 30 s settle ceiling → expected to fail today: the settle times out before the fallback | RuntimeError: the microphone never opened<br>Traceback (most recent call last):<br>  File "/Users/victorrentea/workspace/walkie-talkie/evals/plan/harness.py", line 317, in run<br>    verdict, note = c["fn"]()<br>                    ^^^^^^^^^<br>  File "/Users/victorrentea/workspace/walkie-talkie/evals/plan/cases_audio.py", line 540, in tr11<br>    m, _ = dictate_loopback(CLIP_EN, wait_after=1.0)<br>           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^<br>RuntimeError: the microphone never opened<br> |
