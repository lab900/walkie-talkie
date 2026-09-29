# envelope-width — does `-800px` still read as the width without `at 800px width`?

Victor, 2026-09-29: *"is it still comprehensible the 800 is width? eval it on a few claude code runs."*

`ask.py`: his dictation of 10:02, two footers differing only in ` at 800px width`, a fresh
`claude -p` per run with **no tools** (answered from the text alone). 3 runs × Sonnet/Opus × 2 arms.

| arm | width = 800 | height = 450 | pointer in the 800px file = 121,216 |
|---|---|---|---|
| `old` — `…-800px.jpg at 800px width, or -original.jpg at 1920x1080px` | 6/6 | 6/6 | 5/6 (one Sonnet arithmetic slip) |
| `new` — `…-800px.jpg, or -original.jpg at 1920x1080px` | 6/6 | 6/6 | 6/6 |

In the new arm 3 of 6 answers say that it is inferred ("the message doesn't say", "longest side"),
which gives the same number on a landscape screen. In both arms, every run raised the same doubt: which
coordinate space is `🖱️@290:518` in? All of them assumed the original's pixels, and that is correct
(`ScreenCapture.pixels`). Shipped: `new`.
