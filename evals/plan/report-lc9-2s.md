# Test plan run — 2026-09-28 07:46

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 1

ElevenLabs: **10033** credits used this month before the run, **-33** of 10000 left; cap 3000 → cases that would spend real credits **SKIP**. Engine for the run: `whisper` (was `eleven-live`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 60647 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| LC9 | **PASS** | 18 | append-only ×30 at 2 words/s (letter by letter since 84d420e): corrections 0; per word, reveal grows monotonically, the word starts at opacity < 0.1 and is fully revealed within 2.0 s of its append; centre ±10 pt while the line is narrower than bandWidth − 96; anchor \|velocity\| ≤ 320 pt/s; entry front ≤ 0.7 vMax (490, the catch-up cap) | corrections 0; slowest full reveal 1.02 s over 30/30 words; first opacity max 0; front median 315 pt/s, 85/444 steps over 320 (+15 %, catch-up); centre off ≤ 0.0 pt over 163 narrow samples; max \|velocity\| 310 |

ElevenLabs credits after the run: **10033** — this run used **0** (ElevenLabs' daily buckets can lag by minutes; the dashboard is the final word).

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
