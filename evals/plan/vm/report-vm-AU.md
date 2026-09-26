# Test plan run — 2026-09-26 18:38

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

FAIL 1 · SKIP 2

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TL12 | **FAIL** | 215 | 401 → 'HTTP 401', '↪️ … on this Mac instead', via local-fallback (no retry); next sentence back on ElevenLabs | 401 True, ↪️ True, retries 0, via None in 90.6 s; next sentence via None; the stale-warning half needs G5 (prompt state) |
| LC13 | **SKIP** | 2 | live integration: band words > 0 while isRecording; the band closes when listening goes false | engine is eleven, the case needs eleven-live |
| B2 | **SKIP** | 2 | a VAD commit → '💬 live correction: … → scribe_v2', live.corrections ≥ 1, elevenCost.total grows, band corrections ≥ 0 | engine is eleven, the case needs eleven-live |
