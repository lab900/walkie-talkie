# envelope-wispr — on Wispr, the words first and every picture after them

Victor, 2026-09-30 (dictated): *"să nu înceapă prompt-ul generat cu imagine zero, ci să pui imaginea
respectivă și toate celelalte cu timestamp asociat la finalul, după textul prompt-ului … rulează și
aici niște evaluri … încearcă să minimizezi cât de mult poți textul"*.

`ask.py`: one Romanian/English dictation, a fresh `claude -p` per run with **no tools**, 3 runs ×
Sonnet/Opus per arm. Scene `three` = 📸0 (auto) + two presses; scene `one` = 📸0 alone.

| arm | chars | first words | auto = 📸0 | 📸1 small path | 📸2 full path | 📸2 at 9 s | 📸1 pointer | error frame = 📸2 |
|---|---|---|---|---|---|---|---|---|
| three · `now` (📸0 leads; the pressed rows lose their pointer) | 456 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | **0/6** | 5/6 |
| three · `tail` (a full row per frame, pointer + clock) | 481 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 4/6 |
| three · **`fold`** (template row + `[📸1🖱️@x:y at 0:04]` per frame) | **366** | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 |
| one · `now` | 310 | 6/6 | 5/6 | 6/6 | 6/6 | | 6/6 (📸0) | |
| one · **`tail`** | 313 | 6/6 | 6/6 | 6/6 | 6/6 | | 6/6 (📸0) | |

*Error frame* is a guess by construction (no pixels); `tail`'s two misses are Sonnet answering
`unclear` with 📸2 named as its guess. `now`'s `one` miss: Sonnet read `auto` as *the pointer was
auto-captured*.

**Shipped:** `fold` for two or more plain frames of one size, `tail` for a lone one — 20 % shorter
than today on the three-frame scene, and the pointer of a pressed frame is no longer lost.

```
uite aici … Fix it, and add a test for it.

[Dictated in RO or EN]
[📁=$WALKIE_SHOTS/2026-09-30-09-57-21/11-31-07]
[📸n = 📁/screenshot-n-800px.jpg, or -original.jpg at 3456x2234px]
[📸0🖱️@1952:1134 auto at 0:00]
[📸1🖱️@1204:388 at 0:04]
[📸2🖱️@610:1790 at 0:09]
```

Re-run: `python3 evals/envelope-wispr/ask.py 3` (30 `claude -p` calls, ~2 min).
