# A — Wispr Flow as the engine: lifecycle and timing (adversarial read, 2026-09-28)

Dimension: **Wispr runs its own state machine, and the relay only sees it through witnesses.**
Every timing assumption the relay makes about that machine is attacked here: late or missing
starts, lost stops, Wispr stopping on its own, overlapping sentences, quit, crash, update, sleep,
blind taps, and clocks.

Read-only on the source. Line refs: `WFS` = `WisprFlowSource.swift`, `WS` = `WisprState.swift`,
`WH` = `WisprHistory.swift`, `WN` = `WisprNotes.swift`. These were stable while I read them.
`AppDelegate.swift` (AD) and `HotkeyTap.swift` (HT) were being edited during the read, so they are
cited by **function name**.

**Configuration that matters, as installed on 2026-09-28** (read from disk, not from the docs):
- `WT_WISPR_STANDALONE=1` is set in `~/.walkie-talkie/elevenlabs.env`, so **Q9 is ON**. The
  standalone bullet in `dictation-source.md` still says "OFF".
- Wispr's `ptt` is `54+60` (right ⌘⇧).
- The Engine is `eleven-live`.
- The HT push-to-talk detector still watches `54+61` (right ⌘⌥). As a result, Wispr's own ptt is
  invisible to the tap.

Findings already written by the sibling reports are **referenced by ID and not repeated**:
- `B-errors.md`: W-B1…B10
- `C-firewall.md`: W-C1…C15
- `D-state.md`: W-D1…D13

This file adds four things:
- the lifecycle model (§1)
- the timing action×state table (§2)
- the findings those two did not cover (§3)
- the harness hooks that timing cases need (§4)

---

## 1 · Wispr's lifecycle, as the relay can observe it

### 1.1 What Wispr really does (inferred from its `History` table + measured numbers)

```
            ┌───────────── quit / crash / Squirrel update (new pid) ─────────────┐
            ▼                                                                    │
  [NOT RUNNING] ──launch──▶ [COLD] ──5–6 s (measured)──▶ [IDLE] ◀─────────────────┤
                         (shortcuts may be dropped    │  ▲                       │
                          or queued: unknown)         │  │ ⌘V posted ~57 ms after│
                                                      │  │ `formatted`, then the │
     chord (fn⌃Space toggle │ ptt 54+60 held │ its    │  │ clipboard is restored │
     own UI / pill)         ▼                         │  │                       │
                      [ARMED] row created, status NULL (357 ms)                  │
                         │  └── never records: 100 rows/30 d stay NULL for ever ─┘ (W-A1)
                         │ mic opens (warm 0.3–0.7 s, cold 1–6 s)
                         ▼
                      [RECORDING]  IsRunningInput = 1
                         │ toggle again │ ptt released │ ⌃Esc │ Wispr's own end
                         ▼
                      [FINALISING] mic closed; row NULL → raw_transcript → processing
                         │ e2e p50 2.2 s · p99 7.1 s · 18 > 8 s · 1 > 30 s (36.3 s) in 30 d
                         ▼
                      [TERMINAL]  formatted (5067) · dismissed (164) · raw_transcript (424:
                                  354 with no text) · no_audio (22) · processing-forever (17)
                                  · error (9) · empty (1)
                         │ formatted → [PASTING] ⌘V (firewall) ─▶ IDLE
                         └─ anything else ─▶ IDLE (no ⌘V)
```

(Counts are the `History` rows since 2026-08-28, from a read-only query of metadata columns only.)

### 1.2 The signals the relay reads, and what each one can actually prove

