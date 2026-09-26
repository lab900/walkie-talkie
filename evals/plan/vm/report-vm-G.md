# Test plan run — 2026-09-26 18:34

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

FAIL 2 · PASS 3

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TL22 | **FAIL** | 125 | a cold local model never delays the microphone (2026-09-26 decision): forward-right opens it within 0.5 s while the model loads, nothing is banked; /test/cancel cancels it; an engine switch afterwards opens nothing. Before (R7): the gesture was banked, /test/cancel had nothing to cancel, and the switch opened the ElevenLabs microphone with no gesture | mic opened 1.28 s after the gesture (model still loading=True, 'recording anyway' line=True, banked line=False); /test/cancel cancelled it, quiet=True; switched to eleven: microphone stayed shut |
| TR4 | **FAIL** | 9 | fail-open proves itself (/test/stall 6 + input) → 🧊 within 3.5 s, one hangs/ file, no button left down | nudge posted=False; silent line=3.0 s; back line=6.2 s; new hangs files=0; sessionFlags=[]; buttons down=None |
| TG1 | **PASS** | 2 | 🔼 F7 at idle opens a caret prompt (pasteMode, chip `at caret`). Predicted defect: the key trace is blind to it (no `↓ key 98` line — the F-key branches return nil, not swallow()) | listening=True 162 ms after the POST, pasteMode=True, chip «Prompting → ￼... \| at caret \| ×1», trace ↓98×1, ↑98 (ours) passed×1 · sent forward-click@0.670s |
| TG2 | **PASS** | 4 | F10 train at 0/300/600/900 ms → one start and three `re-triggered … dropped`; at 1.6 s `only NNN ms old — not stopping`; at 2.3 s it stops. Predicted defect (R21): the 2 s dwell runs from the main-thread edge, so the 2.3 s stop is refused too | starts=1, re-triggered at ['350', '252', '375'] ms, refused at sentence ages ['1643'] ms, stopped by +3.2 s=True · sent forward-right@0.000s forward-right@0.352s forward-right@0.602s forward-right@0.974s forward-right@1.647s forward-right@2.353s |
| TG3 | **PASS** | 95 | 🔼← F11 cancels a sentence opened on a cold local model: the gesture opens the microphone within 0.5 s while the model loads (2026-09-26 decision — nothing is banked), F11 cancels it, and nothing opens once the model is up. Before: the gesture was banked, F11 had nothing to cancel, the microphone opened ~10 s later | mic opened 0.14 s after the gesture (model still loading=True); cancel line=True, closed=True (F11 at +1.51 s); model up=False, anything opened after it=False; banked=False · sent forward-right@0.786s forward-left@1.515s |
