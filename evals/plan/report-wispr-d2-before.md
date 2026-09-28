# Test plan run — 2026-09-28 23:59

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 1

ElevenLabs: **2172** credits used this month before the run, **7828** of 10000 left; cap 3000 → real cases allowed. Engine for the run: `whisper` (was `eleven-live`, put back at exit); only `eleven`-tagged cases switch. fake Scribe on port 58625 (live + batch, `WT_FAKE_SCRIBE=1`).

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TW40 | **BUG** | 140 | A's Wispr row never moves → Q14 local decode, parked by B; B's row formatted BEFORE A's decode ends: when A is delivered, B follows at once — both in the witness, A first; no 'wait for the one before' past A | helper stopped True; B waited its turn True; B in the witness False 20.5 s after the resume; A 225 chars before B at -1; 'wait for the one before' ×6; dropped False; queue after the resume [{'waiting': 1, 'id': 3, 'state': 'done', 'startedAt': '2026-09-28T20:59:43.112Z', 'target': 'terminal:training-assistant', 'take': None}] |

ElevenLabs credits after the run: **2172** — this run used **0** (ElevenLabs' daily buckets can lag by minutes; the dashboard is the final word).

Fake Scribe: 0 live session(s), 0 chunks (0.0 s), 0 partials, 0 commits, 0 batch upload(s), 0 error(s) sent.