| signal | where | proves | blind when |
|---|---|---|---|
| the chord **we** post (`postWisprHandsFree`) | HT, `start()`/`stop()` WFS:734/1052 | that we *asked* | always true that we asked; says nothing about whether Wispr took it |
| a chord **he** presses, seen on the tap (`onWisprMaybeStarting`) | HT `handle`: fn⌃Space keyDown · the right ⌘⌥ flagsChanged | that he pressed *our idea* of Wispr's chord | Wispr's real ptt `54+60` is **not watched**. Secure Input hides the keys. Standalone returns early (WFS:1287/1299) |
| `History` newest row appears (150 ms poll, capture only) | WFS:2097–2114 | that Wispr *took* a chord | a newer row exists (poll reads `newest()` only, W-B1). A row is **not** a microphone (W-A1) |
| row status | WFS:2129–2239 | progress / end | NULL or `processing` forever. Textless `raw_transcript` (W-A2) |
| 100 ms `IsRunningInput` poll | WFS:1515 | a mic *is* open | runs only while `WS.wantsPoll` (warming/listening/transcribing). An open in `transcribing`/`done` is a no-op (WS:245–248). A close needs `pollMs` (WFS:1526) |
| `WisprWatch` notification | WFS:1595 | the same, pushed | 0–6 s late, often silent on Loopback. Standalone ignores it when nothing is open (WFS:1612). `lateOpenEdge` eats opens ≤ 12 s after our stop (WFS:1690) |
| Wispr's ⌘V on the tap | HT firewall branch → `injected` WFS:2548 | Wispr finished a sentence *somewhere* | Secure Input / dead tap (W-C8/C9). It carries no row id |
| Wispr's main pid (150 ms, capture only) | WFS:2070–2078 | the process that took the chord is gone | a hung (SIGSTOPped, beach-balled) Wispr looks alive |

### 1.3 The relay's model, and what it assumes about the transitions

`WisprState`: `idle → warming (our chord) → listening (poll | notify | row adopted) → transcribing
(our stop | poll close | notify close) → done(status) → idle (endCapture)`.
Beside it the source keeps its own flags: `speculative`, `isRecording`, `capturing`, `historyRow`,
`discardOnArrival`, `retiredDiscardRow`, and in HT `relayOwned`.

Assumptions baked in. Each is broken somewhere below.

| # | assumption | broken by |
|---|---|---|
| A1 | every chord toggles Wispr **exactly once**, and Wispr's state = the parity of our posts | lost / queued / late chords, Wispr's own stop, a stop before start → §2 rows 1–3 and 6–8, W-A4, W-B9, W-D6 |
| A2 | a row appearing means Wispr is recording | 100 NULL rows that never record → **W-A1** |
| A3 | the capture's row stays the newest row until it is terminal | any second Wispr sentence → W-B1, W-D7 |
| A4 | a mic that closes means the row will be terminal within 30 s | 1 row at 36.3 s, 17 `processing` forever → W-B2 |
| A5 | a textless terminal row means "no speech" | 308/354 textless `raw_transcript` rows had `speechDuration` > 0.5 s → **W-A2** |
| A6 | Wispr's ⌘V is seen iff it was posted | Secure Input, lock screen, dead tap → W-C8/C9 |
| A7 | windows measured on one clock | wall-clock windows next to uptime timers across sleep → **W-A5** |
| A8 | `startedAt` and our clock agree | holds: see "No finding" at the end of §3 |

---

## 2 · Timing events × relay state (Engine = Wispr, standalone ON unless noted)

Columns:
- **IDLE**: nothing in flight.
- **OWN-LISTEN**: the relay's own Wispr sentence is open (`isRecording`/`speculative`).
- **SETTLE**: after our stop; `capturing`, row not terminal, `relayOwned`.
- **TAIL**: capture ended, still ≤ 10 s in the `wisprOwnedTail`.
- **HELD**: a prompt is on the panel / the sentence was just delivered.

