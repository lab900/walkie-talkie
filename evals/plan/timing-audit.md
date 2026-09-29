# Timing audit — why the Wispr / lab suite takes so long (2026-09-29)

Victor: *"why do these tests take so long?"* — then *"have you sped up the tests?"*. The honest
answer was: not the cases. This audit reads the raw logs of lab waves 4 and 5
(`vm/wispr/2026-09-29-wave{4,5}/run-*.log` for each case's seconds, `relay-guest-wave{4,5}.log`
for where they went), finds every sleep and timeout in the cases wave 5 ran, and sets each one
from a measured number.

## Where the time went

| wave | harness wall | sum of case seconds | between cases | of which: waiting out the harness's own Recover staging |
|---|---|---|---|---|
| 4 (W4a–f) | 5 133 s | 3 520 s | 1 613 s | **1 537 s** between cases + **420 s** inside 7 cases (`engine_back`) |
| 5 (W5a–e, t) | 2 762 s | 2 150 s | 612 s | **569 s** between cases + at exit, + **181 s** inside 3 cases |

**The one big finding: `busy` includes *audio staged for Recover*, for five minutes.** Every case
that ends in a cancel (a DEAF take, a quit mid-sentence, a `/test/cancel` in cleanup) stages its WAV
for Recover; `restartBlockers` keeps `busy` true until the five minutes are up (a restart would
wipe `cancelled/`). The harness read `busy` in three places:

1. `engine_back` → `set_engine` → `wait_for(not busy, 60)` — **60 s inside the case's own time**, then
   the switch went through anyway (`setEngine` refuses only mid-sentence). W5a: TW20, TW41, TA6
   (`01:22:54`, `01:27:14`, `01:33:19` — each exactly 60 s after the case's last line).
2. `wait_idle()` before the next case — the rest of the five minutes (W5a: 169 s, 219 s).
3. `eleven_teardown` at exit — `wait_for(not busy, 120)` + `set_engine`'s 60 s = 181 s (W5a
   `01:33:19 → 01:36:20`).

W5a ran 1 142 s for 562 s of cases; W4a 2 335 s for 970 s. Nothing in the app was being waited for.

