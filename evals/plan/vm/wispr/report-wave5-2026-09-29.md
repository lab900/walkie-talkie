# Wispr as engine: lab wave 5 (2026-09-29 night, Tart guest `wt-lab`, real Wispr Flow)

**Verdict: YES — go on all seven criteria (a)–(g), on build 5661ca4.** One follow-up does not block:
fix-batch-4 item 3 (a quit is not his stop) did not hold on a real SIGKILL mid-sentence (TW20, TQ2);
both takes it cost were announced and kept for Recover, never lost silently. Written by the session
from the driver's hand-back; raw data in `2026-09-29-wave5/` (commit 61e0f25). The restore followed
at 05:10 (`5ed6aa1`, `StatusItem.wisprEngineDefault = true`).

## Setup
- **Build 5661ca4** (batch 4), `git archive` + `WALKIE_STAGING=<scratch> ./build-app.sh --stage-only`,
  tar'd into the guest (previous bundle kept as `Walkie Talkie.app.prev-w4`); `~/wt-lab` from the same
  archive. Host app and host `/Applications` untouched.
- **Chain:** batch 4's `chain-wave5.sh` + `run-w5phase.sh` + `bhcheck.py`, launched only through
  `tart exec`; 440 Hz check fine before every phase (peak 0.3). Driver's edits: TS1 in full as W5t,
  optional W5d last, a STOP-file guard (edited chain in the raw folder).
- Engine = wispr; local model warm throughout; pf anchor empty at the end.
- **ElevenLabs:** guest key commented out, restored byte-identical (sha 98f5aa7b…); 0 calls to
  `api.elevenlabs.io`.
- **VM:** headless; stopped cleanly (35 s).

| phase | cases | UTC | host load mean / max | guest max |
|---|---|---|---|---|
| W5a | TW41–43, TA6, TW4, TW8a, TW11, TW20 | 01:17–01:36 | 11.5 / 16.6 | 2.2 |
| W5b | TW4, TX3, TX6b, TX9, TX13 | 01:37–01:43 | 10.0 / 11.6 | 2.4 |
| W5c | TQ2, TQ4 | 01:43–01:46 | 10.9 / 14.1 | 2.0 |
| W5t | TS1 (30 sentences) | 01:46–01:55 | 14.2 / 21.1 | 2.1 |
| W5e | TS3, 2 s gaps | 01:55–02:01 | 15.4 / 21.8 | 3.2 |
| W5d | TM1, TM2, TW39, TX8b, TX10 | 02:01–02:05 | 9.1 / 12.9 | 3.6 |

## Specific reads
- **F1 (the one misroute): met.** TW4 run 1 took the F1 path (`💻 Wispr Flow did not answer the chord —
  13.0 s … carries it on until his stop`, no `🧷`, then `📦 local-fallback → terminal:ttys001`); run 2
  never reached Wispr (item 4: `its process is 2.7 s old`, `local-whisper → terminal`). Whole log:
  0 `→ caret` lines, 0 `🧷` lines. Both TW4 runs are marked BUG by the case on "first-5-words 0/5" —
  the rig: the outbox shows the clip's words delivered to ttys001; the case's `play()` started ~35 s
  late on the guest (`audio came back after restart 3 — 36.6 s / 30.7 s after it` is the clip starting).
- **E-FP: met.** `👻 … disarmed — a new relay chord (E-FP)` ×6, including TW8a's chord right after TW4;
  0 `👻 … dismissing` lines. TW8a went out via `local-fallback` in 1.84 s: Wispr's row 345 came back
  `no_audio` from a Wispr relaunched 33 s earlier (finding A on BlackHole); the relay's own take had
  1.7 s voiced; his `61+60` passed.
