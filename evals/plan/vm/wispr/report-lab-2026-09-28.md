# Wispr as engine: the lab run of 2026-09-28 (Tart guest `wt-lab`, real Wispr Flow)

> **INTERRUPTED at 11:20 EEST (08:20 guest UTC); resumes tonight after 23:55.** Victor's deadline.
> Ran: W1 (16 IDs), W1r (7 re-runs), W2 partial — see *What ran, what remains* at the end.

The build was the host's `/Applications/Walkie Talkie.app`, with the Wispr fix batch through
`c3c97c0` (the binary carries the Q16 flash and `foreignSentence`). It was deployed into the guest
at 10:16 EEST by the manual tar over SSH; `tart exec` is dead this boot. On launch the log said
`accessibility trusted=true eventTap=true`, the canary was alive at 0.3 ms, and
`POST /test/firewall` answered `alive`, `tap: alive`.

The guest runs Wispr Flow 1.6.957, signed in, with `ptt` = `61+60` and auto-learn off. Its only
input is BlackHole 2ch. The local model (mlx large-v3-turbo) is now present too.
`elevenlabs.env` was re-copied (mode 600, no URL lines) and still carries `WT_WISPR_STANDALONE=1`.
The `~/wt-lab` mirror was refreshed with the `docs/vm-lab.md` tar line.

Phases were launched over SSH with `nohup` through `run-wphase.sh`. That is `run-phase.sh` plus
`WT_ALLOW_WISPR_KILL=1` and an `uptime` sample every 30 s. Its copy, the harness reports, run logs
and load logs are in `2026-09-28/`.

## Verdicts

W1 = first run · W1r = the one re-run of every FAIL/BUG (after the three case fixes below) ·
W2 = the desk set repeated in the lab.

| case | W | W1 | W1r | evidence (latest run) | reading |
|---|---|---|---|---|---|
| TW3 | W15 | SKIP | — | needs standalone OFF | **remains**; README §4.2: retire with Q9 step 2 |
| TW4 | W11 | BUG | **BUG** | re-run: chip named the wait (`Opening…`) True; first-5-words 0/5; relay already idle at the stop | **open, 2/2**: a chord ~2 s after Wispr's relaunch gets no row within 12 s (`it ignored it`). The relay then judges its own 12 s recording `0.0 s voiced` with the clip playing, so Q14 does not stand in and the sentence ends as *No speech* |
| TW6a | W3 | PASS | — | recoverable, no orphan WAV | fixed |
| TW6b | W3 | PASS | — | recoverable, no orphan WAV | fixed |
| TW6c | W3 | BUG* | **PASS** | `📦 delivery: local-fallback`, witness 456 chars | **fixed (Q14)**. *W1: the case asserted the pre-Q14 Recover outcome. The app had logged `2.0 s voiced … the local model stands in`, and the harness cleanup's `/test/cancel` disowned the transcript in flight |
| TW6d | W3 | BUG* | **PASS** | local-fallback delivered, 758 chars, no bare screenshot message | **fixed (Q14)**. *same case fix |
| TW7 | W3/W19 | PASS | — | (a), (b), (c) recoverable, no orphan, no *the sentence is lost* | **fixed**; (c) (Wispr relaunched mid-settle) ran for the first time |
| TW8a | W4 | BUG | **BUG** | outbox +1; his own paste never passed | **open, 2/2, lost on Wispr's side** (finding 3). W1 also counted the relay's own ⌘V drop as a rescue (case timing) |
| TW8b | W4 | PASS | — | his ⌘V passed (`its own sentence (standalone, Q9)`) | passes; but the relay's own sentence came back from Wispr as `How` |
| TW9 | W6 | BUG* | **PASS** | `⚠️ dictate gesture refused — Wispr Flow's microphone is already open`; no sentence opened | **fixed**. *W1: the case's regex missed that wording |
| TW10 | W6 | PASS | — | no ghost row with words, nothing delivered in 40 s | passes as written; see finding 2 (the ghost is a *microphone*, not a row) |
| TW11 | W4 | SKIP | — | needs standalone OFF | **remains** |
| TW15 | W19 | BUG | **BUG** | `spawnPending True`; `not running` flashed | **open, 2/2**: plan step 14 (W19) not done |
| TW16 | W19 | SKIP | — | no helper survived the main process | **remains**: in this guest the kill takes the helper too |
| TW17 | W20 | PASS | — | 0 new Wispr corpus rows; the `Built-in` override *matched no input*, so the relay recorded BlackHole like Wispr | **inconclusive**: the guest has no second input |
| TW20 | W3 | BUG | **BUG** | down in 0.66 s / 0.34 s (Wispr killed at +2 s); *next sentence delivered False* | **mostly case timing**: the next sentence *was* delivered (`📦 delivery: local-fallback → terminal` 6 s after `words landed`), but the case reads the witness at `words landed`. W1's 0.66 s is over the 0.6 s bar, W1r's 0.34 s under it. The kill at +2 s logged `0.1 s voiced … no speech` (as TW4) |

