# Wispr as engine: lab wave 3 (2026-09-28 night, Tart guest `wt-lab`, real Wispr Flow)

**Verdict: NOT YET — close.** Steady state is clean (soak 42/42 relay, 20/20 of Victor's own
sentences; 0 misroutes, 0 doubled pastes, 0 stuck on a quiet host). Four relay-side defects
remain: **B2, D2, A (DEAF takes), E (ghost mic)**, below. Written by the session from the VM
driver's hand-back (the driver could not write files); raw data in `2026-09-28-wave3/` (commit 9506910).

**One driver, 21:05–23:50 EEST** (guest clock is UTC; the phases ran 18:21–20:34 UTC).

## Setup

**Builds.** Each built on the host from `git archive <sha>` with
`WALKIE_STAGING=<scratch> ./build-app.sh --stage-only`, copied into the guest with tar; all signed
with Victor Addons Local Code Signing, grants held (`accessibility trusted=true eventTap=true`).

| phase | build | what it holds |
|---|---|---|
| 1 | **1dbf9a2** | committed HEAD before fix batch 2 |
| 2, from P2a | **575bbb2** | fix batch 2 |
| 2, from P2a2 | **e6cfca7** | adds per-take `WT_KEEP_TAKES` and the TW1 2.2 s bar |

**Mirror.** `~/wt-lab` synced from the same `git archive` each time, never from the dirty tree; old
copies stay in the guest as `evals.<sha>`.

**Runner.** `run-w3phase.sh` with `WT_LAB=1 HANDS_OFF=1 WT_ALLOW_WISPR_KILL=1 WT_LOOPBACK="BlackHole 2ch"`,
Engine = wispr. The local model was warmed before every phase.

**Wispr.** Version 1.6.957. Guest config: `61+60 = ptt`, `shouldMuteAudio: false`, `shouldPauseAudio: false`.

**Host load** (1-min average, sampled every 30 s):

| phase | host mean | host max | guest max | note |
|---|---|---|---|---|
| P1a | 15.5 | 46.7 | 5.2 | TW1 ran inside the 46.7 spike |
| P2a | 20.1 | 90 | 5.0 | the spike (22:14–22:18) only hit TW32's idle 600 s wait |
| P2a2 | 11.4 | 23.9 | 5.5 | |
| P2b | 10.3 | 14.3 | 11.0 | |
| P2c (soak) | 11.6 | 18.4 | 2.4 | quiet; wave 2's soak ran at load 100–172 |
| P2d | 12.8 | 19.5 | — | |

## Phases

| phase | build | ids | ran (UTC) |
|---|---|---|---|
| P1a | 1dbf9a2 | TW1, TW2, TW5, TW6a–d, TW7, TW9, TW10. Stopped at TW11 when batch 2 landed | 18:21–18:57 |
| P2a | 575bbb2 | TW4, TW8a, TW8b, TW11, TW15, TW20, TW32. Stopped on TW32: relay busy 600 s on the ghost mic | 19:01–19:24 |
| P2a2 | e6cfca7 | TW32, TW33, TW34, TN4, TW1 | 19:26–19:43 |
| P2b | e6cfca7 | TX2, TX7, TX8a, TX8b, TX9, TX10, TX13 | 19:43–19:56 |
| P2c | e6cfca7 | TS1, TS2, TS3 at full scale | 19:56–20:16 |
| P2d | e6cfca7 | TW14, TW17, TW19, TX1, TX3, TX4, TX5, TX6a, TX6b, TX11a–h, TX12, TX12d | 20:16–20:34 |

## Verdicts per case

\* = re-read against the log.

### Phase 1 (1dbf9a2)

| case | verdict | evidence |
|---|---|---|
| TW1 | BUG | listening from 1.78 s for 0.9 s; ran at host load 46.7 |
| TW2 | PASS | stamped tail ignored |
| TW5 | PASS | 43/43 samples warming with no row; chip says `Opening Wispr Flow...` |
| TW6a, TW6b | PASS | Recover staged, no orphan WAV |
| TW6c, TW6d | PASS | `local-fallback` delivered |
| TW7 | PASS | (a), (b) and (c) all recoverable |
| TW9 | PASS | refused |
| TW10 | PASS | no ghost row with words |

### Phase 2 (fix batch 2)