- **True ghosts (TX3, TX6b): not exercised** — both PASS but no ghost formed (TX3 taken by the local
  model at the start, item 4; TX6b's Wispr mic closed by itself). Wave 4's dismissals stand.
- **Item 5 (kernel exit event): met.** `⚡ Wispr Flow's process … exited — the kernel's exit event` in
  the same second as each kill; TW43 PASS (let go 0.02 s after the exit).
- **Item 3 (a quit is not his stop): NOT met on a real kill.** TW20: kill at 3.0 s → `listening →
  transcribing — the 100 ms poll saw the microphone close (3001 ms)`, `mic: closed`, then the exit
  event → `only 0.5 s voiced … kept for Recover`. TQ2: same at 3.9 s, and the take was DEAF (36 buffers,
  peak 0 — finding A after TX13's SIGSTOP/SIGCONT) → `NO AUDIO … kept for Recover`. No 0.3 s grace
  (`quitCloseGrace` in `closeFromWisprSide`), no `holdOwnTake`. Desk TW42 passed with `fakeExit` only.
  Probable cause (unverified): the guard at `WisprFlowSource.swift:1811` (`… state.pollMs != nil`) did
  not take the close path — both state lines read `Wispr created a row, poll saw it never after the
  chord`, so the close fell through to `state.poll(false)`. Next: check `pollMs`/`hasChord` for a
  relay sentence whose row came before the poll saw the microphone.
- **Item 4 (process age): met.** Sentences started while Wispr was < 12 s old went to the local model
  and landed: TX9 ×3 1.10 / 1.91 / 4.20 s after the close (wave 4: 4.3–6.3 s via Q14); TX3 1.61 s, TQ4
  cold 1.74 s, TQ2's next 1.35 s, TW20's next 1.78 s, TA6 1.29 s.
- **TW11 (criterion g): PASS** — B refused out loud while A settled; A delivered (379 chars).

## Criteria
| # | result |
|---|---|
| (a) relay delivery ≥ 95 % | **MET.** 60/62 = 96.8 %; 60/61 = 98.4 % without the BlackHole-only DEAF take (TQ2). Only losses: TW20 (item 3, 0.5 s voiced) and TQ2 (DEAF + item 3), both said out loud and kept for Recover |
| (b) 0 cross-destination paste | **MET.** 0 `→ caret`; TS3 0/20 misrouted; TX10 relay 5/5 in the witness, his 5/5 in TextEdit; TX8b crossed nothing |
| (c) 0 doubled | **MET.** TS1/TS3 0 doubled; late row 345 `only logged, never a second delivery`; TX13 no stray delivery after the restart |
| (d) his `61+60` sentences delivered | **MET for the relay: 19/19** (TS3 13/13, TX10 5/5, TW8a 1/1). Wispr-side, TX8b: his `61+60` 0.3 s after the relay's stop never became a Wispr row (as wave 4 W4b); the dropped ⌘V at 02:02:43 was the relay's own late one |
| (e) nothing dropped / stranded | **MET.** 0 `wait for the one before`; the 11 `⌘V … dropped` lines are the firewall blocking Wispr's paste for relay rows (by design). Noted: after the TX13 app restart the next sentence took 57.6 s — cold helper loaded at 01:43:14; delivered, late |
| (f) voiced audio within 5 s of a launch | **MET, 6/6** (TX3, TX9 ×3, TW20's next, TQ4 +2 s). TW4 run 2 read zeros ~6 s after a launch but the clip had not started. BlackHole DEAF only in TQ2 (after SIGSTOP/SIGCONT) |
| (g) refused 🔽→ no toggle flip | **MET** (TW11) |

## Case list
PASS: TW41, TW42, TW43, TA6, TW8a, TW11, TX3, TX6b, TX9, TX13, TQ4, TS1 (30/30 wispr-history, recall
1.00, 0 stuck), TS3 (20/20: relay 7, his 13), TM1, TM2, TW39, TX10. BUG rig: TW4 ×2. BUG Wispr-side:
TX8b. **BUG real: TW20, TQ2 (item 3).**

## Latency (time to text, quiet guest)
| path | n | p50 | p90 / range |
|---|---|---|---|
| Wispr row, relay | 46 | 0.81 s | 1.92 s (0.40–2.92) |
| local model at the start (Wispr < 12 s old or not running) | 9 | 1.61 s | 1.10–4.20 s (TW4 run 2: 3.45 s on a 49 s take) |
| Q14 `local-fallback` | 5 | 4.49 s | 1.84–4.49 s (+ TX13's cold helper 57.6 s) |
| `local-auto` (budget ran out) | 1 | 5.27 s | TX13 frozen row, budget 3.7 s, fired 3.9 s |
| `local-forced` (TX6b) | 1 | 4.09 s | |
| into the terminal, relay (TS1; settle + typing) | 30 | 5.8 s | 6.4 s |
| his standalone at the caret (TS3) | 13 | ~1.2 s | 0.6–2.6 s |
| local decode alone | 13 | 1.57 s | max 5.09 s (cold) |

## Seconds to local
| scenario | case | budget | fired at | close → words |
|---|---|---|---|---|
| warm Wispr answering | TQ4 +2/+15 s, TS1 | 2.9 s | never | 0.51–0.54 s |
| Wispr frozen, row processing | TX13 | 3.7 s | 3.9 s | 5.27 s |
| Wispr ignored the chord (F1 path) | TW4 run 1 | — | Q14 at his stop | 4.49 s (55 s take) |
| Wispr `no_audio` row | TW8a | — | Q14 | 1.84 s |
| Wispr < 12 s old / not running | TX9, TX3, TQ4, TQ2 next, TW20 next | — | local at the start | 1.10–1.91 s (one 4.20 s) |
| Wispr killed mid-sentence | TW20, TQ2 | 1.9 / 2.2 s | — | none: Recover (item 3 open; TQ2 also DEAF) |
| next sentence after an app restart (cold helper) | TX13 next | — | Q14 | 57.6 s |

## State left
VM stopped cleanly (not cloned/baked/reset/snapshotted); guest ElevenLabs env restored; credits 0;
host load logger stopped. Files in `2026-09-29-wave5/`: `report-lab-W5{a,b,c,t,e,d}.md`, `run-W5*.log`,
`load-W5*.log`, `relay-guest-wave5.log`, `latency-out.txt`, `host-load.log`, `chain-w5.log`,
`chain-w5.out`, `chain-wave5.sh`, `soak-json/`.
