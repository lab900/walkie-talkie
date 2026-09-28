# Wispr as engine: lab wave 2 (2026-09-28 evening, Tart guest `wt-lab`, real Wispr Flow)

**One driver, 18:27–20:31 EEST** (guest clock = UTC, phases 15:45–17:28). Raw files, per-phase
harness reports, soak JSON, a guest `relay.log` excerpt and the Wispr `History` rows are in
[`2026-09-28-wave2/`](2026-09-28-wave2/). This wave follows the interrupted morning run
(`report-lab-2026-09-28.md`).

## Setup

- **Boot**: `tools/vm-lab.sh up`, SSH answered after ~3 min. `tart exec` worked this boot, but
  everything except one probe went over SSH (`admin@192.168.64.4`).
- **App**: the host's installed build, tar over SSH, deployed twice.
  - 18:32: the 11:54 build.
  - 18:44: redeployed after the host rebuilt at 18:39. That build has `a5bf36b` (the Wispr
    Engine row behind `WT_WISPR_ENGINE`) and `b2d9bbd` (🔽 → = plain dictation, 🔽 = Return).
  - Grants held after both: `accessibility trusted=true eventTap=true`, canary alive in 67.9 ms.
  - **`POST /engine {"id":"wispr"}` is still taken without `WT_WISPR_ENGINE`** (`engine: wispr`,
    `source: Wispr Flow`). No env change was needed.
- **Files copied in**: `elevenlabs.env` (600, no URL lines; its stale `WT_WISPR_STANDALONE=1`
  line is now inert), the `~/wt-lab` mirror (refreshed 3 times, and after every case edit), and
  the RO clip `2026-09-11/17-08-41-98d90459.{wav,txt}` into the guest corpus.
- **Wispr** 1.6.957, quit + `open -b com.electron.wispr-flow` at 15:41 UTC.
  - **No ghost microphone after a bare relaunch**: 8 samples over 40 s, then 60 s more with no
    chord, all `micOpen false`, no capture.
  - The ghost appeared later, only after chords (finding E).
- **Load, the big caveat**:
  - The host went to **load 172** by 19:39 EEST (other sessions resumed host work at 19:30;
    `host-load.log`). The guest followed, up to 52.9 (`load-*.log`).
  - W2b and W3r1 ran clean (guest ≤ 7.8). W3r2's end, Ssmoke, S and the start of X ran heavily
    contaminated. X2 ran at guest ≤ 20.5 as the host calmed down (≤ 57 after 20:00).
  - Timings and several Wispr-side losses in S are load-shaped. The *path* verdicts stand.
- **pf**: after X2 the chaos anchor `com.apple/wt-chaos` was empty and the main ruleset was the
  stock two lines. Wispr was left running (state `S`, not stopped), relay idle, Engine = wispr.
- **Shutdown**: the guest was shut down cleanly at 20:30:41 (`guest has stopped the virtual
  machine`, 42 s). `vm-lab.sh down`'s SSH reported a failure only because the connection
  dropped mid-shutdown. No `tart stop`.

## Phases

| phase | ids | cap | ran | notes |
|---|---|---|---|---|
| W2b | TW12, TW13, TW14, TW19, TW22 | 30 min | 15:45–16:03 | |
| W3r1 | TW4, TW8a, TW15, TW20 (+ TW3, TW11 rewritten) | 20 min | 16:03–16:12 | |
| W3r2 | TW4, TW8a, TW15, TW20, TW11 | 20 min | 16:12–16:16 | TW4/TW20 with the new-pid wait |
| probe | BlackHole during a Wispr relaunch, 2 control + 2 relaunch | — | 16:16 (SSH), 17:27 (`tart exec`) | the SSH run is void (SSH processes record silence: no mic grant for `sshd-keygen-wrapper`) |
| X | `TX` | 75 min | 16:18, **0 cases** | `--only` is exact-or-glob, not a prefix: `TX` matched nothing. Kept as `*-X-empty.*` |
| Ssmoke | TS2, TS4, TS5 at `WT_SOAK_SCALE=0.2` | 20 min | 16:18–16:28 | |
| S | TS1, TS3, TS6 full | 50 min | 16:28–16:51 | |
| X2 | `TX*` (23 cases) | 75 min | 16:51–17:26 | |

