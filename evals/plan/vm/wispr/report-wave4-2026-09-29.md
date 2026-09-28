# Wispr as engine: lab wave 4 (2026-09-29 night, Tart guest `wt-lab`, real Wispr Flow)

**Verdict: NOT YET — one relay defect from GO.** B2, D2 and E are fixed on real Wispr, and the
auto fallback (p98) worked in every case where Wispr stalled, quit or was not running. Two things
block: **F1**, one cross-destination paste (a Q14 answer at the caret instead of the bound terminal,
TW4 run 1); and **E-FP**, one false ghost-mic dismissal (Wispr dismissed while finishing the relay's
own sentence; the auto fallback rescued the words). Finding A still happens, only on BlackHole:
none of the three restart steps brings audio back. Written by the session from the driver's
hand-back; raw data in `2026-09-29-wave4/` (commit d55d943).

## Setup

- **Build 051baed** (master: 233c357 + the restart-gate `raw_transcript` change), built on the host
  from `git archive` with `WALKIE_STAGING=<scratch> ./build-app.sh --stage-only` (needs a
  `victor-mac-kit` symlink beside the archive), tar'd into the guest; grants held.
- **Mirror** `~/wt-lab` from the same archive (`MIRROR_HEAD` 051baed).
- **Guest-only rig edits** (`guest-rig-patches.diff`): `cases_w4real` in the harness module list;
  a `WT_SOAK_GAP` knob (TS3 with 2 s gaps); TX8b/TX10 print the TextEdit text in their evidence.
- **Runner** `run-w4phase.sh`, `WT_LAB=1 HANDS_OFF=1 WT_ALLOW_WISPR_KILL=1 WT_LOOPBACK="BlackHole 2ch"
  WT_KEEP_TAKES=1`, driven by `chain-w4.sh`; each phase: drain, ghost check, local model warm,
  Engine = wispr, 440 Hz check.
- **ElevenLabs:** guest key commented out for the run, restored identical; 0 calls to
  `api.elevenlabs.io` (fake Scribe did all the ElevenLabs work).
- **First attempt aborted (`aborted1/`):** launched over SSH, the harness's Python reads exact zeros
  from BlackHole (no microphone grant for the `sshd-keygen-wrapper` chain); TM1/TM2 SKIPped. Relaunched
  through `tart exec` (alive this boot). Also fixed: the chain's `warm()` posted `{}` to
  `/test/whisper` (never loads the helper) → `{"restart":true}`, up in 60 s.

| phase | ids | ran (UTC) | host mean | host max | guest max |
|---|---|---|---|---|---|
| W4a | TM1, TM2, TW1, TW4, TW8a/b, TW12, TW20, TW33–TW40, TN4 | 22:10–22:49 | 11.7 | 17.1 | 3.8 |
| W4b | TX2, TX3, TX6b, TX8a, TX8b, TX10, TX13 | 22:49–22:58 | 10.1 | 14.0 | 3.2 |
| W4c | TA1–TA5, TQ1–TQ4 | 22:59–23:07 | 9.6 | 14.1 | 3.4 |
| W4d | TS1, TS2 | 23:07–23:21 | 9.9 | 13.3 | 4.4 |
| W4e | TS3, 2 s gaps | 23:21–23:27 | 10.8 | 16.4 | 2.8 |
| W4f | TW4, TX8b, TX9, TX10 (re-runs) | 23:31–23:41 | 15.0 | 32.5 | 3.0 |

**TQ1–TQ4** (`cases_w4real.py`, new): the auto fallback against the real Wispr; every sentence logs
a `SEC` line (close→words, via, budget, fired). TQ1 six warm sentences; TQ2 Wispr SIGKILLed 3 s into
the sentence then the next start; TQ3 Wispr SIGSTOPped 0.3 s after the stop for 20 s; TQ4 Wispr
killed then a start, then sentences at +2 s and +15 s after Wispr is back.

## Verdicts per case

\* = re-read against the log.