| case | verdict | evidence |
|---|---|---|
| TW4 (575bbb2) | **BUG** | First chord 9 s after a relaunch; first 5 words 0/5. Meter: `0.0 s voiced — BlackHole 2ch: 105 buffers, peak 0, 0 tap restart(s) — DEAF`, no 🔁 line. Ends `NO AUDIO … not 'no speech'; kept for Recover`. Finding A |
| TW8a | BUG → **PASS\*** | `passed — row 116 is newer than the relay's — his own sentence, inside the relay's tail (B, Q19)`. The case regex still wants `its own sentence (standalone, Q9)` |
| TW8b | PASS | his paste passed |
| TW11 | PASS | B refused out loud; no stray sentence (**C fixed**) |
| TW15 | PASS | `spawnPending False`, `not running` flashed (**W19 fixed**) |
| TW20 | PASS | down in 0.34 s; the next sentence delivered |
| TW32 (e6cfca7) | PASS | the relay's tail ⌘V dropped and said to be the relay's; his newer row passed |
| TW33 | **BUG** | A parked and delivered by `local-fallback`. **B never delivered**: `sentence #4's words wait for the one before` for 151 s after #3 was done, then cancelled and dropped. Finding D2 |
| TW34 | PASS | +1 / +3 / +5 s after a relaunch: 2.2 / 2.2 / 2.1 s voiced, peak 16366, 0 restarts. The desk rig mutes the chords, so Wispr never opened its mic |
| TN4 | SKIP | `BlackHole 2ch pass-thru is dead (440 Hz check)` right after TW34's relaunches; later phases heard audio |
| TW1 | BUG | listening from 0.76 s for 2.0 s against the 2.2 s bar; no early release. Borderline: the onset is Wispr's row lag |
| TX2 | PASS, loud loss | Wispr killed 5 s in; down in 0.17 s. **The relay's take was DEAF for all 5.2 s** (51 buffers, peak 0), ended `NO AUDIO`, kept for Recover. Finding A |
| TX7 | FAIL → **PASS\*** | 62.9 s take, 10.9 s voiced (= 6 × CLIP_EN), one `raw_transcript` row, delivered once. Wispr returned 4 of 6 repetitions, as in wave 2. Cap line False: the TX7 fix held |
| TX8a | PASS | relay refused; his words in TextEdit only |
| TX8b | **BUG (unverified)** | The relay passed his ⌘V at 19:47:20, but nothing reached TextEdit within 30 s, nor the witness. Where Wispr's paste went is unknown. The case's `(Q19)` regex misses `(B, Q19)` |
| TX9 | PASS | 3/3 sentences 1 s after a relaunch delivered by Q14 `local-fallback`, 2.6–2.8 s voiced (wave 2 ended these in Recover only) |
| TX10 | **BUG** | relay 5/5 in the witness; **his 5/5 lost**. Each logs `with no capture open — asking the rows` → `the dropped ⌘V is row N (formatted), newer than the relay's — his own Wispr sentence (Q19)`, and is dropped anyway. Finding B2 |
| TX13 | ERROR (rig) | the `ba2f29a` runner-lock gate waits on the harness's own lock |
| TS1 | **PASS** | 30/30 delivered (100 %), all via `wispr-history`; recall 1.00; mic close → witness p50 5.6 s, p90 6.4 s; 0 doubled, 0 stuck |
| TS2 | **PASS** | 20/20 of his sentences at the caret, 0 into the terminal or outbox; close → caret p50 0.8 s, p90 2.1 s |
| TS3 | **PASS** | 20/20 mixed (12 relay, 8 his), routed right 100 %, 0 misroutes, 0 silent, 0 stuck |
| TW14, TW17, TW19 | PASS | |
| TX1 | PASS | SIGSTOP 8 s: delivered once |
| TX3 | **BUG** | Delivered by Q14. Then Wispr opened its own mic at +11 s and still held it at +30 s, so the next 🔼→ was refused. Finding E |
| TX4, TX5 | PASS | 443 cut → row `error` → Q14, delivered once |
| TX6a | PASS | |
| TX6b | **FAIL** | Chord storm: see findings A, E and the B-risk |
| TX11a–h | PASS ×8 | cancels leave audio in Recover |
| TX12, TX12d | PASS | |

**TX6b in detail.** Wispr's own mic-close ended the relay's second take after 0.75 s. The recorder
then logged `🔁 mic: no audio buffer for 1.0 s — tap restarted` and got 0 buffers after the
restart. The 4 s of speech went into Wispr row 217, which the relay armed as *his* (`a Wispr ⌘V
passes now (B)`). The row stayed NULL, so nothing was pasted. The sentence ended `NO AUDIO`, and
Recover gave no transcript.

