# Test plan run — 2026-09-29 01:55

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 1

ElevenLabs: credits unreadable (no ELEVENLABS_API_KEY); cap 3000 → cases that would spend real credits **SKIP**. Engine for the run: `whisper` (was `wispr`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 53700 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TS3 | **PASS** | 323 | 20 relay/standalone sentences in seeded random order, 1–6 s gaps: ≥ 90 % routed right, 0 misroutes, 0 silent, 0 stuck | 20/20 · delivered 20 (100.0 %) · truncated 0 · lost 0 (silent 0) · rows 20/20 (NULL 0) · via wispr-history 7 · recall mean 0.99 min 0.88 · close→landed p50 2.0 s p90 5.9 s · doubled 0 · stuck 0 · 323 s · seed 46949 · relay 7 / standalone 13 · routed right 20 (100.0 %) · misrouted 0 · start: mic closed · /tmp/wt-plan/soak-TS3-20260929-020112.json<br>#01 relay 17-08-41-98d row ✓ landed 6.0 s via wispr-history recall 1.00<br>#02 stand 17-08-41-98d row ✓ landed 1.9 s via - recall 1.00<br>#03 stand 17-08-41-98d row ✓ landed 1.2 s via - recall 1.00<br>#04 stand 21-05-35-11l row ✓ landed 0.6 s via - recall 0.91<br>#05 relay 21-05-35-11l row ✓ landed 4.7 s via wispr-history recall 1.00<br>#06 relay 17-08-41-98d row ✓ landed 5.9 s via wispr-history recall 1.00<br>#07 stand 17-08-41-98d row ✓ landed 2.5 s via - recall 1.00<br>#08 relay 17-08-41-98d row ✓ landed 6.4 s via wispr-history recall 1.00<br>#09 stand 17-08-41-98d row ✓ landed 2.0 s via - recall 1.00<br>#10 relay 21-05-35-11l row ✓ landed 4.6 s via wispr-history recall 1.00<br>#11 stand 21-05-35-11l row ✓ landed 0.6 s via - recall 1.00<br>#12 stand 21-05-35-11l row ✓ landed 0.7 s via - recall 1.00<br>#13 stand 17-08-41-98d row ✓ landed 1.9 s via - recall 0.88<br>#14 relay 21-05-35-11l row ✓ landed 4.8 s via wispr-history recall 1.00<br>#15 stand 21-05-35-11l row ✓ landed 0.6 s via - recall 1.00<br>#16 relay 21-05-35-11l row ✓ landed 4.8 s via wispr-history recall 1.00<br>#17 stand 17-08-41-98d row ✓ landed 2.6 s via - recall 1.00<br>#18 stand 21-05-35-11l row ✓ landed 0.6 s via - recall 1.00<br>#19 stand 17-08-41-98d row ✓ landed 2.0 s via - recall 1.00<br>#20 stand 21-05-35-11l row ✓ landed 0.8 s via - recall 1.00 |

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