**Fix** (`harness.py`, `relay_busy()` / `busy_why()`): the harness's *own* staging is ignored —
a WAV staged while a case was running (its `expiresAt − 300 s` ≥ the case's start), remembered
after the case in `OWN_RECOVER`; in the Tart guest every staging is the harness's. A staging it did
not make — Victor cancelled a sentence before the run or between two cases — is still waited out,
because the next case's cancel would replace his file (`keepCancelled` keeps one). Every settle wait
that read `state()["busy"]` (`wait_idle`, `set_engine`, `eleven_teardown`, `cases_audio.settle_out` /
`rig` / `engine_as`, nine in `cases_wispr`) reads `relay_busy()` now. Assertions that *observe* `busy`
(TD24, the lifecycle gate cases) are untouched.

## The knob and the rule

`tmo(path)` = (measured p99 × 1.5 + 1 s) × `WT_HARNESS_SLOW`. Default 1.0 at the desk; the guest
drivers (`vm/night/run-phase.sh`, `vm/wispr/run-w5phase.sh`) export 1.5. The p99s live in one table,
`harness.P99` — with n this small the max seen in waves 3–5 stands in for the p99:

| path (`P99` key) | what it waits on | measured (waves 3–5, guest) | p99 used | `tmo` desk / guest |
|---|---|---|---|---|
| `mic_open` | gesture → `mic: recording through` | < 1 s warm; **10 s** behind the 6 s main-thread stall after a Wispr relaunch (W5a TW4) | 10.0 | 16.0 / 24.0 s |
| `wispr_row` | close → words from Wispr's row | p50 0.61–0.98, p90 1.80–2.2, max 2.92 s (n = 46–62) | 3.0 | 5.5 / 8.3 s |
| `caret` | his standalone sentence → pasted at TextEdit | p50 0.9–1.2, p90 1.5–2.6 s | 3.0 | 5.5 / 8.3 s |
| `local` | one local decode, warm | p50 1.47–1.57, max 8.45 s | 8.5 | 13.8 / 20.6 s |
| `q14` | close → words via Q14 / local-auto | p50 4.5–5.3, wave 3 max 11.1 s | 11.1 | 17.7 / 26.5 s |
| `terminal` | close → the words *in* the witness tab | p50 5.2–5.8, p90 6.2–6.4 s | 7.0 | 11.5 / 17.3 s |
| `q14_terminal` | Q14 words + the typing into the witness | 11.1 + ~5 s | 16.0 | 25.0 / 37.5 s |
| `wispr_relaunch` | relaunch → new pid + `/engine.ready` | 1.0–1.2 s (TX3); **14.5 s** (W5a TW4) | 15.0 | 23.5 / 35.3 s |
| `recover_staged` | a cancel → `state.recoverable` | same log second | 1.0 | 2.5 / 3.8 s |

**What is not a timeout and is never scaled or cut:** a SIGSTOP's length (TX1 8 s, TX13 240 s
dead-man, TQ3 20 s), a soak's gap (TS1 3 s, TS3 1–6 s seeded — the case's spec), the stimulus
timing a case is *about* (TW4's 0.5 s after `ready`, TW41's 13 s / 15 s against the 12 s give-up,
TX9's 1 s after a relaunch, TQ4's +2 s / +15 s), the app's own constants a case steps over (the 2 s
stop dwell → `sleep(2.2)`; the 1 s selection tick), and every **watch window for something that
must not happen** (TX6's 10 s ghost-mic watch, TX3's 30 s, TW10's 40 s, TW19's 6 s late row, the
chaos cases' post-end grace for a second copy). And **the chaos cases' `_wait_end(mark, 45–120)`
stays**: past it `_after` reads `_still_up()`, so that number is the definition of *stuck*, not
slack — cutting it would turn a slow settle into a FAIL.

## Per case — wave 5's list

Seconds are the harness's per-case time (`run-W*.log`); **stall** = the 60 s `engine_back` wait on
the case's own Recover staging, now gone. *Round* = a number nobody measured; *load-bearing* = what
the case must wait out.

| case | W4 s | W5 s | sleeps / timeouts in the case | load-bearing · round | p99 of what it waits on | proposed | est. W5 after |
|---|---|---|---|---|---|---|---|
| TW4 | 20.7 · 105.4 (+60 stall) | 95.7 · 56.3 | relaunch wait 30 · 0.5 after ready · 0.2 + clip + 1.0 · `wait_delivered` 45 | 0.5 / clip / 1.0 = stimulus (load-bearing); 30, 45 round | relaunch 14.5 s; Q14 11.1 s | `tmo("wispr_relaunch")`, `wait_delivered()` = `tmo("q14")` | 95.7 · 56.3 (both waits ended on their line; the 55 s take is the guest's `play()` starting 36 s late) |
| TW8a | 27.4 | 27.9 | `dictate_loopback` (mic ≤ 8, 0.4, clip, 2.0 tail) · drop line ≤ 3 · **`sleep(6)`** after his ptt | 2.0 tail + the 1 s offset = stimulus; 6 round | his ⌘V verdict line 1–2 s after his release (W5a `01:19:20`) | `when(m2, passed｜dropped, tmo("caret"))` + 1 s | ~23 |
| TW11 | — | 64.5 | 0.5 · clip 8 s · 0.3 · 0.4 · clip 3 s · 0.5 · **wait 2 deliveries ≤ 45** · 3 | gestures' spacing = stimulus; 45 round — and **ran out on the PASS path**: B refused out loud, only A delivers | A: `terminal` 7 s | wait also ends on *A delivered + B refused + witness*; `tmo("q14_terminal")` | ~23 |
| TW20 | 86.7 (+60 stall) | 138.3 (+60 stall) | ownTake ≤ 5 · clip join 15 · **witness ≤ 40** · **📦 ≤ 10** · relaunch ≤ 30 · 3 · next sentence · witness ≤ 40 | 5 = the case's 0.6 s bar's window; 40 + 10 ran out on every BUG run (0.2–0.5 s voiced → Recover, nothing will ever land); 3 after relaunch round, kept | Q14 + typing 16 s | witness wait also ends on `kept for Recover｜No words…｜dictation abandoned`; 📦 wait only if words came; `tmo` | ~28 |
| TW41 | — | 90.6 (+60 stall) | 1.0 · 1.5 · until 13 s · until 15 s · witness ≤ 40 · 📦 ≤ 10 | 13 / 15 s = the case (F1's 12 s give-up); 1.0 / 1.5 kept | Q14 11.1 s | stall gone | ~31 |
| TW42 | — | 50.2 | 3.0 · 2.0 · clip joins · 2.2 ×2 · witness ≤ 40 · `_landed` ≤ 40 · 15 · 15 | 3.0 / 2.0 stimulus + 2 s observation; 2.2 = past the 2 s stop dwell | — | unchanged (all end on their condition) | 50.2 |
| TW43 | — | 15.8 | 0.3 · clip · 0.5 · capture ≤ 5 · `_landed` ≤ 40 | 0.5 = "the exit 0.5 s later" (stimulus) | — | unchanged | 15.8 |
| TA6 | — | 78.8 (+60 stall) | chip ≤ 3 · 0.4 · clip · 0.6 · witness ≤ 40 · 📦 ≤ 10 · 20 · 1.5 · 0.8 | 0.8 = the "not borrowed" observation; 1.5 round, kept | — | stall gone (its second start's `/test/cancel` staged Recover) | ~19 |
| TX3 | 42.1 | 39.2 | relaunch · 0.4 · clip · 0.8 · `_wait_end` 45 · **30 s ghost watch** · 1.5 | 30 s = finding E's window (mic opened at +11 s): load-bearing | — | unchanged | 39.2 |
| TX6b | 60.6 | 22.0 | 0.4 · 0.2 chords · 0.3 · clip · 0.8 · `_wait_end` 60 · **10** | 10 = the ghost-mic watch; 60 = stuck | — | unchanged | 22.0 |
| TX9 | 176.4 | 58.8 | ×3: relaunch + **1.0** · 0.2 · clip 8 s · 0.6 · `_wait_end` 60 · 2 · `_unrig` | 1.0 = the case ("1 s after a relaunch"); 2 = grace for a second copy | — | unchanged | 58.8 |
| TX13 | 108.7 | 169.7 | 2.0 at the freeze · dry-run `--max-wait 10` · `_quiet` 45 · **Recover staged ≤ 8** (×2: one hit, one empty pass) · restart ≤ 120 · `/up` ≤ 60 · late row ≤ 40 · **5** · next sentence `_wait_end` 60 · 5 | max-wait 10 > the gate's 5 s inactivity (a shorter one would "hold" for the wrong reason); 5 s = the stray-delivery window; 8 round | staged in the cancel's log second | `tmo("recover_staged")` | ~165 (the rest is the app: restart, a cold helper's 57.6 s first decode) |
| TQ2 | 76.1 | 78.2 | `_one`: 0.4 · clip bg · kill at 3 · `_wait_end` 75 · 3 · `_unrig` (Recover drained ≤ 45) · 1.0 · `_one` next · Wispr up ≤ 60 | 3 = kill offset (stimulus); 75 = stuck | — | unchanged | 78.2 |
| TQ4 | 58.3 | 58.4 | kill · 1.0 · `_one` ×3 (+3 grace each) · up ≤ 90 · **2** · **15** | 2 / 15 = the case (+2 s, +15 s after Wispr is up) | — | unchanged | 58.4 |
| TS1 | 560.2 | 567.0 | ×30: 0.4 · clip (3.5 / 5.9 s + 1 s pads) · 1.2 tail · `_watch` (words + 1.2 + 1.0 quiet) · `_quiet` · **3 gap** | all per-sentence waits end on conditions; 3 s gap and 1.2 tail = the spec | terminal p50 5.8 s | **`WT_SOAK_N`** (default 30, unchanged) | 567 (18.9 s / sentence; `TS1=10` → ~195) |
| TS3 | 357.7 | 322.8 | ×20, as TS1, gaps 1–6 s seeded (`WT_SOAK_GAP=2` in wave 5) | gaps = the spec (inside the 10 s tail) | — | **`WT_SOAK_N`** (default 20) | 323 (16.1 s / sentence; `TS3=8` → ~135) |
| TM1 | 38.1 | 23.7 | give-up ≤ 15 · closed ≤ 10 · `settle_out` 60 | all conditions | — | `settle_out` → `relay_busy` | 23.7 |
| TM2 | 24.4 | 24.4 | ready ≤ 90 · **1.6** · clip · 1.0 · delivered ≤ 60 · `settle_out` 60 | 1.6 = past the 1 s peak-0 beat (the case) | — | as TM1 | 24.4 |
| TW39 | 29.2 | 22.9 | 2.5 ×2 · waits ≤ 15 / 6 / 8 · `busy` ≤ 15 · 2.2 · 0.5 · 1.5 | 2.5 = a row within ~1 s of the relay's chord is the relay's (B-risk); 2.2 = stop dwell; 0.5 / 1.5 = the claim's windows | — | the busy wait → `relay_busy` | 22.9 |
| TX8b | 50.4 · 21.0 | 50.9 | 0.3 · 0.4 · clip · 0.6 · 0.3 · 0.4 · his clip 5 s · 1.0 · `_wait_end` 60 · **TextEdit ≤ 30** · 4 | 30 round — and **ran out every BUG run** (his sentence lost on Wispr's side, TextEdit stays empty); 4 = grace for a second copy | his sentence at the caret p90 1.5–2.6 s, and the wait starts after the relay's own sentence has ended | `tmo("caret")` (5.5 / 8.3 s) | ~29 |
| TX10 | 93.5 · 94.4 | 93.3 | ×10 (0.4 · clip · 0.6 · 2.0 gap / ptt 0.4 · clip 4 s · 0.8 · 2.0) · `_wait_end` 60 · `_really_busy` ≤ 60 · **8** | gaps = the case ("2 s gaps"); 8 round (his last sentence's paste + late copies) — kept: it is also the misroute watch | — | unchanged | 93.3 |

**Also tightened outside wave 5's list** (same rules): TX8a's TextEdit wait (30 → `tmo("caret")`),
TW8b (`wait_delivered()`), every `dictate_loopback` (mic 8 → `tmo("mic_open")`, longer in the
guest: the 10 s post-relaunch stall would have ERRORed at 8).

## Wave 5, before → after

| phase | before | after (est.) | where |
|---|---|---|---|
| W5a | 1 142 s | ~300 s | 569 s between cases + at exit, 3 × 60 s stalls, TW11 −41 s, TW20 −50 s, TW8a −5 s |
| W5b | 359 s | ~355 s | TX13 −4 s |
| W5c | 141 s | 141 s | — |
| W5t (TS1) | 572 s | 572 s | `WT_SOAK_N` unset |
| W5e (TS3) | 328 s | 328 s | `WT_SOAK_N` unset |
| W5d | 220 s | ~198 s | TX8b −22 s |
| **total** | **2 762 s (46 min)** | **~1 895 s (32 min)** | −31 %; with `WT_SOAK_N=TS1=10,TS3=8` ~1 320 s (22 min) |

Wave 4 on the same arithmetic: 5 133 s → ~3 150 s (W4a alone 2 335 → ~655 s: six Recover stalls
and 1 321 s of `wait_idle`).

## Left slow on purpose

- **The soak lengths** (TS1 30, TS3 20): the rates are what the case measures; `WT_SOAK_N` shortens a
  smoke run, the default stays wave 5's.
- **`_wait_end`'s 45–120 s in the chaos cases and `STUCK_S` = 60 in the soak**: they define *stuck*.
- **The watch windows** (TX3 30 s, TX6 10 s, TW10 40 s, TW19 6 s, TX10 8 s, TX13 5 s, every
  post-end grace): an absence cannot be waited for on a condition; shortening one weakens the case.
- **TX13's `--max-wait 10` dry run**: below the gate's 5 s inactivity rule it would "hold" for the
  wrong reason.
- **`_unrig`'s Recover drain** (POST `/test/recover` into the witness after the verdict): it existed
  only because a staged file held `busy`; with `relay_busy` it is no longer needed for speed and could
  go (~5–10 s per chaos case that ends in Recover) — left in, because it is the only place Recover is
  exercised end to end in the lab, and it is outside every assertion.
- **The app's own latency**: ~5.5 s of every relay sentence is typing into the witness tab (TS1
  p50 5.8 s); TX13's next sentence meets a cold helper (57.6 s).

## Side effects to know

- **A run can leave its last Recover staged**: waves 4–5 waited it out by accident (181 s at exit);
  now `relay-restart.sh` right after a desk run may wait up to five minutes on the harness's own file.
- **TX13's next sentence has 2.4 s of headroom** (`_wait_end(m2, 60)` against a measured 57.6 s cold
  decode). Left at 60 — it is also that case's *stuck* bar — but it is the next flake.
- **`--changed-since`** (`README.md`) skips a case whose `covers` did not change: after a commit that
  touches only `StatusItem`, `CaretHalo`, `LiveCaptionBand` or docs, every Wispr / lab case SKIPs.