**Phase 2 counts, fixed builds:** 37 case runs — PASS 28 (2 re-reads), BUG 6 (TW4, TW33, TW1,
TX8b, TX10, TX3), FAIL 1 (TX6b), ERROR 1 (TX13, rig), SKIP 1 (TN4).

## The criteria

| # | criterion | result | numbers |
|---|---|---|---|
| (a) | relay-side delivery ≥ 95 % on real Wispr | **MET in steady state; marginal overall** | soak 42/42 = 100 %; all phase-2 relay sentences (chaos in, deliberate cancels out): 64 delivered, 3 lost to finding A → **64/67 = 95.5 %**; with TW33 B (D2) **64/68 = 94.1 %**. Wave 2: 90.8 % |
| (b) | zero cross-destination paste | **MET (0 seen)** | TX8a, TX10, TS3: 0 misroutes. Near miss: TX6b (B-risk) |
| (c) | zero doubled paste | **MET** | soak 0; TX1, TX6a, TX12, TX4, TX5 each once |
| (d) | his own `61+60` sentences in the firewall tail delivered | **NOT MET** | Passed: TW8a\*, TW8b, TW32, TX8a, TS2 20/20, TS3 8/8. **Lost: TX10 5/5**, silent. TX8b passed at the relay but never landed |
| (e) | no fallback answer dropped | **MET for the fallback** | 0 `which is over — dropped`; TW33's A parked and delivered. **The sentence after it is lost (D2)** |
| (f) | voiced audio within 5 s of a Wispr launch | **MET as worded; A is not gone** | TW34 3/3; TX9 3/3 at +1 s; TX3 at +0.8 s. DEAF takes follow Wispr's *first mic open*, not the clock |
| (g) | a refused 🔽→ does not flip the toggle | **MET** | TW11 |

## Latency: time to text

From the app's own `the words landed … N ms after the microphone closed`, quiet guest.

| path | n | p50 | p90 | range |
|---|---|---|---|---|
| **Wispr row, relay sentences** (TW + TX + soak, no chaos stalls) | 52 | **0.98 s** | **2.2 s** | 0.48–2.45 s |
| Wispr row, soak only | 42 | 1.6 s | 2.2 s | |
| **Local fallback (Q14)**, Wispr gave nothing (TW6c/d, TW20, TW33, TX9) | 7 | **4.6 s** | 11.1 s | 2.6–11.1 s |
| Local fallback when Wispr fails late (TX4/TX5: row `error` after ~30 s) | 2 | ≈ 30 s | | 27–35 s |
| Local decode alone, warm (guest, Metal) | 23 | 1.45 s | | max 8.0 s for 59.9 s of audio |
| **Into the terminal**, relay (TS1 / TS3); includes settle and typing | 30 / 12 | 5.6 s / 4.9 s | 6.4 s | |
| **His standalone Wispr, at the caret** (TS2) | 20 | **0.8 s** | 2.1 s | |

When Wispr answers, its row is the fastest path (~1 s), against ~1.5 s for a warm local decode. The
Q14 fallback costs 2.6–11 s because it adds the wait for Wispr's row (3 s NULL check, 12 s no-mic
ceiling) — the auto-fallback budget (p98, 2026-09-28 22:25) is meant to replace that wait. In the
terminal, the 4–5 s after "words landed" is the relay's settle and typing, paid by every engine.

## Findings for fix batch 3

### B2 — his ⌘V is dropped in the "no capture open" path even after his row is identified

TX10, 5/5, silent. Each time: `row 130 (open) is his … a Wispr ⌘V passes now (B)` → the relay's
own `📦 delivery` in the same second → his ⌘V ~6 s later: `⌘V from Wispr Flow with no capture open —
asking the rows (floor 129)` → `the dropped ⌘V is row 130 (formatted), newer than the relay's — his
own Wispr sentence (Q19)` → dropped anyway. In TW8a, TW32 and TX8b the ⌘V arrived before the relay's
delivery and took the `passed — … inside the relay's tail (B, Q19)` path.
**Fix:** honour the armed pass in the no-capture path, or paste the row's text at the caret once the
post-hoc lookup says the row is his. **Also TX8b:** the relay passed his ⌘V but nothing landed in
TextEdit — look at the frontmost app and the pasteboard at the pass (the Q17 clipboard write is 1.6 s later).

### D2 — the sentence after a parked fallback waits forever

