# Test plan run — 2026-09-26 20:55

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 1

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TL25 | **PASS** | 697 | 10-min ceiling on real audio at 600±1 s; record `via` (the 20 s request timeout on a 19 MB WAV) | ceiling at 600.3 s after the chord, delivered 92 s later via local-fallback; ElevenLabs upload failed/absent; fallback True |
