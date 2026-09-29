# Test plan run — 2026-09-29 04:57

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 1

ElevenLabs: credits unreadable (no ELEVENLABS_API_KEY); cap 3000 → cases that would spend real credits **SKIP**. Engine for the run: `whisper` (was `wispr`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 56581 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TS3 | **PASS** | 303 | 20 relay/standalone sentences in seeded random order, 1–6 s gaps: ≥ 90 % routed right, 0 misroutes, 0 silent, 0 stuck | 20/20 · delivered 20 (100.0 %) · truncated 0 · lost 0 (silent 0) · rows 20/20 (NULL 0) · via wispr-history 8 · recall mean 0.99 min 0.88 · close→landed p50 1.8 s p90 5.6 s · doubled 0 · stuck 0 · 303 s · seed 57821 · relay 8 / standalone 12 · routed right 20 (100.0 %) · misrouted 0 · start: mic closed · /tmp/wt-plan/soak-TS3-20260929-050204.json<br>#01 relay 17-08-41-98d row ✓ landed 5.6 s via wispr-history recall 1.00<br>#02 stand 17-08-41-98d row ✓ landed 1.9 s via - recall 1.00<br>#03 stand 21-05-35-11l row ✓ landed 0.6 s via - recall 1.00<br>#04 relay 17-08-41-98d row ✓ landed 5.5 s via wispr-history recall 1.00<br>#05 stand 17-08-41-98d row ✓ landed 1.8 s via - recall 1.00<br>#06 stand 21-05-35-11l row ✓ landed 0.7 s via - recall 1.00<br>#07 relay 21-05-35-11l row ✓ landed 4.7 s via wispr-history recall 1.00<br>#08 stand 21-05-35-11l row ✓ landed 0.6 s via - recall 1.00<br>#09 stand 17-08-41-98d row ✓ landed 1.4 s via - recall 1.00<br>#10 stand 17-08-41-98d row ✓ landed 1.9 s via - recall 0.88<br>#11 relay 21-05-35-11l row ✓ landed 4.6 s via wispr-history recall 1.00<br>#12 stand 21-05-35-11l row ✓ landed 0.5 s via - recall 1.00<br>#13 stand 21-05-35-11l row ✓ landed 0.5 s via - recall 1.00<br>#14 stand 17-08-41-98d row ✓ landed 1.3 s via - recall 1.00<br>#15 relay 17-08-41-98d row ✓ landed 5.7 s via wispr-history recall 1.00<br>#16 relay 17-08-41-98d row ✓ landed 5.8 s via wispr-history recall 0.88<br>#17 stand 21-05-35-11l row ✓ landed 0.5 s via - recall 1.00<br>#18 relay 17-08-41-98d row ✓ landed 5.4 s via wispr-history recall 1.00<br>#19 stand 21-05-35-11l row ✓ landed 0.7 s via - recall 1.00<br>#20 relay 17-08-41-98d row ✓ landed 5.6 s via wispr-history recall 1.00 |

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