W2 (desk cases in the lab, second sample beside the desk's `report-wispr-fix*.md`):

| case | W | W2 (lab, 08:01–08:18 UTC) | evidence | reading |
|---|---|---|---|---|
| TW1 | W1 | **PASS** | held seen; listening from 0.15 s for 2.4 s; no early release | fixed; matches the desk |
| TW2 | W1 | **PASS** | the stamped tail was ignored | fixed; matches the desk |
| TW5 | W11 | **PASS** | 39/39 samples warming with no row, chip `Opening Wispr Flow...` | fixed (Q20); matches the desk |
| TW7 | W3/W19 | **PASS** | (a), (b), (c) recoverable, no orphan | fixed; second lab sample |
| TW12 | W4 | not finished | killed by the 08:18 cap mid-case (`rc=137`) | **remains**; expected BUG (plan step 3) |
| TW13, TW14, TW19, TW22 | W10, W9, —, W2 | not run | — | **remain** |

The first W2 attempt (07:55–07:58, *contaminated* by the ghost microphone of finding 2) gave TW1 BUG,
TW2 PASS, TW5 PASS (false: no sentence opened), TW7 ERROR. It is superseded by the table above;
files kept as `2026-09-28/*-W2-contaminated.*`.

### The case fixes (applied to `evals/plan/cases_wispr.py` in this commit)

- **TW4**: `opening` joins the chip regex (Q20's `Opening Wispr Flow...`, as TW5 already has it).
  The stop toggle is sent only while the relay is still listening. In W1 the stop went to a relay
  that had given up at 12 s and *opened* a stray sentence. It ran to the 10-minute ceiling, with
  Wispr's row 8 open alongside it for the whole 10 min, and the phase lost 9 min.
- **TW6c/d**: per Q14, a `📦 delivery: local-fallback` with text in the witness is a PASS; Recover
  still counts for a recording under the floor.
- **TW9**: `microphone is already open` joins the refusal regex (the W6 wording).
- **Proposed, not applied — TW20**: wait for witness text (`wait_for(lambda:
  witness_text().strip(), 40)`), not `wait_delivered`, before judging *next sentence delivered*.
- **Proposed, not applied — TW8a**: take `m2` after the relay's own ⌘V has been dropped, which
  lands ~1.1 s after the close. Or match only drop lines that name a row newer than the relay's.

## Findings

### 1. A bound delivery to the witness tab always ends with a Return

Every bound delivery in the guest logged:

```
⚠️ ⌨️ ttysNNN: the typed keys never showed in the tab — falling back to do script, which presses Return
⚠️ ⌨️ delivered with a Return — the typed keys never showed in the tab
```

That is 8 of 8 terminal deliveries since the 10:16 deploy. It contradicts the no-Return rule of
`9f8e49b` (Victor's other session, 08:49: *bound delivery presses no Return … unseen → the old do
script delivery*). The host's own log (read-only) shows the same line 13 times today, and every
time the foreground program is `cat`. Deliveries to `claude` tabs never fell back.

The witness tab runs `stty -echo; exec cat`, so a read-back that waits for the typed keys to show
in the tab can never see them. The likely reading is that **the witness rig forces the do-script
fallback**. Two consequences follow:

- (a) No harness case exercises the typed, no-Return path.
- (b) The typed keys may reach `cat` *and* `do script` may send the text a second time.

(b) is unverified: witness sizes (456, 758 chars for one sentence with an area shot) are not
obviously doubled, but nobody diffed them.

The guest's Terminal is 2.14 and may behave differently from the host's. Candidate fix: the
read-back also accepts the tty's input having been consumed when the foreground is `cat`, or the
witness keeps echo on.

### 2. The ghost microphone after a Wispr relaunch (W6, still open)

After TW20's relaunch, the relay's first chord got its Wispr row only at the close (8.7 s after
the chord). Wispr never opened its microphone, and the relay rightly fell back to the local model.

Then, 10–20 s later, **Wispr opened its microphone by itself and held it open**. The log said
`⚡ Wispr opened its microphone for a sentence of its own — left to Wispr (Q9)`, at 07:53:00 and
at 07:55:42. The mic stayed open until the next relaunch: 07:53:28 by TW4, and 07:58 by hand the
second time.

This is the blind toggle to a cold Wispr, arriving late (W6). While it stood, every relay start
was refused with `Wispr Flow's microphone is already open`, which contaminated the first W2
attempt:

- TW1 BUG: the ⌘⌥ hold was refused.
- TW5: a false PASS, since no sentence ever opened.
- TW7: ERROR, `prompt panel paused by the pointer`.

That attempt was stopped and Wispr relaunched (`micOpen` → false), then W2 was run again. The
contaminated files are kept as `2026-09-28/*-W2-contaminated.*`. TW10 does not see this: it
asserts *no row with words within 40 s*, and the ghost has no row with words, only an open
microphone. A case for it is to relaunch Wispr, 🔼→ at once, stop, then assert
`wisprLive.micOpen` is false 30 s later.

### 3. Wispr lost the words (counts, this run)

- **2 of 2 of his `61+60` sentences started ~1 s after the relay's stop were lost** (TW8a):
  - Run 1: row 14 stayed `status NULL` forever, with no ⌘V and no paste.
  - Run 2: his chord made no row at all. Wispr had been relaunched 10 s before, and the relay's
    own sentence (row 21) had no microphone either.
- **1 relay sentence came back truncated**: row 15 (TW8b) = `How`, 3 characters from the
  11-word CLIP_EN.
- **3 relay sentences right after a relaunch got a row only at the close and never a
  microphone** (rows 19, 21, 23). All 3 were delivered by the Q14 local fallback, so these lost
  nothing for Victor.
- **2 of 2 cold first chords (TW4) got no row within 12 s.** The relay then judged its own
  recording `0.0 s voiced` with CLIP_SPEECH playing, so Q14 did not stand in. The `0.1 s` of
  TW20's 2 s of clip is the same pattern.
  - Whether the meter under-counts early in a sentence or the playback started late is not known.
  - Under 0.3 s voiced the WAV is deleted by design, so nothing is left to check.
  - For comparison, the 6 s of TW6c/d measured 2.0 s voiced and CLIP_EN measured 1.8 s.

### 4. Main-thread stalls right after a Wispr relaunch

In TW4 (W1) the main thread went silent for 3.0–12.4 s five times in 50 s. The 12.4 s stall was
at the gesture itself. `hangs/hang-2026-09-28-07-18-31.txt` was sampled a minute late and shows
only an idle main thread. Guest load was 7.6 then.

## Guest load (`uptime` every 30 s, `2026-09-28/load-*.log`)

| phase | 1-min load | over ~6 |
|---|---|---|
| W1 (07:17–07:53 UTC) | 1.4–8.7 | 07:18 (7.6, the first Wispr relaunch), 07:51 (8.7, TW10's relaunch) |
| W1r (07:53–07:56) | 4.5–13.4 | **07:54–07:55 at 12.9–13.4**: TW6c/d, TW8a and TW9 ran under it. Their verdicts are about *which path* ran, not speed, so they stand. The local decode rates in that minute (0.18–0.52×) are speed-contaminated |
| W2 | 1.20–2.17 (never over 6) | |

Every `/test/wispr-proc relaunch` is what pushes the load past 6.

## Fixed vs open

- **Fixed, confirmed in the lab:**
  - W3: TW6a–d, TW7 (a)(b)(c).
  - W6's refusal: TW9.
  - W1: TW1/TW2 (W2 sample).
  - W11's chip: TW4's `Opening…` and TW5 (W2 sample).
- **Open:**
  - W4: TW8a, lost on Wispr's side, 2/2.
  - W11: TW4's cold chord with Q14 not standing in, 2/2.
  - W19: TW15, 2/2.
  - W6 ghost microphone after a relaunch: finding 2, no case yet.
  - W4/W-D7: TW12, expected BUG since plan step 3 is not done.
  - Finding 1 (Return on witness deliveries).

## Desk vs lab

- **Now covered by the lab:** W3 on a real Wispr quit (TW6c/d, TW7c), the W6 refusal (TW9), W19's
  spawn flag (TW15).
- **Lab-only, still open:** TW8a, TW4, the ghost microphone.
- **Lab-only, not run:** TW3 and TW11 (need standalone off), TW16 (the helper does not survive the
  kill here), TW17 (no second input in the guest).
- **Desk cases:** the W2 table above is their second, lab, sample.

## What ran, what remains

| | IDs |
|---|---|
| **ran once (W1)** | TW3 (SKIP), TW4, TW6a, TW6b, TW6c, TW6d, TW7, TW8a, TW8b, TW9, TW10, TW11 (SKIP), TW15, TW16 (SKIP), TW17, TW20 |
| **re-runs (W1r)** | TW4, TW6c, TW6d, TW8a, TW9, TW15, TW20 |
| **ran in W2 (lab sample of the desk set)** | TW1, TW2, TW5, TW7 |
| **remain for tonight** | TW12 (was mid-run at the cap), TW13, TW14, TW19, TW22 (W2's rest), then a re-run of any new FAIL/BUG among them; TW3 and TW11 need a standalone-off pass (`WT_WISPR_STANDALONE` commented out in the guest's `elevenlabs.env`); TW16 needs a helper that survives the kill; TW17 needs a second input in the guest |

**State left:** the harness was SIGKILLed by the cap (`rc=137`), so it did not put the Engine back:
the guest app was left on `Whisper (local)`, `busy` with staged Recover audio (expires in 5 min), at the
cap. The fake-Wispr block and the chord mute were already cleared. **The guest was NOT shut
down**: the `sudo shutdown -h now` over SSH was refused by this session's permission classifier, so
`wt-lab` is still running (Wispr signed in; never reset, cloned or baked) — a human shutdown is
pending. Tonight: if it was restarted, `tart run` anew brings `tart exec` back; then
`POST /engine {"id":"wispr"}`, then
`run-wphase.sh W2b 1800 "TW12,TW13,TW14,TW19,TW22"`.