TW33: A had a NULL row; Q14 decoded 59.9 s and A was parked. B's row was `formatted` at 19:33:24
(`sentence #4 landed before #3 — it waits its turn`). #3 done 19:33:28, delivered 19:33:37. #4 kept
logging `the settle waits: sentence #4's words wait for the one before` every ~8 s for 151 s, then
was cancelled and dropped. A silent loss introduced by D's parking.
**Fix:** when a parked sentence finishes, re-check the sentences waiting behind it; test B's words
arriving before A's decode ends.

### A — DEAF takes follow Wispr's first mic open after a launch, not the time since the launch

| case | when | the relay's take | what Wispr did |
|---|---|---|---|
| TW4 | first chord 9 s after a relaunch | 105 buffers, peak 0, no 🔁 | did not answer |
| TX2 | first chord to a Wispr launched 63 s earlier (every earlier chord muted by TW34) | 51 buffers, peak 0, no 🔁 | made a row |
| TX6b | chord storm | 0 buffers after a stall-triggered tap restart | |

Healthy: TW34 at +1/+3/+5 s (Wispr never opened its mic), TX9 3/3 at +1 s, TX3 at +0.8 s, every warm
sentence. **A1: zero instances** — not one `AVAudioEngineConfigurationChange` 🔁 line all night.
**A2-shaped:** every DEAF take — buffers flowing, peak 0, no 🔁. **Not `shouldMuteAudio`** (false in
the guest, `shouldPauseAudio` false). So a "refuse starts for 5 s after a Wispr launch" fallback would
not cover TX2 (63 s after launch).
**Proposal:** treat "buffers flowing, peak == 0 for ≥ 1 s while Wispr's mic is open" like a stall:
restart the tap and log whether audio comes back (today the watchdog fires only on missing buffers);
or arm a check on the first Wispr mic open after each launch. **Open question — BlackHole only?** A
host probe with a real microphone would say whether this affects Victor.

