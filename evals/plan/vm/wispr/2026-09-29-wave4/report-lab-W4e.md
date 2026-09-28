# Test plan run — 2026-09-28 23:21

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

FAIL 1

ElevenLabs: credits unreadable (no ELEVENLABS_API_KEY); cap 3000 → cases that would spend real credits **SKIP**. Engine for the run: `whisper` (was `wispr`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 57739 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TS3 | **FAIL** | 358 | 20 relay/standalone sentences in seeded random order, 1–6 s gaps: ≥ 90 % routed right, 0 misroutes, 0 silent, 0 stuck | 20/20 · delivered 19 (95.0 %) · truncated 0 · lost 1 (silent 1) · rows 20/20 (NULL 0) · via wispr-history 10 · recall mean 1.00 min 1.00 · close→landed p50 4.8 s p90 6.2 s · doubled 0 · stuck 0 · 358 s · seed 37683 · relay 10 / standalone 10 · routed right 19 (95.0 %) · misrouted 0 · start: mic closed · /tmp/wt-plan/soak-TS3-20260928-232721.json<br>#01 stand 17-08-41-98d row ✓ landed ✗ via - recall - SILENT<br>#02 relay 21-05-35-11l row ✓ landed 4.8 s via wispr-history recall 1.00<br>#03 relay 17-08-41-98d row ✓ landed 5.8 s via wispr-history recall 1.00<br>#04 stand 21-05-35-11l row ✓ landed 0.5 s via - recall 1.00<br>#05 relay 21-05-35-11l row ✓ landed 5.3 s via wispr-history recall 1.00<br>#06 relay 17-08-41-98d row ✓ landed 6.5 s via wispr-history recall 1.00<br>#07 relay 21-05-35-11l row ✓ landed 4.8 s via wispr-history recall 1.00<br>#08 stand 17-08-41-98d row ✓ landed 1.1 s via - recall 1.00<br>#09 relay 17-08-41-98d row ✓ landed 6.1 s via wispr-history recall 1.00<br>#10 relay 17-08-41-98d row ✓ landed 6.0 s via wispr-history recall 1.00<br>#11 stand 17-08-41-98d row ✓ landed 1.9 s via - recall 1.00<br>#12 stand 21-05-35-11l row ✓ landed 0.6 s via - recall 1.00<br>#13 relay 17-08-41-98d row ✓ landed 5.9 s via wispr-history recall 1.00<br>#14 stand 21-05-35-11l row ✓ landed 0.6 s via - recall 1.00<br>#15 relay 17-08-41-98d row ✓ landed 5.9 s via wispr-history recall 1.00<br>#16 stand 21-05-35-11l row ✓ landed 0.6 s via - recall 1.00<br>#17 stand 17-08-41-98d row ✓ landed 1.9 s via - recall 1.00<br>#18 relay 17-08-41-98d row ✓ landed 6.2 s via wispr-history recall 1.00<br>#19 stand 17-08-41-98d row ✓ landed 2.4 s via - recall 1.00<br>#20 stand 17-08-41-98d row ✓ landed 1.4 s via - recall 1.00 |

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