| case | verdict | evidence |
|---|---|---|
| TM1 | FAIL → **PASS\*** (rig) | the case's `did not bring audio back` regex also matches step 2's line, so it stopped after 2 restarts; the app: `mic: closed — … peak 0, 2 tap restart(s) — DEAF`; the full ladder shows in TM2's take |
| TM2 | FAIL → **PASS\*** (rig) | `play()` took ~8 s to make sound on the guest → 3 peak-0 restarts on real silence; `audio came back after restart 3` is the clip starting; words whole |
| TW1 | PASS | listening from 0.14 s for 2.4 s |
| TW4 (W4a) | **BUG, finding F1** | Q14 fallback delivered `local-fallback → caret` |
| TW4 (W4f) | BUG, finding A | chord 2 s after a relaunch, Wispr never opened its mic, relay's take DEAF 12.1 s: 116 buffers, peak 0, 3 restarts, `stays DEAF` |
| TW8a, TW8b | PASS | TW8a delivered by `local-auto` after the E false positive |
| TW12 | BUG, known | as in batch 2 (plan step 3) |
| TW20 | BUG (0.6 s bar) | down in 1.48 s (wave 3: 0.34 s); Wispr killed 2.0 s in, 0.2 s voiced → Recover; next sentence via Q14 in 4.3 s after an E dismissal (correct) |
| TW33 | **PASS (D2 fixed)** | A parked, B not refused, A's 537 chars before B, no `dropped` |
| TW34 | PASS | +1/+3/+5 s: 2.0/2.2/2.2 s voiced, 0 restarts |
| TW35–TW38, TW40 | PASS | TW38 WAL latency 4–6 ms; TW40: B waited its turn, witness 3.5 s after the resume |
| TW39 | BUG → **PASS\*** (case timing) | the prompt-panel tail took ~4 s in the guest, his row 2 was already noted (`… 4.2 s into the tail — passes now (B)`) before the ⌘V; correct. (b) pasteboard claim (21 chars) as designed |
| TN4 | PASS | deliveries in order local-fallback, then elevenlabs-scribe |
| TX2 | PASS, loud loss (A) | DEAF from Wispr's mic open: 53 buffers, peak 0, 3 restarts; killed → Recover |
| TX3 | **PASS (E)** | delivered once via `local-auto`; `mic with no capture … at +30 s closed` |
| TX6b | **PASS (E, B-risk)** | once via `local-forced`; Wispr mic closed 10 s after; `👻 … dismissed`, `closed` 1.5 s later |
| TX8a | PASS | relay refused; his words in TextEdit |
| TX8b (W4b) | BUG → **Wispr-side\*** | his `61+60` 0.3 s after the relay's stop never became a Wispr row (rows 237/238 are relay sentences) |
| TX8b (W4f) | BUG → **PASS\*** (case marker) | `TE='Could you get the assumption? '` landed; the case wants *assumptions*, Wispr wrote *assumption* |
| TX9 | PASS | 3/3 at +1 s after a relaunch, via Q14, 2.5–2.7 s voiced |
| TX10 (×2) | BUG → **PASS\* (B2 fixed)** | relay 5/5 in the witness; his 5/5 in TextEdit (`Would you get the assumption? Could you get the assumption? ×4`), `pastedText` agrees on rows 239–247; marker again *assumptions* |
| TX13 | PASS | gate held; the frozen row-248 sentence delivered by `local-auto` 5.1 s after the close; no stray delivery after the restart |
| TA1 | PASS | fake ElevenLabs 20 s late: budget 9.3 s (0 samples, prior × 3); fired 9.35 s; words 12.0 s after the close; late answer only logged |
| TA2–TA5 | PASS | TA3 fired 5.15 s, via local-auto, late row not pasted; TA4 OFF → no budget; TA5 borrowed local, one launch |
| TQ1 | PASS | 6/6 via wispr-history, 0.48–0.64 s, never fired (budgets 2.9–5.5 s) |
| TQ2 | BUG → loud loss | kill at 3 s: the relay's recording closed at the kill, 1.0 s voiced; auto fired at 2.2 s but the take was under the 1.5 s floor → Recover (19 chars); next start borrowed local, 1.26 s |
| TQ3 | PASS | fired 5.5 s (cap for a 15 s take), words 6.90 s, via local-auto, once |
| TQ4 | PASS | Wispr not running: borrowed local 1.64 s, Wispr launched by the relay; +2 s: Wispr row 0.45 s, 1.7 s voiced; +15 s: 0.41 s |
| TS1 | **PASS** | 30/30 wispr-history, recall 1.00, 0 doubled, 0 stuck; close→landed (terminal) p50 5.2 s, p90 6.2 s |
| TS2 | **PASS** | 20/20 at the caret, 0 into the terminal; p50 0.9 s, p90 1.5 s |
| TS3 (2 s gaps) | FAIL → **PASS\*** | relay 10/10, his 9/10, 0 misroutes, 0 stuck; #01 lost on Wispr's side (row 310 `raw_transcript`, duration 0.48 s against an 8.9 s hold, 0 words, no ⌘V); the relay was idle, not in a tail |