| # | event (Wispr side) | IDLE | OWN-LISTEN | SETTLE | TAIL | HELD |
|---|---|---|---|---|---|---|
| 1 | our start chord taken **late** 0.2–5 s (cold) | — | ring + chip say Listening from the gesture; the first 0.3–6 s are **lost** (W-D2, `caret-short-cold` red) | refused (F3) | refused? no: not settling → new start ok | ok |
| 2 | our start taken **after 12 s** (after wake, update) | — | at 12 s `speculativeGrace` drops, **WAV deleted** (W-B6). Wispr then records a sentence nobody owns → pasted at the caret after the tail (W-B8, W-A4) | — | — | — |
| 3 | our start **never** taken | — | 12 s drop, WAV deleted (W-B6). If Wispr made a NULL row, it is **confirmed** as Listening instead, and waits 30 s (**W-A1**) | — | — | — |
| 4 | Wispr started **by him** (ptt `54+60`, pill, Wispr's own shortcut) | Wispr's own, pastes at the caret (Q9 as designed) | not seen by the tap. The poll/notify cannot tell it apart; Wispr's hands-free toggle semantics mid-ptt are unknown (W-D5) | invisible to the source (WS:245, WFS:1700); **its ⌘V is firewalled while owned/armed → lost** or re-routed (W-C4, W-D4). The first sentence is blinded by the newer row (W-B1) | ⌘V dropped → `rescueFromRow` → **delivered to the previous sentence's destination** (W-C4, W-C5) | sent to the relay's own route if within the tail (W-C4); `dictationBegan` force-sends the held prompt when standalone is OFF (W-D8) |
| 5 | fn⌃Space typed by him (the tap sees it) | standalone: ignored (WFS:1299) | standalone: ignored as a stop too (WFS:1287), so **Wispr stops and the relay keeps "Listening"** until poll close (needs `pollMs`) → else W-B9 | as #4 | as #4 | as #4 |
| 6 | our **stop before** Wispr started | — | the relay goes transcribing at once. Wispr may start *after* the stop → ghost dictation (W-D6); the relay's capture waits 30 s on a row that records the room | — | — | — |
| 7 | our stop **lost** (Wispr keeps listening) | — | the relay transcribes; the row stays NULL/`recording`; 30 s later *No words came back* and idle. **Wispr still records with no ring**; the next forward click posts a toggle that *stops* it → see **W-A4** | — | — | — |
| 8 | Wispr **stops by itself** (its window, device change, ⌃Esc on the pill) | — | the poll closes it if `pollMs` is set. Otherwise `isRecording` sticks, and the next stop *starts* Wispr (W-B9) | fine | fine | fine |
| 9 | Wispr keeps the mic **open after** its stop | — | — | `lateOpenEdge` ignores it ≤ 12 s. The poll open is a no-op in `transcribing` | fine | fine |
| 10 | second sentence while the first **transcribes** | — | — | relay gestures refused, silently on Wispr (W-D9). His own → row #4 | — | — |
| 11 | rows **out of order / never terminal** | — | — | first row blinded by the newer (W-B1). NULL/`processing` → 30 s stall with refusals (W-B2, W-A1) | rescue picks `newest()`, which may be a still-open *later* row, retries 3 s, and gives up → the earlier sentence is **lost** (§3 note) | — |
| 12 | Wispr **quit / crash / update** (new pid) | next `start()`: `isReady` is prefix-matched, so a helper-only Wispr passes; the capture abandons at 300 ms | abandon → *the sentence is lost* although the meter WAV exists (W-B3, W-D3) | same | — | — |
| 13 | Wispr **hung** (SIGSTOP, beach ball) | chord queued | the pid is alive, so no abandon; 12 s drop or 30 s *No words came back*; on resume Wispr acts on queued chords → ghost (W-B8) | 30 s | — | — |
| 14 | **Mac sleep** mid-sentence / mid-settle | — | uptime timers pause, wall windows run → **W-A5** | same | the tail expires across sleep → his next Wispr paste passes | — |
| 15 | **tap blind** (Secure Input, lock screen: the 07:06–07:14 incident) | Wispr's own paste goes to the front app (fine under Q9) | our gestures are not seen at all; Wispr's ⌘V of **our** sentence is not firewalled → lands in the front app *and* the row is delivered → duplicate (W-C8). A Terminal password prompt holding Secure Input is the front app | same | same | — |
| 16 | Wispr `error` (and a "retry" in its UI) | — | — | `error` → `.silent("Wispr Flow reported error")`, audio thrown away (W-B3). A retry that rewrites the same row is refused by `rescueFromRow` as "already delivered" (WFS:2616) **(PL)** | — | — |

---

## 3 · Findings not covered by B/C/D, ranked by damage

Labels: **CBR** = confirmed by reading (traced to a wrong outcome). **PL** = plausible (depends on
Wispr behaviour I cannot see; the assumed behaviour is stated).

### W-A1 — A row is not a microphone. A NULL row makes the relay say "Listening" over a Wispr that is not recording, then stall 30 s. **CBR + DB evidence**

**Data.** `History` has **100 rows with status NULL** since 2026-08-28. None of them has a
`duration`, `micDevice`, `app`, audio or text: Wispr created the row at the chord and never
recorded. Nine of them are followed by the next row **31–32 s later**:

| NULL row | next row, seconds later | next row's status |
|---|---|---|
| 17059 | 31.6 | NULL |
| 17060 | — | `no_audio` |
| 17063 | 31.3 | — |
| 17064 | — | `no_audio` |
| 17885 | 31.7 | — |

31 s is `captureTimeout` + a re-press: the relay's stall, visible in Wispr's own table.

**Interleaving (relay-started, standalone ON or OFF):**
1. 🔼 → `start()` → `gestureSeen(relay: true)`.
2. Wispr writes row R (NULL) at +357 ms and never opens the mic.
3. `pollHistory` adopts R → `confirmSpeculative(by: "Wispr's own row")` (WFS:2113, 1411–1419).
   This cancels `speculativeGrace` and sets `isRecording = true`.

   The 12 s "Wispr ignored the chord" retraction is now disarmed. Its own comment says it "may only
   fire when Wispr never created a row" (WFS:1355). But the row is exactly what Wispr leaves behind
   when it takes the chord and does **not** record.
4. He speaks the whole sentence into nothing. The chip says Listening; the ring breathes on the
   **relay's meter**, which does hear him.
5. He stops → `stop()` posts the toggle again (WFS:1102). What Wispr does with it is unknown. If
   it starts, that is a ghost dictation (row #6/#7).
6. `closeListening` → R stays NULL → `WisprState.intermediateStatuses` contains `""` (WS:129).
   - The `silenceCeiling` only covers `raw_transcript` (WFS:2152).
   - So 30 s of *Transcribing…*, every start refused (`isWaitingForWords`).
   - Then `captureExpired` → *No words came back* (WFS:2703).
   - The WAV is thrown away (→ W-B3).

**The held-pair variant (standalone OFF only).** Right ⌘⌥ is `.pushToTalk` →
`gestureSeen(confident: false, heldPair: true)`.
- A tap under ~0.4 s: the release arrives while the source is only `speculative`, so
  `pushToTalkReleased` ignores it (WFS:1560).
- R then appears → `confirmSpeculative` → `isRecording = true` and `didBegin` (WFS:1429).
- No release will ever come again, and the poll never saw a mic (`pollMs` nil) → **`isRecording`
  is stuck**.
- `recorderBehindListening` (AD) counts `source.isRecording`, so TR18's stuck-listening cure never
  fires.
- The next 🔼 is read as a **stop** → posts fn⌃Space → Wispr **starts** a hands-free take nobody
  asked for (the W-B9 ending, reached from a different door).

**Expected vs actual.**
- Expected: a row without an open microphone within the grace is "Wispr took the chord and did
  not record" → retract, and keep the WAV.
- Actual: Listening for the whole sentence, 30 s of stall, words lost.

**Fix direction.** Confirm on the row only together with `WS.pollMs != nil`, or with
`speechDuration`/`duration` non-null. Treat NULL + no mic after `speculativeGrace` as the
retraction. Give NULL its own ceiling, like `silenceCeiling`.

**TEST (VM, real Wispr).**
1. Make Wispr take the chord but not record: in the guest, point Wispr's input at a device that
   will not open — select BlackHole 2ch, then `sudo launchctl kickstart -k
   system/com.apple.audio.coreaudiod` 200 ms after the chord.
   - Assumption: this reproduces the NULL row. The DB's NULL rows are the evidence it happens;
     the trigger is PL.
2. 🔼 via `/test/gesture forward-click`, play `CLIP_EN` into BlackHole, 🔼 again.

Assert:
- `GET /test/state.wispr.lags.pollMs == null` ⇒ `isRecording` must go false within 12 s, with a
  retraction line.
- No 30 s `phase=transcribing`.
- `recoverable` set (the WAV).

Held-pair variant, VM with `WT_WISPR_STANDALONE=0` and Wispr's ptt set back to `54+61`: post
right ⌘⌥ down/up 150 ms apart (`helpers/wispr_loopback._post`, `WISPR_PTT_KEYS=54,61`), then
`/test/gesture forward-click` at +3 s. Assert that no new row with a non-null `duration` appears
in the next 40 s.

**Desk.** Needs **H1** (fake `History`): insert a NULL row 300 ms after `/test/wispr
{"hotkey":true}` and never touch it. Assert `state.isRecording == false` at 12.5 s.

### W-A2 — "No speech was heard" is false for most textless Wispr rows. Wispr's own `speechDuration` says there was speech, and the relay has the audio. **CBR + DB evidence**

**Data.** Textless rows since 2026-08-28 (`formattedText` empty), with Wispr's own `speechDuration`:

| status | rows | speech > 0.5 s | mean speech | max speech |
|---|---|---|---|---|
| `raw_transcript` | 354 | **308** | 5.7 s | 40.8 s |
| `error` | 9 | 9 | 9.0 s | 19.7 s |
| `processing` (for ever) | 17 | 16 | 3.9 s | 23.5 s |
| NULL | 100 | 0 | — | — |
| `no_audio` | 22 | 0 | — | — |

The textless `raw_transcript` rows are:
- 288 on `🎓 TO Wispr` (mostly the harness nights of 09-19/09-20)
- **56 on the built-in mic**
- 10 on the DJI / Rx

These are real sentences Wispr heard and failed to transcribe (ASR or network).

**Path.** `pollHistory`: `raw_transcript` + all three texts empty + 8 s → `endCapture` +
`didEnd(.silent("No speech was heard"))` (WFS:2152–2159).
- `error` goes to the default branch → `.silent("Wispr Flow reported error")` (WFS:2231–2238).
- The user reads *No speech was heard* and believes the mic was dead. The meter WAV is orphaned in
  the shots dir; `recording` is only nil-ed at the next `startMeter` (WFS:1741). W-B3/W-D3 cover the
  lost audio; this finding adds that **the relay can tell the two cases apart for free**.

**Expected vs actual.**
- Expected: `speechDuration > 0.5` (or the meter's own `voicedSeconds` ≥ `fallbackVoicedFloor`,
  the rule ElevenLabs already follows) ⇒ this is a *failure with audio in hand* → local fallback
  (`fallBackToLocal`) or Recover.
- Actual: `.silent`, nothing kept, and a false banner.

**Fix direction.**
- `WisprHistory.Entry` should read `speechDuration`.
- `WisprFlowSource` should end these as `.failed(why:, audio: meterWav, duration:)` and set
  `recordsOwnAudio`-equivalent semantics for this path. The ElevenLabs Q8 floor already
  exists (`fallbackVoicedFloor`).

**TEST (VM).**
1. Block Wispr's ASR in the guest mid-sentence: `pfctl` anchor on Wispr's API hosts, after the
   mic opens. This is B §4.5's recipe.
2. 🔼 → play `CLIP_SPEECH` (12 s) → 🔼.

Assert:
- `lastFailure.why` ≠ "No speech was heard"
- `fallingBack == true` → `lastDelivery.via == "local-fallback"`, or `recoverable` set
- Wispr's row: `speechDuration > 0`

**Desk:** H1, insert `raw_transcript` with `speechDuration = 5` and empty texts.

### W-A3 — The idle-after-sleep window: the relay's windows mix wall clock and uptime, so sleep breaks their ordering. **PL (low)**

**Clocks, by construction:**
- **Uptime** (`DispatchTime`, which does not advance in sleep):
  - `speculativeGrace` (`asyncAfter`, WFS:1388)
  - `captureTimeout` (WFS:1908)
  - the 150/100 ms polls
- **Wall clock** (`CFAbsoluteTimeGetCurrent`):
  - `lateOpenGrace` (WFS:1692)
  - `silenceCeiling`'s `took` (WFS:2131)
  - `retiredDiscardUntil` (WFS:1947)
  - `heldPairIsTheEngines` 30 s (HT)
  - `wisprOwnedTail` 10 s and `wisprOwnedCeiling` 11 min (HT `wisprRelayOwnedLocked`)

**Interleaving A.** A relay Wispr sentence is in the settle (row `processing`, Wispr's HTTP
request in flight) and the lid closes.
1. After wake the capture still has, say, 25 s of uptime left.
2. If the settle spanned more than 11 min of wall time, `relayOwned` is false (the ceiling).
3. The capture is still `armed`, so the tap's standalone branch still firewalls. Fine.
4. But the capture then expires or delivers → idle → the tail starts at wall-now, and **the
   ceiling already reads expired**. If Wispr's retry for the old request pastes after that, the
   standalone branch lets it through into the front app.
   - Wispr's behaviour assumed: it retries the sentence after wake and pastes it.

**Interleaving B (standalone OFF).**
1. Speech in the grace window just before sleep.
2. `lateOpenEdge` (wall) has expired by wake, so the CoreAudio churn at wake (devices re-enumerated
   → `WisprWatch.resubscribe` → `publish`) can be taken as a **new** Victor dictation →
   `beginCapture` with a stale `intercepting` → a ring over nothing for up to 30 s.

**Damage.** Wrong-place paste (rare) or a phantom ring.

**TEST (VM).** Tart can suspend the guest: `tart suspend` / resume stands in for a lid.
- 🔼→ bound + clip, stop.
- Block the network (B §4.5) so the row stays `processing`.
- Suspend 12 min, resume, unblock.

Assert: no Wispr paste lands in the front app (the `WisprSink` witness stays empty) and at most one
delivery happens.

**Missing hook:** H5 (`/test/clock-skew`) to fake a sleep without suspending.

### W-A4 — The toggle is driven blind: `start()`/`stop()` never ask Wispr's actual state, although the tap already asks it for the back click. **CBR (relay side). Consolidates W-B8, W-B9, W-D5, W-D6.**

**The asymmetry.**
- `start()` (WFS:734–764) checks only `!isRecording` and `isReady`, where `isReady` is a
  bundle-*prefix* match that is true for a helper-only Wispr (WFS:315). Then it posts fn⌃Space.
- `stop()` (WFS:1052–1105) posts the same toggle whenever `isRecording || speculative`.
- Neither samples `watch.sampleIsRunningInput()` nor asks whether the newest row is open.
- Yet HT's F5/F6 branches (`case VK_F6`: `wisprSentence = backStopsWispr || (wisprMicIsOpen?() ==
  true && !ownDictation)`) **do** decide start-vs-stop from Wispr's live microphone. That is the
  resync the forward click lacks.

**Interleaving (row #7, stop lost, standalone ON).** Wispr's behaviour assumed: it can ignore a
toggle that arrives while it is busy (warming, network stall, beach ball).
1. 🔼 → Wispr records R1.
2. 🔼 (stop) is ignored → the relay's capture waits 30 s → *No words came back* → idle; `relayOwned`
   tail until +40 s.
3. Wispr is **still recording**. There is no ring: the poll is off in `idle`, and standalone
   ignores the edge (WFS:1612).
4. At +2 min he 🔼's for a new sentence → `start()` posts the toggle → Wispr **stops** R1.
   `gestureSeen` re-owns and arms a capture. Its `beginCapture` takes `priorRow = R1`, open ⇒
   `priorRowWasOpen`, but R1's `startedAt` < `openedAt − 2`, so R1 is never adopted.
5. R1's ⌘V (2 min of room audio) is firewalled (owned) and dropped as "the History row delivers"
   (WFS:2584). Lost. That is the lesser evil: had the ownership tail expired, it would have been
   **pasted into the front app**.
6. The new gesture made no row (the toggle was a stop) → 12 s → "Wispr ignored the chord", WAV
   deleted (W-B6).

Net:
- two sentences lost
- ~2 min of unannounced recording
- one 12 s ring over nothing

**Fix direction.**
- `start()`: if `watch.sampleIsRunningInput()` or the newest row is open with `startedAt` < now,
  then Wispr is already recording. **Adopt it** (or refuse with a banner); never post a toggle
  into it.
- `stop()`: if the mic is not open and the row is not open, close without posting.
- The same 3-read sampler that `wisprMicIsOpen` uses.

**TEST (VM, real Wispr; needs H2 `/test/wispr-proc`):**
1. 🔼, wait for the mic, play `CLIP_EN`.
2. `POST /test/wispr-proc {"stop": true}` (SIGSTOP Wispr's main pid).
3. 🔼 (the stop is queued, not lost).
4. After 400 ms, `{"cont": true}`.

Variants:
- `{"drop-next-chord"}`: not possible from outside, so emulate a lost stop by posting nothing and
  calling `/test/cancel`-free `closeListening`. That needs H4 (`/test/wispr {"relayStopOnly":true}`:
  run `closeListening` without posting).
- Assert over 60 s: `state.wisprMicOpen` (H3) is false within 2 s of every relay stop.
- The next 🔼 leaves `wisprMicOpen` true, and its row is adopted (`state.wispr.row` = the new
  rowid).
- The `WisprSink` witness stays empty.

### W-A5 — Notes (lower, or partially covered)

- **Rescue during two unseen sentences (row #11).** `rescueFromRow` only looks at `newest()`
  (WFS:2616).
  - Sentence X's ⌘V arrives while a later sentence Y already has an open row → 20 retries × 150 ms
    → "never became terminal".
  - **X is lost**; Y is rescued later.
  - Reachable under standalone inside the ownership tail (W-C4 window). Fix: rescue the newest
    *terminal* row after `lastRow`, not the newest row.
  - **CBR**, trigger PL.
- **`isReady` is a prefix match (WFS:315).** A helper-only or ShipIt-only Wispr passes. It costs
  300 ms (the pid check abandons fast), but the gesture's flags stand (W-D10). **CBR**, low.
- **Ownership tail vs the e2e tail.**
  - The owned tail starts at the relay's idle. That is `captureTimeout` (30 s) or `silenceCeiling`
    (8 s) after the stop.
  - A Wispr paste later than idle + 10 s (e2e > 40 s: none in 30 days, max 36.3 s) passes into the
    front app **for a relay-started, bound sentence**: the words are misdelivered to where the caret
    is.
  - Complement of W-B2 (≤ 10 s → dropped as "already delivered"). **PL**.

**No finding — clock skew between our clock and `History.timestamp` (A8).**
- The column is stored as UTC with an offset (`2026-09-27 17:58:54.155 +00:00`, read from the DB),
  so `strftime('%s')` is correct.
- It truncates to whole seconds; the `openedAt − 2` tolerance (WFS:2105) absorbs that.
- The residual risk is B's epoch/`T…Z` format change (W-B4) and B's quick re-press (W-B7), not
  skew.

---

## 4 · Harness hooks that timing cases need (beyond B §4 H1–H5 and C §4)

| id | hook | why |
|---|---|---|
| **H1** | `WT_WISPR_DB=<path>` + a fake-row writer (= B §4.1) | W-A1, W-A2 and row #11 become desk-deterministic |
| **H2** | `POST /test/wispr-proc {"stop"｜"cont"｜"kill"｜"relaunch", "afterMs"?, "forMs"?}`: SIGSTOP/SIGCONT/SIGKILL on the **anchored main executable's** pid, optionally scheduled relative to the next chord this app posts (`afterMs` after `postWisprHandsFree`) | delays Wispr's chord handling and mic open by N ms (rows 1, 2, 13), and the late-start > 12 s orphan (W-B8). Mirrors G4's `/test/whisper` |
| **H3** | `GET /test/state.wisprTruth = {micOpen: sampleIsRunningInput(), newestRow: {rowid, status, startedAt, speechDuration}}` | the toggle-desync detector: relay belief vs Wispr's truth in one assertion (W-A4, W-B9, W-D6) |
| **H4** | `POST /test/wispr {"relayStopOnly": true}` (close without posting) and `{"postOnly": true}` (post without touching state) | emulate a lost stop / an extra toggle deterministically |
| **H5** | `POST /test/clock-skew {"wallSeconds": n}`: add n to every wall-clock window read (`CFAbsoluteTimeGetCurrent` sites listed in W-A3) | emulate sleep without `tart suspend` |
| **H6** | `POST /test/wispr-handsfree {"hand": true, "ptt": <ms>, "keys": "54,60"}`: post Wispr's **real** ptt pair (device bits) for N ms as his | today the route posts only fn⌃Space. Row #4 (his `54+60` ptt during the settle/tail) is the commonest overlap and has no route |

The Secure-Input case already has its hook: `POST /test/tap {"kill":"secure","seconds":n}`. Row
#15 in the VM: hold it for 20 s, drive Wispr's ptt with H6, and assert that the `WisprSink` witness
receives nothing **and** exactly one delivery happens.

---

**Top 5 (this file only):**
1. **W-A1** — a NULL row confirms "Listening" over a Wispr that never recorded, then a 30 s stall.
   With standalone OFF, a short ⌘⌥ tap sticks `isRecording` and the next stop *starts* Wispr.
2. **W-A2** — *No speech was heard* is false for 308/354 textless rows (Wispr's `speechDuration`
   says speech), and the relay drops the WAV it holds.
3. **W-A4** — start/stop post the toggle blind. One mic/row sample before posting (already done for
   F6) closes W-B8/B9/D5/D6.
4. **W-A5** — rescue reads `newest()` only, so an earlier unseen sentence is lost behind a later
   open row. The ownership tail can also let a > 40 s Wispr paste of a bound sentence into the
   front app.
5. **W-A3** — wall-clock windows vs uptime timers across sleep (PL, low).
