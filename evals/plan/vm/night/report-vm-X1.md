# Test plan run — 2026-09-26 21:07

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

FAIL 2 · PASS 3

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| LC3 | **PASS** | 10 | pause: velocity → 0 within 1.5 s of the last word, centre unchanged until the eraser starts at 5.0 s | eraser at +5.07 s, max velocity 0.0 pt/s and centre drift 0.00 pt in [+1.5 s, eraser), velocity exactly 0 from +1.47 s |
| LC9 | **FAIL** | 14 | append-only ×30: corrections 0; each appended word's opacity starts < 0.1 and reaches its target within 0.6 s | 1 word(s) started at ≥ 0.1, e.g. [(15, 0.15)]; 6 word(s) slower than 0.65 s to 90 %: [(4, 0.78), (5, 0.72), (12, 0.65)] — corrections 0, start opacity max 0.15, slowest to 90 % 0.83 s over 30/30 words |
| TL2 | **PASS** | 1 | cancel of a test-open sentence → within 200 ms listening/settling false, 'nothing to cancel' line | cleared in 27 ms; 'nothing to cancel' line: yes |
| TD13 | **PASS** | 7 | restoring a tmux binding (POST /bind {client tty}) binds the pane that was bound, not the active one | client ttys003; panes ['%0', '%1']; bind with %0 active → 200 %0; bound-tty='ttys003 %0'; restore with %1 active → 200 %0 |
| TG16 | **FAIL** | 8 | 🔼↓ F9 while the panel is held (words not yet committed) marks that prompt kamikaze. Predicted defect: `☠️ kamikaze gesture with no sentence in flight — ignored` | panel up 67 ms; ignored line=False; sent prompt carries kamikaze=False · sent forward-down@0.067s |