The chaos suite (`3e4346c`) and the soak suite (`3d38351`) had both landed before the first
phase, so neither waited.

## Verdicts per case

\* = re-read against the evidence; the reason is in the *reading* column.

### W2b and W3: the TW cases

| case | W | verdict(s) | evidence | reading |
|---|---|---|---|---|
| TW3 | W15 | SKIP | retired | Q9 step 2 deleted the standalone-off world; TW1 covers the held pair (README §4.2) |
| TW4 | W11 | **BUG**, **BUG** | first-5-words 0/5 both runs; chip named the warming True; `no row and no microphone within 12 s` → `0.0 s voiced on the relay's own recording too: no speech` | **open, 4/4 over the day.** W3r1's chord went out 2 s *before* the relaunched Wispr existed (the case read the stale pid, fixed for W3r2). W3r2's went 4 s after the new pid: same result. Finding A |
| TW8a | W4 | **BUG**, **BUG** | outbox +1; no false rescue line (the case fix held); his paste passed False | run 1: Wispr **transcribed him** (row 26 `formatted`, 55 chars), and the relay's tap swallowed his ⌘V in its 10 s tail. **Relay-side**, finding B. Run 2: row 31 `raw_transcript`, 0 chars. **Wispr-side** |
| TW11 | W4 (rewritten) | **PASS**, **PASS** | A delivered with its shot (371 / 367 chars); B's 🔽 → `refused — words still in flight` on the chip | the refused start left the next 🔽 → as a *start*, so the case's "stop" opened a stray sentence (rows 28, 33). Finding C |
| TW12 | W4 / W-D7 | **BUG** | A at 10, B at −1 | expected (plan step 3). The ungated path can now only be a microphone edge, not his chord |
| TW13 | W-D8 | **ERROR** | `fake row 1 was not adopted (captureRow 1)` | rig: the cold local-model load at harness start stalled the main thread 3.0–7.3 s six times; adoption missed the 3 s window. Not re-run |
| TW14 | W-D9 | **PASS** | no second sentence; chip named the wait; refusal logged | fixed |
| TW15 | W19 | **BUG**, **BUG** | `spawnPending True`, `not running` | **open, 4/4**: plan step 14 not done |
| TW19 | D §1 | **PASS** | L/S refused; X switched with the swallow standing; late row not delivered | fixed |
| TW20 | W3 | **BUG**, **PASS** | down in 1.08 s / 0.34 s; next sentence delivered True both runs | the delivery half is fixed (it was case timing). The 0.6 s bar holds 2 of 4 over the day (0.66, 0.34, 1.08 at guest load 7.8, 0.34). The killed sentence itself ended `0.0` / `0.1 s voiced … no speech` (finding A) |
| TW22 | W2 / Q14 | **BUG\*** | the NULL-no-mic ceiling not taken; the 30 s cap, then `local-fallback`, 223 chars | **contaminated**: the real Wispr opened its microphone by itself at 16:02:30, 6 s into this fake sentence with every chord muted, and held it 84 s. The ceiling rightly did not apply; nothing was lost (finding E) |

### S and Ssmoke: the soak