## The criteria

| # | criterion | result |
|---|---|---|
| (a) | relay delivery ≥ 95 % | **73/78 = 93.6 %**; excluding the two BlackHole-only DEAF takes (TX2, TW4-W4f): **73/76 = 96.1 %**. Other losses: TW4 caret paste (F1), two kills with < 1.5 s voiced (TW20, TQ2) → Recover, loudly |
| (b) | 0 cross-destination paste | **NOT MET: 1** (F1: 77 chars at the caret instead of ttys001). TX10 ×2, TX8a/b, TS3: 0 misroutes |
| (c) | 0 doubled paste | **MET.** 0 doubled in the soaks; late answers only logged (TA1, TA3, TQ3); TX13 no stray delivery |
| (d) | his `61+60` in the tail delivered | **MET for the relay.** TX10 5/5 ×2, TX8b 1/1, TW8a/b, TS2 20/20, TS3 9/10; the misses are Wispr making no row (TX8b W4b) or a 0.48 s `raw_transcript` row (TS3 #01) |
| (e) | no fallback answer dropped; nothing stranded | **MET.** TW33, TW40, TN4; 0 `dropped`, 0 `wait for the one before` |
| (f) | voiced audio within 5 s of a Wispr launch | **7/8.** TW34 3/3, TX9 3/3, TQ4 +2 s; TW4-W4f DEAF at +2 s (A, BlackHole) |
| (g) | refused 🔽→ does not flip the toggle | not re-run; wave 3's TW11 PASS stands |

## Latency: time to text (quiet guest)

| path | n | p50 | p90 | range |
|---|---|---|---|---|
| **Wispr row, relay** | 62 | **0.61 s** | **1.80 s** | 0.38–2.14 s (wave 3: 0.98 / 2.2 s) |
| auto p98 hand-over (`local-auto`), real Wispr | 5 | 5.3 s | 6.9 s | 4.9–6.9 s |
| Q14 `local-fallback` (Wispr never opened its mic / ignored the chord) | 5 | 4.6 s | 6.3 s | 4.3–6.3 s |
| borrowed local at the start (Wispr not running) | 2 | | | 1.26 s, 1.64 s |
| local decode alone, warm | 19 | 1.47 s | | max 8.45 s |
| into the terminal, relay (TS1; settle + typing) | 30 | 5.2 s | 6.2 s | |
| his standalone at the caret (TS2) | 20 | 0.9 s | 1.5 s | |

## Seconds to local (auto fallback on real Wispr)

| scenario | case | budget | fired at | close → words |
|---|---|---|---|---|
| warm Wispr answering | TQ1 ×6, TQ4 +2/+15 s | 2.9–5.5 s | never | 0.41–0.64 s (Wispr) |
| Wispr frozen after the stop (stalled row) | TQ3 | 5.5 s (cap) | 5.5 s | **6.90 s** |
| Wispr frozen, row 248 processing | TX13 | 3.5 s | 3.9 s | 5.14 s |
| Wispr relaunched, did not answer the chord | TX3 | 3.6 s | 3.8 s | 5.26 s |
| Wispr's own row dismissed by E-FP | TW8a | 3.2 s | 3.3 s | 4.89 s |
| Wispr quit mid-sentence, 1.0 s voiced | TQ2 | 2.1 s | 2.2 s | none: under the 1.5 s floor → Recover |
| Wispr quit mid-sentence, 0.2 s voiced | TW20 | 1.8 s | — | none → Recover |
| Wispr not running at the start | TQ4 cold | — | borrowed | **1.64 s** |
| Wispr just killed, next start | TQ2 next | — | borrowed | **1.26 s** |
| Wispr relaunched by someone else, +1 s | TX9 ×3 | — | Q14 | 4.3–6.3 s |
| fake ElevenLabs 20 s late (0 samples) | TA1 | 9.3 s | 9.35 s | 12.0 s |

In practice a stalled Wispr costs 5–7 s (the 0.3 × audio + 1 s cap for 12–15 s takes); a missing
Wispr costs 1.3–1.6 s.

## Findings

**F1 — a Q14 answer pasted at the caret instead of the bound terminal (the one misroute).** TW4 run 1,
22:17 UTC: `📍 re-bound to ttys001`, 🔼→ at 22:17:04; 22:17:16 `done(timeout) — no row and no microphone
within 12 s` → Q14 decoding 11.8 s; 22:17:20 the case's stop 🔼→ met `🧷 stuck listening? a stop gesture
met it 16.0 s old with no recorder behind it`; same second: `📦 delivery: local-fallback → caret (route)`,
`📋 pasting 77 chars at the caret`. Reading: the stop gesture landing during the Q14 decode, with
`listening` still up after the ring-down, switched the answer to the caret path. TX9's Q14 answers (no
stop mid-decode) all went to the witness.

**E — fixed; the ⌃Esc clears the ghost.** Six dismissals, each followed by `the ghost microphone 1.5 s
after the dismiss: closed`; no ghost relaunch needed (wave 3: one ghost > 14 min).
**E-FP:** 22:17:32 `👻 … 16 s after a relay chord it never answered … dismissing it (⌃Escape)` — the
unanswered chord was TW4's, the mic open belonged to TW8a's relay sentence (chord 22:17:24, mic open
22:17:27, stop 22:17:31, row 227 at 22:17:33); the row was then declared dead and auto p98 delivered
locally at 4.9 s. **Fix:** disarm the watch at the next relay chord; ignore a mic that stays open after
the relay's own stop while its capture is in flight.

**B2 — fixed** (TX10 ×2, TX8b W4f): each of his ⌘Vs logs `passed — row N is newer … (B, Q19)` and
`front: com.apple.TextEdit pid 513; clipboard #46 (the relay's own last write #45)`, then `0.7 s after …
moved (Wispr's restore)`. In TW8a/TW39 `front:` was `com.electron.wispr-flow`: the rig's open-by-path
relaunch brings Wispr to the front — probably wave 3's "TX8b passed, nothing in TextEdit". Case fix:
markers *assumptions* → *assumption*.

**D2 — fixed** against a cold 60 s decode (TW33, TW40).

**A — every `🔁 mic:` line.** Readout identical every time (`mute off, input volume 1.00, nominal 48000 Hz,
tap 48000 Hz, running somewhere yes, IO buffer 512`), same as healthy takes. TX2: first Wispr mic open
after its launch; steps 1/2/3 at +1.3/+3/+5 s all peak 0. TW4-W4f: 2 s after a relaunch, no Wispr mic at
all; all three steps, `stays DEAF`. Every `audio came back after restart N` line (6) is the harness clip
starting late, not a recovery. Healthy first opens after a launch exist (22:17:27, 22:51:50, 23:05:21), so
it is not strictly the first open: a fresh Wispr process sharing BlackHole is enough. **Nothing brings audio
back against BlackHole's shared ring.** Lab-rig recommendation (nothing installed tonight): give the relay
its own BlackHole from a **separate driver bundle** (e.g. the `blackhole-16ch` cask — 0.7.1's statics are
per driver binary), and play each clip into both devices or through a multi-output aggregate. The app
already does the right thing with a DEAF take: says so, keeps it for Recover.

**Other items**
- **Wispr quitting mid-sentence cuts the sentence at the quit**: the relay closes its own recording when
  Wispr's mic closes (TQ2 3.8 s, TW20 2.6 s); the rest is not recorded; < 1.5 s voiced → Recover only.
  Suggestion: keep the relay's mic open until his stop, then decode locally.
- **"Never wait for Wispr" covers only a Wispr the relay launched itself**: TX9 (relaunched by someone
  else, +1 s) paid 4.3–6.3 s through Q14. Use Wispr's process age.
- **TW20:** listening down 1.48 s after the kill (bar 0.6 s; wave 3 0.34 s) — the quit is noticed ~1.4 s
  later (`No words heard — 1408 ms`); likely the quit check lost the 150 ms poll when the WAL watch
  replaced it.
- **Rig:** run the harness only through `tart exec` (over SSH BlackHole reads zeros); TM1's regex; TM2 and
  TW39 timing on a slow guest; TX8b/TX10 markers; the chain's `warm()` must post `restart`.

**State left:** VM down cleanly; ElevenLabs credits untouched (0 real calls); night stamp written 01:50:17
(the 02:00 weekly suite skipped; the gate reads the stamp's age, so automatic runs stay blocked until ~6 Oct);
host app and /Applications untouched; VM headless. Files: `report-lab-W4a…W4f.md`, `run-W4*.log`,
`relay-guest-wave4.log`, `latency-out.txt`, `host-load.log`, `cases_w4real.py`, `guest-rig-patches.diff`, `aborted1/`.