**Answer (2026-09-28, 23:55, host, read-only): as far as can be checked without the VM, yes: BlackHole
only.** It cannot reach his DJI, Elgato or MacBook microphone.
- **The mechanism is BlackHole's own read path.** BlackHole 0.7.1's `DoIOOperation(ReadInput)` (the
  version in the guest; identical on `master` 62953f5) fills the reader's buffer with **zeros** when
  `lastOutputSampleTime - inIOBufferFrameSize < mInputTime.mSampleTime`. Put simply, this reader is
  ahead of the last write. When that happens it also **clears the whole ring buffer**
  (`vDSP_vclr(gRingBuffer…)`). `lastOutputSampleTime` and `isBufferClear` are function-`static`: one
  value shared by every client and both BlackHole devices. The timeline resets in `StartIO` when the
  client count goes 0→1, but `lastOutputSampleTime` does not
  ([BlackHole.c @ v0.7.1](https://github.com/ExistentialAudio/BlackHole/blob/v0.7.1/BlackHole/BlackHole.c)).
- The HAL calls `DoIOOperation` per client. Apple's `AudioServerPlugIn.h` says `inClientID` is *"the
  client doing the operation"*, *"a device is allowed to do different sets of operations for
  different clients"*, and `inIOBufferFrameSize` *"will be different than the nominal buffer frame
  size"* for some operations. A second reader, such as Wispr's Chromium `getUserMedia` with its own
  IO buffer and phase, is judged against the same global write time and can wipe the ring the relay
  reads from. The relay then gets flowing buffers of exact zeros, and no configuration change is
  posted, because nothing about the device changed. That is the VM's signature (A2-shaped, A1 = 0).
  Why only the *first* open after a launch is **not** established; only the VM can say.
- **A hardware input has no such branch.** Its driver hands every client the same ADC samples. There
  is no "has anyone written" test and no shared state that one reader can clear for another. The
  other generic ways to get zeros with buffers flowing do not come from Wispr:
  - a missing grant, which macOS answers with `noErr` and zero-filled buffers: the sandbox's Audio
    Input entitlement ([Apple forums 771048](https://developer.apple.com/forums/thread/771048)), or
    TCC's audio-capture consent ([*2,000 Buffers of Nothing*](https://dev.to/nickdelv/2000-buffers-of-nothing-3i8)).
    The guest's healthy takes (peak ~16 k) rule it out;
  - an input muted or set to volume 0. Wispr's helper only *listens* for that
    (`[AudioInterruptionMonitor] Input volume dropped to zero`, `Could not add mute listener`). Its
    `Set system mute state` belongs to the *output* Volume Manager, behind `shouldMuteAudio`, which
    is false on the host;
  - hog mode (not in Wispr's binary).
- **Probe, host, no Wispr driven:** `probe.swift` in the session's scratchpad. Reader A (AVAudioEngine,
  default IO buffer) ran for 7 s. Reader B was a fresh process with a **128-frame** IO buffer (the
  Chromium "interactive" shape), opened on the same device 2 s in, for 3 s:

  | device | A before B | A during B | A after B |
  |---|---|---|---|
  | MacBook Pro Microphone, 48 kHz | peak 41–106 | 45–59 | 43–63 |
  | Elgato Wave XLR, 96 kHz | 71–79 | 73–121 | 87–135 |

  A never dropped to 0, and buffers never stopped. The room tone floor on a silent desk is **≥ 41**,
  so the new peak-0 watch can never fire on these microphones. The DJI receiver was not plugged in
  (a USB class device, same argument). Victor's host Wispr reads `🎓 TO Wispr` (1476 rows / 7 days),
  the built-in (147) and `Wireless Mic Rx` (77), so it does share the built-in and the DJI with the
  relay. The probe covers that sharing.
- **Not probed:** a Loopback (Rogue Amoeba) device with two readers. The rig's `🧪 WT Inject` was in
  use by another session's harness, and Loopback is closed source. On the host the relay is the
  **writer** of `🎓 TO Wispr` and Wispr its reader, so a zero-on-read there would starve Wispr, not
  the relay.
- **What changes:** `MicRecorder`'s peak-0 watch restarts in steps: 1 = the tap, 2–3 = a new
  `AVAudioEngine` with the device re-resolved. Each `🔁` line carries a `[device readout]` (mute,
  input volume, nominal vs tap rate, running somewhere, IO buffer), and the next line says whether
  audio came back. The VM run (wave 4: TM1, TM2, TW4, TW34, TX2) says which step, if any, beats the
  BlackHole ring wipe.

### E — the ghost microphone, 3 times tonight, now blocking

1. After TW20: relaunch 19:09:54, a sentence where Wispr "never opened its microphone", then Wispr
   opened its mic on its own and held it **> 14 min**; `busy` stayed true, TW32 died after 600 s,
   only a relaunch cleared it. 2. TX3: mic opened at +11 s, still open at +30 s, next 🔼→ refused.
3. TX6b: still open 10 s after the storm. Each time after a relay chord a cold Wispr never answered.
**Proposal:** when Wispr opens its mic within ~20 s of a relay chord it did not answer, and no `61+60`
was seen, treat it as the relay's late start and dismiss it (⌃Esc), or at least say so on the chip.

### B-risk — TX6b: the relay armed its own intended speech as "his"

After the storm desynced the relay and Wispr, row 217 held the speech the relay meant to take, and
the relay armed it as his. Had it finished, Wispr would have pasted it at the caret with the relay's
approval. **Suggestion:** a row that opens < ~1 s after the relay's own chord is not his.

### Rig and case items

- TX13: the runner-lock gate (ba2f29a) waits on the harness's own lock — exempt the lock's own pid.
- TW8a regex: `its own sentence (standalone, Q9)` → `his own sentence, inside the relay's tail (B, Q19)`.
- TX8b: `"(Q19)" in txt` misses `(B, Q19)`.
- TN4: the 440 Hz self-test failed right after TW34's relaunches; re-run alone.
- TW1: 2.0 s against the 2.2 s bar with 0.76 s of Wispr row lag before listening; measure from the row.

## Confirmed fixed on real Wispr

| finding | evidence |
|---|---|
| B, main path | TW8a\*, TW32, TX8a, TS2 20/20, TS3 8/8 |
| C | TW11 |
| W19 | TW15 |
| D's drop | 0 `which is over — dropped` lines |
| A's message | now `NO AUDIO … not 'no speech'`, kept for Recover |
| TX9 cold relaunch | Q14 3/3 |

**Fix batch 3, in order:** B2, D2, A (first-mic-open DEAF), E, the TX6b "his" risk, rig items.
**Re-run after:** TW33, TX8b, TX10, TW4, TX2, TX3, TX6b, TX13, TN4, TW1, plus TS3 with 2 s gaps
(TX10's rhythm) or a relay + his pair soak.

**State left:** VM down cleanly; ElevenLabs credits 0 (guest key commented out for the run, restored);
night stamp not written (finished before 01:50); host app untouched; VM headless throughout.