| case | verdict | evidence (the soak's own numbers) | reading |
|---|---|---|---|
| TS1 | **FAIL** | 30/30 run, **delivered 24 (80 %)**, lost 6 (*silent* 3), rows 27/30, recall mean 0.56, close→landed p50 7.2 s / p90 14.0 s, stuck 1 | ran at host load 100–172, guest 20–53. The 6 losses: <ul><li>#11, #12, #20: Wispr rows `raw_transcript`, 0 chars, 19–25 s after the gesture (Wispr-side). The relay's Q14 stood in each time. **#11's and #20's local answers were then dropped** because the next sentence had opened (finding D, relay-side). #12's landed 285 s late, during #15.</li><li>#13, #14: the soak counted them *silent*, but they were refusals on the chip (`🚫 start refused — settling`, flashed `⏳ Wispr Flow takes one sentence at a time`). Its refusal regex misses the wording.</li><li>#24: **macOS disabled the event tap** (`the tap was disabled by the system (timeout) — re-enabled`) and the gesture never arrived. Truly silent; environment (host starvation).</li></ul>Low recall is Wispr under load: e.g. `Please take the node application.` for the EN clip, row 45 |
| TS2 | **ERROR** ×1 | `TextEdit would not open a document (osascript)` | rig: `make new document` overran the 8 s `_osa_out` timeout at guest load 7–11 (0.5 s when idle). Timeout raised to 25 s (case changes). Not re-run |
| TS3 | **ERROR** | same | same; not re-run |
| TS4 (0.2) | **PASS** | idle 120 s, 4 samples, Wispr mic never open; then a row at 11.7 s, delivered via `wispr-history`, recall 0.82 | no ghost while idle |
| TS5 (0.2) | **PASS** | 2/2 delivered (both `local-fallback`), rows 1/2, stuck 1, **ghost mic after sentence 2** | cold Wispr: Q14 carries both |
| TS6 | **FAIL\*** | 10/10 delivered, 0 lost; *preset back mid-sentence* 9 | **Q17's end state holds 10/10** (clipboard = the sentence after, 0 violations of that kind). The 9 are Wispr's own write + restore of the pre-sentence clipboard during the settle, before the relay writes the sentence: a transient window of 5–10 s |

### X2: the chaos

| case | verdict | evidence | reading |
|---|---|---|---|
| TX1 | FAIL → **PASS\*** | 📦×1, one copy, late row waited for | the only STILL UP was `sentences`, which is a case bug (below). Recall 0.33 is Wispr's |
| TX2 | **ERROR** | `KeyError: 'wisprLive'` | `/test/state` answered without `wisprLive` once, mid-relaunch (also seen at 15:43:05) |
| TX3 | **PASS** | relaunch, 🔼→ at once: no row → Q14 + Recover staged; mic closed at +30 s; no slow state answer | no ghost this time |
| TX4 | FAIL → **PASS\*** | 443 cut 45 s: row `error`, Q14 + Recover staged, longest Listening 15.8 s | `sentences` only |
| TX5 | FAIL → **PASS\*** | cut at the stop for 25 s: 📦×1 once | `sentences` only |
| TX6a | FAIL → **PASS\*** | triple 🔼→: delivered once, recall 0.91, mic closed 10 s later | `sentences` only |
| TX6b | FAIL → **PASS\*** | raw chords: row 79 empty → Q14 + Recover staged, loud | `sentences` only; a Wispr-side loss covered by Recover |
| TX7 | FAIL → **PASS\*** | 60 s sentence: 📦×1 in 2.3 s after the stop, 4.0/6 repetitions, row `raw_transcript` | `cap line True` is a false match on the decode-rate line's `ceiling × 1.19`; `stop→end 120 s` is the `sentences` artefact. 4/6 repetitions is Wispr's own text |
| TX8a | **FAIL** | relay refused (loud); his row `formatted`; his words in TextEdit 0 | **finding B**: his ⌘V at 17:07:12 was swallowed in the tail of the previous relay sentence (idle 17:07:06) |
| TX8b | **FAIL** | relay's in the witness once; his in TextEdit 0; drop line True | **finding B** |
| TX9 | **FAIL** | 3/3 sentences 1 s after a relaunch lost their head; every one ended Q14 → `dictation abandoned (the recogniser could not be reached)` → Recover staged (2.6–2.7 s voiced), 0 silent | W11 / finding A's cousin. The relay recorder *did* hear these. Q14 fell to Recover, not to the local model: the run's `WT_COLD_WHISPER=kill` leaves no warm helper. Recover gave the 62 chars back |
| TX10 | **FAIL** | relay 5/5 in the witness, 0 in TextEdit; **his 5/5 lost**; rows +10, all `formatted` | **finding B** at scale: each of his ⌘Vs logged `with no capture open — not the relay's; nothing delivered` |
| TX11a–h | FAIL ×8 → **PASS\* ×8** | cancel at +0.5 … +4.0 s: 📦×0, Recover staged, rows `()` / `dismissed` / `processing` | `sentences` only |
| TX12 | FAIL → **PASS\*** | WAL lock 8 s: 📦×1 once | `sentences` only |
| TX12d | FAIL → **PASS\*** | fake DB locked 8.1 s: capture held, no give-up, delivered 4.4 s after the release | `sentences` only |
| TX13 | **ERROR** | `relay-restart.sh`'s gate held (`audio staged for Recover (158 s left)`) and gave up after 122 s | the gate held, as asked; the case never drained Recover before its restart step |

**The `sentences` artefact.** Chaos `_still_up()` counted any entry in `state.sentences` as
stuck. `describeSentences()` returns parked + live, and the live one stays as `done` until the
next sentence opens. Sampled at 17:02: `busy false` with `[(67,'done')]`. That is why 16 chaos
FAILs are re-read as PASS: `sentences` was the only thing left up in each (TX7 also had the false
cap-line match). Fixed in
`cases_wispr_chaos.py`.

**Counts**:

- TW: 16 runs — PASS 5, BUG 9 (TW22 re-read as contaminated), ERROR 1, SKIP 1.
- TS: 6 — PASS 2, FAIL 2 (TS6 re-read: the end state holds), ERROR 2.
- TX: 23 as reported — PASS 1, FAIL 20, ERROR 2. **Re-read: PASS 17, FAIL 4 (TX8a, TX8b, TX9,
  TX10), ERROR 2 (TX2, TX13).**

## Findings

### A. The relay's own recording is empty for a sentence started just after a Wispr launch

This is what keeps TW4 open, and it hits TW20's killed sentence too.

Four relay sentences measured `0.0`/`0.1 s voiced` while CLIP_SPEECH was playing into BlackHole:
16:03:58, 16:11:35, 16:12:32 and 16:15:11. All four were within ~5 s of a Wispr (re)launch. So
Q14 could not stand in, and each ended *No speech was heard*, with the WAV deleted.

**The device is not what goes silent.** The `tart exec` probe (`probe-relaunch-tartexec.log`)
recorded BlackHole from a stream opened *before* the relaunch and heard the clip: 2.2 s voiced,
the same as the control. That points at the relay's recorder opened *just after* Wispr starts:
Wispr's CoreAudio set-up is the suspect.

Not always, though. TX9's three sentences 1 s after a relaunch measured 2.6–2.7 s voiced.

These are **4 relay-side losses** with a wrong message. The next probe: record the relay's own
WAV (disable the < 0.3 s delete under a test flag) at +0/+2/+5 s after a relaunch.

### B. The firewall's 10 s relay-owned tail swallows *his own* Wispr sentence

Q9 says his `61+60` sentence is Wispr's alone and pastes where the caret is. In this wave
**`⌘V from Wispr Flow passed` appeared 0 times**. Every one of his sentences whose ⌘V landed
within 10 s of a relay sentence going idle was eaten with `🛡️ ⌘V from Wispr Flow with no capture
open — not the relay's; nothing delivered`:

| case | his sentences eaten |
|---|---|
| TW8a run 1 | 1 |
| TX8a | 1 |
| TX8b | 1 |
| TX10 | 5 |
| **total** | **8** |

His 9th sentence (TW8a run 2) was lost on Wispr's side. **Wispr transcribed all 8 correctly**
(rows `formatted`). The relay dropped them silently.

The fix is W4's: in the tail, let a ⌘V through (or deliver it at the caret) when the newest
`History` row is *not* the relay's capture row. The row's rowid/timestamp is newer than the one
the relay adopted.

### C. A refused 🔽 → leaves the next 🔽 → as a start

TW11, both runs. 🔽 → during A's settle is refused out loud. Victor's natural "stop" press then
**opens** a new plain Wispr sentence (rows 28 and 33): one ran 48 s until cancelled, one was
abandoned with no row answer.

Not a loss, but a trap. Either keep refusing for ~2 s after a refusal, or say *nothing is
recording* on the chip.

### D. A Q14 fallback in flight is dropped when the next sentence opens

`dictationBegan()` closes a live sentence that was not parked
(`🧾 sentence #N had no answer left to wait for — closed`). The Q14 local decode still running
for it then answers into a finished sentence (`🗑️ the local model answered for sentence #N,
which is over — dropped`):

| sentence | closed | answer dropped | words lost |
|---|---|---|---|
| #33 (TS1 #11) | 16:34:29 | 16:35:53 | its answer, dropped |
| #40 (TS1 #20) | 16:42:39 | 16:44:14 | 948 chars |

That is **2 relay-side losses**. Nothing was said on the chip after the fallback's
*transcribing*. At normal speed the window is the ~3–4 s of a local decode, so a quick next 🔼→
after a Wispr failure loses the previous sentence.

Fix: park the fallback sentence (Q12's queue) or count it in `startBlocker()`. The refusal at
16:36/16:37 (`settling`) shows the blocker *does* see some fallbacks, so this is a gap, not a
design.

### E. The ghost microphone: seen 3×, every time after chords, every time cleared by a relaunch

1. 16:02:30: the real Wispr opened its microphone with all chords muted (desk TW22), 84 s.
2. 16:12:12: 25 s after TW20's second sentence.
3. TS5: after sentence 2 (`GHOST@0.1s`).

It was never seen on a bare relaunch (15:41), in 2 min idle (TS4), or 30 s after TX3's cold
sentence. Each was cleared by the next Wispr relaunch; none needed an app restart.

### F. Environment effects (not the app)

- **The event tap disabled by macOS under starvation**: 1 gesture lost (TS1 #24).
- **Main-thread stalls**:
  - 3–18 s with the local model loading cold at harness start (TW13's ERROR);
  - 11.9–18.5 s at guest load 20–40.
- **Local decodes**: 19.8 s of audio took 143 s and 19.2 s took 275 s (load 24–31), against 4.4 s
  typical.
- **Rig**: `/test/state` without `wisprLive` once, mid-relaunch (TX2).
- **Rig**: SSH-launched processes record silence (probe, first run).

## Is Wispr as an engine robust enough to restore?

**Criteria and numbers, whole wave** (79 relay-opened sentences on the real Wispr: 77 🔼→ and 2
🔽 →; the 10 desk sentences on the fake `History` are excluded). Counted from
`relay-guest-wave2.log` with `sentences.py` (`sentences-out.txt`) and the soak/chaos JSON.

- **(a) No relay-side word loss in ≥ 95 % of sentences: NOT MET.**
  - The denominator is 65: 79 minus 13 deliberate cancels (TX11a–h, cleanups) minus TW11's 1
    stray start.
  - **Relay-side losses: 6.** Finding A: 4 (`0.0 s voiced` after a launch). Finding D: 2 (Q14
    answer dropped).
  - **59/65 = 90.8 %.**
  - Leaving out the host-starved S phase (D's 2) gives 4/47 = 91.5 %. That is still under 95 %.
  - Not in the 65: **8 of his 9 standalone sentences were lost to the relay's firewall**
    (finding B). Counted against his sentences, that is 0/9 delivered.
- **(b) No stuck state that a Wispr relaunch does not clear: MET.**
  - Ghost mic 3×, each cleared by the next relaunch.
  - The chaos `sentences` "stuck" is a case artefact (a `done` ledger entry).
  - TS1's one *stuck* was busy 60 s during a 143 s fallback decode at load 24, which ended by
    itself.
  - TX13 (gate + freeze) did not reach its restart step, so relaunch-under-restart is untested.
- **(c) The firewall caught 100 % of Wispr's ⌘V during relay sentences: MET.**
  - 27 drops inside a capture, plus the relay's own late ⌘Vs swallowed in the tail.
  - 0 Wispr ⌘V passed anywhere.
  - No relay words in TextEdit (TX10: 0/5), each relay sentence in the witness once (TX10
    `copies 5.0`; its `doubled text` flag is the same clip five times).
  - Soak `doubled` 0 in TS1/TS5/TS6.
  - **But it over-catches**: finding B.
- **(d) Failures always end in local fallback or Recover, never silent: NOT MET.** The loud ones:

  | how it ended | count |
  |---|---|
  | Q14 + Recover staged: TX2, TX3, TX4, TX6b, TX9 ×3, TX13 (16 `recovered N chars` drains over the wave) | 8 |
  | `local-fallback` delivered | 5 |
  | refusals on the chip | several |

  The exceptions:
  - Finding D: 2 fallback answers dropped with no word on the chip. **Silent.**
  - Finding A: 4 ended *No speech was heard* with speech played and the WAV deleted. Loud, but
    wrong, and nothing to Recover.
  - Finding B: 8 of his sentences dropped with a log line only. **Silent.**
  - TS1 #24: the tap disabled by macOS. Silent; environment.
- **(e) The Wispr-side losses, counted and attributed.** 86 `History` rows since 15:40 UTC
  (`wispr-history-rows.txt`):

  | status | rows |
  |---|---|
  | `formatted` | 53 |
  | NULL | 11 |
  | `raw_transcript` | 5 (4 empty) |
  | `dismissed` / `processing` | 5 / 1 (the TX11 cancels, by design) |
  | `error` | 1 (TX4's 443 cut, by design) |

  - **NULL (11)**:
    - 5 were chords to a Wispr under ~5 s old (rows 29, 34, 36, 85, 86; TW4/TX9's other cold
      chords made **no row at all**);
    - 3 were case-made (TW19's real gesture under the desk rig, TW11's two stray starts);
    - 1 killed (TX2), 1 in TX6b's chord storm, 2 cancels (TX11a/b).
  - **Empty `raw_transcript` (4)**:
    - 3 in TS1 under host load 100–172 (rows 47, 48, 54, 19–25 s after the gesture);
    - 1 his TW8a run 2 (row 31).
  - **Truncated** (the morning's `How` kind): 2 formatted rows ≤ 12 chars, both from the RO clip
    (`Poți să?`, `lăzeșe`). Plus low-recall mis-recognitions under load in TS1: mean recall 0.56
    against 0.79 in TS6, e.g. `Please take the node application.`.
  - **The morning's `How` (row 15) did not recur.**
  - **Every Wispr-side loss on a *relay* sentence was covered**: by Q14/Recover, or loud. Except
    where finding A or D made the cover itself fail.

### Verdict: **NOT YET.**

The firewall is sound: (c) holds, nothing crossed destinations, nothing doubled, and nothing
stays stuck past a Wispr relaunch (b). But three relay-side defects lose words: two silently, one
with a false message. The relay-side loss rate is 90.8 %, below the 95 % bar.

Still to fix before Wispr is restored as an engine:

1. **B, the firewall tail eats his own Wispr sentences**: 8/8, silent. Let a ⌘V through in the
   tail when Wispr's newest row is not the relay's capture row (W4). This alone makes Wispr's
   standalone mode unusable next to the relay today.
2. **D, the Q14 answer dropped when the next sentence opens**: park the fallback sentence or
   make it a start blocker, and never finish a sentence whose local decode is still out.
3. **A, 0.0 s voiced on the relay's recording right after a Wispr launch**: find out why (keep
   the WAV under a test flag, probe at +0/+2/+5 s). Until then, refuse or delay a relay start
   for ~5 s after a Wispr launch, and never say *No speech* while a clip is known to be playing.
   Keep the WAV for Recover whenever Wispr also failed.
4. Smaller:
   - C, the refused 🔽 → toggle trap;
   - TW15 / W19 (`spawnPending` with Wispr quit, 4/4);
   - TW12 (plan step 3, now only reachable via a mic edge).

Then re-run on a quiet host:

- TW4, TW8a, TX8a/b, TX9, TX10;
- TS1 (it ran starved);
- TS2 and TS3, which never got past their first TextEdit call here;
- TX13, with a Recover drain before its restart step.

## Case changes in this commit

- `cases_wispr.py`:
  - **TW20** waits for witness text (40 s), not `wait_delivered`.
  - **TW8a** takes its mark after the relay's own ⌘V drop (≤ 3 s), keeping ≥ 1 s from the close.
  - **TW4/TW20** wait for a **new** Wispr pid after `/test/wispr-proc relaunch`: the state answered
    the old pid for ~2 s.
  - **TW3** retired (a `pre` that SKIPs with the reason).
  - **TW11** rewritten as a relay-only overlap: 🔼→ A with a shot, then 🔽 → (`back-right`
    since `b2d9bbd`) B during A's settle. It PASSes on a loud refusal.
- `cases_wispr_chaos.py`: `_still_up()` ignores `done` sentences.
- `cases_wispr_soak.py`: `_osa_out` timeout 8 → 25 s.
- Still to change:
  - the soak's `silent` should count `🚫 start refused` as loud;
  - chaos TX7's cap regex matches the decode-rate line;
  - TX13 must drain Recover before `relay-restart.sh`;
  - TX2 should tolerate a state without `wisprLive`.
