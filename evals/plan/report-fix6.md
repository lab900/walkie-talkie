# Test plan run — 2026-09-27 08:01

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

BUG 1 · PASS 15 · SKIP 5

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| LC1 | **PASS** | 2 | first word centred: \|centre − bandWidth/2\| < 3, velocity 0, opacity 0 → 0.4 within 0.5 s, never anchor ≥ bandWidth − 5 | centre off 0.00 pt, max velocity 0.0, opacity 0 → [0.37] at +0.5 s → 0.4, bandWidth 1728 |
| LC2 | **PASS** | 21 | growth at 0.4 s/word for 20 s: centre ±80 until line > bandWidth − 96, then anchor + shownWidth ≤ bandWidth − 48 + 2; \|Δanchor\| ≤ 700·Δt + 2; anchor rises only by a drop | 297 samples, wide from t=6.437, max centre offset 0.0 pt while narrow, dropped 32, max velocity 689 |
| LC3 | **PASS** | 9 | pause: velocity → 0 within 1.5 s of the last word, centre unchanged until the eraser starts at 5.0 s | eraser at +5.02 s, max velocity 0.0 pt/s and centre drift 0.00 pt in [+1.5 s, eraser), velocity exactly 0 from +1.5 s |
| LC4 | **PASS** | 5 | burst of 15 words: anchor eases, no step > 700·Δt, every sample velocity ≤ 700 | max velocity 700 pt/s, 39 samples, dropped 0 |
| LC5 | **PASS** | 5 | "fix the build today" → "fix it today": corrections +1, ghosts [the, build] within 0.3 s, [] after 0.6 s, correcting [] after 2.7 s, reflowing > 0 then < 0.5 within 1.6 s, centre glides | corrections +1, ghosts [['the', 'build']], reflowing 125.0 → [0] at +1.6 s, update seen 0.02 s after the POST |
| LC6 | **PASS** | 3 | "500" → "five hundred": corrections +2, ghosts ["500"] | corrections +2, ghosts [['500']] |
| LC7 | **PASS** | 1 | revision past the dropped words: dropped 0, words 3, centred at once (velocity 0 on the first sample), ghosts [] | dropped before 13; first sample: dropped 0, anchor 732, velocity 0, centre off 0, corrections 0 |
| LC7b | **PASS** | 2 | change only inside the dropped region: corrections unchanged, anchor continuous | dropped 13 → 13, corrections +0, anchor -69.5 → -69.5 |
| LC8 | **PASS** | 4 | tail punctuation flicker and mid-line case/punctuation commits: corrections unchanged, ghosts [] | 6 revisions, corrections +0, 0 sample(s) with ghosts |
| LC9 | **PASS** | 12 | append-only ×30: corrections 0; each appended word's opacity starts < 0.1 and reaches its target within 0.6 s | corrections 0, start opacity max 0.08, slowest to 90 % 0.55 s over 30/30 words |
| LC10 | **PASS** | 3 | {on:false}: open flips at once, words 0 after 0.6 s; reopen within 0.15 s is not reset by the fade's completion | after close: open False words 0; after reopen at 0.1 s: open True words 2 (the panel's alpha is not in describe(): a fade that ends at 0 over a reopened band is invisible here) |
| LC11 | **SKIP** | 0 | second display: the band on the screen under the pointer (needs G7 frame) | needs G7 liveCaption.frame/screen |
| LC12 | **SKIP** | 0 | RELAY_SHOOT never shows the band | needs the app relaunched under RELAY_SHOOT (out of scope: no restarts from the runner) |
| LC14 | **PASS** | 1 | empty text while open: words 0, still open | words 0, open True |
| LC15 | **PASS** | 3 | {text:"a b c.", partial:"d e f"}: committed 3, opacity ≈ [1,1,1,0.8,0.6,0.4] within 0.6 s; commit all → ≈ 1 within 0.8 s, corrections 0 | +0.6 s [0.94, 0.94, 0.94, 0.75, 0.56, 0.37] (max err 0.06), settled [1, 1, 1, 0.8, 0.6, 0.4]; after commit +0.8 s [1, 1, 1, 1, 0.99, 0.99], corrections 0 |
| LC16 | **PASS** | 17 | eraser after 5 s at ≈260 pt/s; visible centre ±80 while dropped grows; a new word freezes the front; after a full wipe the next word is a fresh centred line with eraseFront null | eraser at +5.05 s, 257 pt/s; dropped 2, visible-centre offset max 3 pt over 14 samples; fresh line: eraseFront None, centre off 0.0, velocity 0 |
| LC17 | **PASS** | 7 | gentle correction: corrections +1, the eraser keeps sweeping (eraseFront still increasing) | corrections +1, front -754.0584652550751 → -444.2037252575392 (255 pt/s); the paler tint is not in describe() |
| LC18 | **SKIP** | 0 | timing precision needs G8's server-side script/trace, two displays G7's frame | needs G8 (/test/live-caption script + trace) |
| TL15 | **SKIP** | 0 | a slow upload (45 s) keeps the settle up past the old 30 s ceiling — it waits while the recogniser works (2026-09-26, item 5) — and both start gestures refuse while the words are in flight, saying so; the late reply lands in the latched terminal (since Q12, batch 6: both gestures START the next sentence, queued; the late reply still lands). Before: the settle gave up at 32 s, forward-click refused, forward-right started a sentence the late reply then landed in | needs hands-off |
| TL18 | **SKIP** | 0 | the restart gate blocks while audio is staged for Recover; today: --dry-run opens (busy:false) and a restart would wipe cancelled/ | needs hands-off |
| TD21 | **BUG** | 15 | a bound tab closed and its tty reused by a new tab within 10 s → the binding does not move to the stranger | binding silently moved to the new tab — tty ttys000 reused by the new tab; bound after 11 s=ttys000; to=terminal:ttys000; landed in the new tab=True |

## Notes (2026-09-27 morning)

Gesture-tagged cases SKIP here by design (no hands-off); they ran in `report-fix6b.md`.
**TD21 BUG** — first time reachable on the host: Terminal reused the closed tab's tty (ttys000)
for the new tab within 10 s and the binding moved to the stranger. Same defect the Tart lab found
the night before; not in batch 6's scope, not fixed.
