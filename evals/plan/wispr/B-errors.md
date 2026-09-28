# Wispr Flow as the engine — B: errors, retries and the `History` row

*Adversarial read, 2026-09-28. Source read-only; the real `flow.sqlite` was queried with
`sqlite3 -readonly "file:…?mode=ro"`, aggregates only, no transcript text printed. Nothing was run.*
Code refs are `WisprFlowSource.swift` (WFS), `WisprHistory.swift` (WH), `WisprNotes.swift` (WN),
`AppDelegate.swift` (AD) unless stated otherwise. AD line numbers as of 2026-09-28 (the file was being edited by another session while this was written).

**Tags:** **CBR** = confirmed by reading the code path (the Wispr behaviour it needs is stated, with
DB evidence when there is some). **PL** = plausible: the code path is confirmed, but the Wispr
behaviour that sets it off has not been observed.

---

## 1 · The `History` row lifecycle (what the DB says, 17 890 rows, 2026-01-15 → 2026-09-27)

Schema: `transcriptEntityId VARCHAR(36) PRIMARY KEY` (**not** an INTEGER PK, so `rowid` is
implicit), 60+ columns. `rowid` runs 1…17 890 with no gaps, and rowid order equals `timestamp`
order across the whole table (0 inversions). That means no deletes, no archives
(`isArchived` = 0 everywhere) and no REPLACE-style re-inserts so far.

| stage | columns written | evidence |
|---|---|---|
| **gesture** | `transcriptEntityId`, `timestamp` (text, `YYYY-MM-DD HH:MM:SS.mmm +00:00`), `status` **NULL** (not `''`; WH coalesces it to `''`) | 100 rows in Sept stay like this for ever: no `app`, `micDevice`, `duration` or `audio` |
| **mic close** | `status='processing'`, `duration`, `audio` blob | 17 Sept rows stay `processing` for ever (avg 5.3 s speech, audio kept by Wispr, no text) |
| **finish** | `asrText`, `formattedText`, `pastedText`, `serverFinalizedText`, `e2eLatency`, `app`, `micDevice`, `detectedLanguage`, `status` → terminal | `row-watch` (journal 2026-09-22): all text columns land in the same tick as the terminal status |
| **after delivery** | `editedText`, `contentObservationEndReason`, `editDistanceToDictated` (Wispr watches the textbox after its paste) | 683 Sept rows have `editedText`. `contentObservationEndReason = dictated_text_not_found` on **3001** Sept rows: the firewall dropped the paste, so Wispr's observer is watching a textbox its words never reached |
| never | `language` (always NULL: the relay reads it, WH:111, so it always gets `''`); `editedTextStatus` stays `NOT_EXTRACTED` | 0 / 5000 formatted rows in Sept |

Text columns, Sept `formatted` (n = 5000):

- `pastedText ≠ formattedText` 4748 (3074 after trim; 1524 are the same text plus a trailing space).
- `serverFinalizedText = pastedText` 4918. `pastedText` is the final text and `formattedText` is
  one pass earlier. `Entry.text` prefers `pastedText`, which is right. Scratchpad mode prefers
  `formattedText` (WFS `deliverFromRow`) and so delivers the earlier pass in 57 % of rows. Low
  damage, noted.

Terminal and stuck statuses, all time / **Sept, excluding rig mics**:

| status | all | Sept (Victor) | text? | `e2eLatency` | relay reading |
|---|---|---|---|---|---|
| `formatted` | 15 204 | 561 | yes | p50 0.85 s · p90 2.8 s · p99 4.5 s · **max 36.3 s** (Sept, all mics) | deliver |
| `raw_transcript` | 1139 | 85 | 452 with text / 687 without | — | text → `rawTextSettled`; empty → `silenceCeiling` 8 s |
| **NULL** (`''`) | 813 | **100** | never | — | intermediate → **waits the full 30 s** |
| **`processing`** | 31 | **17** | never | — | intermediate → **waits the full 30 s** |
| `dismissed` | 504 | 149 | never | — | `.cancelled(audio: nil)` |
| `no_audio` | 76 | 22 | never, `duration 0.0` | — | `.silent("No words detected")` |
| **`error`** | 16 | 6 | never | **33 020 / 33 029 ms** (the 2 that carry one) | would be `.silent("Wispr Flow reported error")`, but the relay has already given up at 30 s |
| `empty` | 100 | 0 | — | 10.3 s avg | `.silent("No words detected")` |

**The slow tail is Wispr's own fallback ASR.** Formatted rows over 20 s in Sept: 24.2, 27.3, 28.0,
28.4 s (all `usedFallbackAsr = 1`) and 36.3 s (`calledExternalAsr = 1`, `clientNetworkLatency`
11.3 s). Every error row has `fallbackLevel = 2`. Wispr's own give-up is therefore **≈ 33 s after
mic close** (`e2eLatency` counts from mic close: row 16759 went `processing` at +29.6 s and
`formatted` at +33.7 s with e2e 4152). The relay's `captureTimeout` is **30 s** from its own stop.
**Wispr finishes after the relay has given up**, for successes (36.3 s) and failures (33 s) alike.

---

## 2 · Error × relay state

Relay states: **W** warming (chord out, no row, no mic) · **L** listening · **T** transcribing
(capture armed, row adopted) · **X** after the capture ended (timeout or delivery) · **N** the next
sentence is in flight on top.

| Wispr event | W | L | T | X | N |
|---|---|---|---|---|---|
| network down / 5xx (row `processing` or NULL for ever, `error` at ~33 s) | — | recording normal | **30 s of "Transcribing", then `No words came back`; meter WAV orphaned** (W-B3) | the late `error` is ignored (fine) | **the next sentence rides the zombie capture** (W-B1) |
| slow fallback ASR, `formatted` at 24–36 s | — | — | margin < 6 s; past 30 s: `No words came back` | **the late row is dropped, "already delivered"** (W-B2) | old words arrive in the new sentence's place (W-B1) |
| retry clicked in Wispr's UI (same row goes terminal later, Wispr pastes) | — | — | — | paste eaten by the firewall; rescue refuses `lastRow`, **or after a relay restart re-delivers an older sentence** (W-B5) | eaten by the firewall; nothing delivered |
| `no_audio` / mic permission lost / Loopback pass-thru dead | — | — | `No words detected`; **meter WAV with his speech discarded** (W-B3) | — | — |
| logged out / Wispr hung (SIGSTOP) / chord ignored | **relay-started sentence silently cut at 12 s, meter WAV deleted** (W-B6) | — | stuck row → 30 s (W-B3) | SIGCONT: Wispr can start late on the queued chord and be adopted (W-B8) | — |
| Wispr quit / relaunched | — | caught in ≤ 300 ms (pid check) | `Wispr Flow quit — the sentence is lost`, WAV orphaned (W-B3) | — | — |
| Wispr ends the take itself mid-sentence (device gone, internal error) | — | poll closes it (needs `pollMs`); a terminal row while `isRecording` ends the sentence relay-side but not source-side (W-B9) | — | — | — |
| auto-update: renamed column / new `timestamp` type / replaced file | **every Wispr sentence lost, and Wispr's own paste eaten too** (W-B4) | ← | ← | ← | ← |
| DB busy > 50 ms / transient I/O error | poll skips a tick (fine) | — | `status(of:)` answers `''` → the zombie guard holds (W-B1 trigger) | the last look at the timeout fails → lost | — |
| `formattedText` rewritten after delivery (`editedText`, observer) | — | — | — | never re-read → no double delivery ✔ | — |
| a quick re-press: a stale NULL row created ≤ 2 s before the gesture | **adopted as this sentence's row** (W-B7) | ← | the real row is never read | — | — |

---

## 3 · Findings, by damage

### W-B1 · A second Wispr sentence during a non-terminal row: both are blinded. The old words land in the new sentence's slot and the new sentence is lost. **CBR**

**Path.**

1. Victor starts sentence 2 with his own Wispr chord or the held right ⌘⌥. That goes
   `onWisprMaybeStarting` → `gestureSeen`, with no `isWaitingForWords` gate: that gate is only in
   `startDictation`.
2. The gate it does meet is `retireCaptureIfSettled` (WFS:1344, 1930). Sentence 1's row is not
   terminal, so the capture stays standing.
3. `beginCapture()` (WFS:1396) returns at `guard !capturing` (WFS:1778). Sentence 2 now rides
   sentence 1's capture: `historyRow` is still row 1, and `armedAt` is older than `chordAt`, so the
   state machine is never fed (WFS:2129).
4. `pollHistory` reads **only `WisprHistory.newest()`** (WFS:2097). Row 2 is on top, so
   `guard e.rowid == historyRow` (WFS:2115) returns on every tick. Row 1 going terminal is never
   seen, and row 2 is never adopted.
5. Sentence 2's stop calls `armCaptureDeadline` (WFS:1495), which **cancels sentence 1's deadline**
   and starts a new 30 s.
6. At that timeout `captureExpired` reads `entry(rowid: historyRow)`, which is **row 1**
   (WFS:2685). If row 1 finished in the meantime, **sentence 1's words are delivered as sentence
   2's**, to sentence 2's latch.
7. Row 2's ⌘V is dropped by the firewall and `injected` says "the History row delivers" (≈WFS:2583).
   Nothing ever reads row 2. **Sentence 2 is lost.**
8. If row 1 never finishes (NULL or `processing` for ever), the result is `No words came back` and
   sentence 2 is lost anyway.

**The trigger is ordinary.** A Wispr hiccup (117 stuck rows among Victor's Sept dictations, plus
the 24–36 s tail) leaves the chip on "Transcribing". He repeats the sentence with his keyboard
chord, and the repeat is eaten too. The retry is exactly what a person does.

**Fix direction.** Once a row is adopted, poll `entry(rowid: historyRow)`, never `newest()`. Give
each dictation its own capture record: a standing capture for the old row, plus a fresh one for
the new gesture.

- **Desk:** there is no fake-row hook (see §4). With `WT_WISPR_DB`: arm a relay sentence, write
  row A (`NULL`), stop, then `POST /test/wispr {"hotkey":true}` and write row B (`NULL`). Flip B
  to `formatted "BEE"` at +1 s and A to `formatted "AAA"` at +5 s. Expect "BEE" delivered at +1 s
  and "AAA" either delivered or reported late. Today: nothing until +30 s, then "AAA" in B's slot.
- **VM:** in the guest, `sudo pfctl -e` with a rule blocking Wispr's API hosts (or
  `dnctl pipe 1 config delay 20000` for a slow link). Relay sentence 1 via
  `/test/wispr-handsfree`, then 2 s after its stop a hand chord (`/test/wispr-handsfree
  {"hand":true}`) playing a different clip into BlackHole. Lift the block 10 s later. Assert
  `outbox.jsonl` has 2 lines with the right texts, in order. Today: 1 line, the wrong text, at
  ~+30 s.

### W-B2 · A row that finishes after the 30 s is thrown away, and the log says "already delivered". **CBR (Wispr timing observed)**

**Path.**

1. At 30 s, `captureExpired` → `No words came back` → `endCapture`, which sets
   `lastRow = historyRow` (WFS:2796).
2. The row goes `formatted` at 33–36 s. Wispr presses ⌘V and the firewall drops it.
3. `injected`: no capture is open, so it calls `rescueFromRow` (WFS:2568).
4. `newest() == lastRow` → *"the newest row is one already delivered — nothing to put anywhere"*
   (WFS:2616). The words sit in Wispr's History while the log says they were delivered.

**Evidence.** One Sept `formatted` row at 36.3 s. Four at 24–28 s (fallback ASR) have under 6 s of
margin. Wispr's `error` arrives at 33 s, which shows Wispr's own budget is longer than ours.

**Fix direction.**

- Tell `lastRow` apart from `lastDeliveredRow`.
- Keep a *late-row watch* on a timed-out row for about 60 s. If it goes terminal with text,
  deliver it flagged `late` (or hold it for the panel).
- Raise `captureTimeout` above Wispr's 33 s, or better, key it off the row: stay patient while it
  says `processing`, give up early on NULL with no mic.

- **VM:** `dnctl` delay of 32 s on Wispr's API hosts. Dictate one relay sentence. Assert the words
  are delivered or held, not the `already delivered` line. Also run it at 25 s to confirm the
  margin holds today.
- **Desk:** fake writer: row `processing` → `formatted` at +31 s, plus
  `POST /test/wispr {"injectCmdV": true}` (missing hook, §4).

### W-B3 · Every Wispr failure throws away a recording the relay already holds: no local fallback, no Recover. **CBR**

**The relay has the audio.** The meter records his voice for every Wispr sentence
(`startMeter`, WFS:1722, `wispr-<ts>.wav`). `stopMeter(keep: true)` keeps it as `self.recording`
(WFS:1765).

**Every failure throws it away.** Timeout (`No words came back`, WFS:2703), `error` / unknown
status, `no_audio` / `empty` (WFS:2227), stuck NULL / `processing`, and `Wispr Flow quit`
(WFS:2344) all end as `.silent(...)`. None of them carries `audio:`.

- Wispr's `recordsOwnAudio` is `false` (DictationSource.swift:398), so `AD.fallBackToLocal`
  (AD:3663) cannot run.
- The comment above it, *"Wispr's audio never reaches this app"*, is false: the meter WAV is that
  audio, or near enough.
- `.silent` flashes for 8 s and stages nothing for *Recover* (AD:3787).
- The next `startMeter` sets `self.recording = nil` (WFS:1741) without deleting the file, so the
  WAV is left orphaned in the shots staging folder.

**Damage.** During any Wispr outage, every sentence costs 30 s of a blocked relay (starts are
refused while `isWaitingForWords`) and is then lost. `no_audio` after a dead Loopback pass-thru
(see memory: *Loopback pass-thru dies silently*) is a case where the meter, on the default input,
heard him fine.

**Fix direction.** End these as `.failed(why, audio: meterWAV)`, behind the same ≥ 1.5 s voiced
floor Scribe uses (`MicRecorder.voicedSeconds`). Let `fallBackToLocal` accept Wispr. Stamp
the row as "owned by fallback" so a late W-B2 delivery cannot double it.

- **VM:** `pfctl` block of Wispr's hosts; dictate 12 s. Assert `state.fallingBack` goes true and
  `outbox` shows `via: local-fallback`, or failing that `recoverable` is set. A second variant:
  `killall -STOP "Wispr Flow"` right after the stop chord (upload stalled), `-CONT` at +40 s.
- **Desk:** fake writer with a NULL row that never moves, and a `/test/dictation/start`-style
  Wispr sentence with the meter on (needs the `WT_WISPR_DB` hook).

### W-B4 · A Wispr auto-update that changes the row's shape fails *closed*: every Wispr sentence is lost, and Wispr's own paste is eaten too. **CBR code path / PL trigger**

Wispr updates itself (Squirrel). Its `appVersion` moved 1.6.721 → 1.6.957 within Sept, and the
columns added so far were additive. Three ways an update breaks the reader:

- **A renamed or dropped column** named in the one SELECT (WH:108–112): `prepare` fails,
  `Log.error` fires, the handle is reset, and every read is nil for ever (WH:116–120).
- **`timestamp` stored as epoch ms or ISO `T…Z`:** `strftime('%s', …)` returns NULL, so
  `startedAt = 0`, so `e.startedAt >= openedAt - 2` (WFS:2105) is never true. **No row is ever
  adopted, and nothing is logged.** One row already has a NULL `timestamp`.
- **The DB replaced by a migration copy:** the cached handle (WN:33) keeps reading the unlinked
  old inode, and `newest()` answers the same old row for ever.

**All three end the same way.**

- No row, so `No words came back` after 30 s. The log says "Wispr never created a row".
- `HotkeyTap` still drops Wispr's ⌘V (stateless, by pid), so Wispr cannot insert either.
- This holds whatever Engine is picked: his own Wispr chord under ElevenLabs is lost the same way.
- The canary checks the tap, not the reader, so `/test/firewall` answers `alive`.

**Fix direction.** A reader health check at launch, on Wispr relaunch and whenever `appVersion`
changes: `newest()` non-nil, `startedAt` within the last N days, `rowid` ≥ the last one seen.
While it fails, **open the firewall** (let Wispr paste) and flash once. Re-stat the file's inode on
every capture.

- **VM (the one place it is safe):** quit Wispr in the guest, run
  `ALTER TABLE History RENAME COLUMN pastedText TO pastedText2` on a copy, and swap it in (or
  point `WT_WISPR_DB` at a doctored copy). Dictate. Assert the relay flashes and lets Wispr's paste
  through, rather than eating it.
- **Desk:** `WT_WISPR_DB` → a copy with an epoch `timestamp` written by the fake writer.

### W-B5 · A Wispr ⌘V outside any capture re-delivers an old sentence into the bound agent after a relay restart. **CBR code path / PL trigger**

**Path.** `rescueFromRow` (WFS:2611) takes `newest()` if `rowid ≠ lastRow`, with **no freshness
check** (no `startedAt` against now). `lastRow` lives in memory and is nil after every
`relay-restart.sh`.

**Triggers.**

- Wispr's *paste last transcript* shortcut (`13+55+59`, in his `config.json`).
- A Retry or re-paste from Wispr's History window.
- A late W-B2 row after a restart.

Any of them makes Wispr post a ⌘V, the firewall drops it, and the rescue hands the newest row
(possibly hours old, already delivered before the restart) to `AD.deliver` with `.route`. It goes
to the bound terminal, not the caret he was pasting into.

**Fix direction.** Persist `lastRow` (or read the newest `outbox.jsonl` line). Rescue only rows
whose `startedAt` is within about 60 s. For a row that is not new, let Wispr's paste through
instead of dropping it.

- **Desk (safe):** bind a scratch terminal, `./relay-restart.sh`, then press ⌘⌃W (`paste_last_text`)
  with TextEdit in front. Assert nothing reaches the bound tty, and preferably that the text lands
  in TextEdit.
- **VM:** the same, plus a History-window Retry on an `error` row produced with `pfctl`.

### W-B6 · A relay-started sentence that Wispr never answers is cut silently at 12 s and its audio deleted. **CBR**

**Path.**

1. A confident gesture sets `isRecording = true` and `didBegin`, but `speculative` stays true until
   a mic or a row confirms it.
2. If Wispr is logged out, SIGSTOPped, its shortcut changed, or it lacks mic permission and creates
   no row, the `speculativeDrop` fires at 12 s. It calls `stopMeter(keep: false)`, **deleting the
   WAV** (WFS:1378), then `didEnd(.silent(""))` (WFS:1384).
3. `.silent("")` means **no flash** (AD:3791 `if !why.isEmpty`).

A long sentence is cut mid-word, the ring vanishes, and the log's "it ignored it" is all there is.

**Fix direction.** For a relay-started sentence, keep the meter running and end with
`.failed("Wispr Flow did not answer the chord", audio:)`, which goes to the local model. Always
flash a reason.

- **VM:** `killall -STOP "Wispr Flow"`, then `/test/wispr-handsfree`, and play 20 s into BlackHole.
  Assert a flash, and that `recoverable` is set or a local-fallback delivery happens. Variant: sign
  out of Wispr in the guest.
- **Desk:** the same with `kill -STOP` on the host's Wispr, **only with Victor's OK** (it is his
  live tool). Prefer the VM.

### W-B7 · A quick re-press adopts the stale row of the chord Wispr ignored. **CBR code path / trigger seen in the DB**

**Path.** A chord leaves a NULL row (Wispr took it, never recorded), and Victor presses again
within about 2 s. `priorRow` is the NULL row with `priorRowWasOpen = true`. On the first tick,
before Wispr writes row 2, `newest()` is the NULL row: `isNew` is true, and `startedAt` (floored
to the second by `strftime('%s')`) passes `≥ openedAt − 2` (WFS:2104–2105). **The dead row is
adopted.** Row 2 then lands on top and is never read (the WFS:2115 blindness, as in W-B1). The
outcome is 30 s, then `No words came back`, for a sentence Wispr transcribed.

**Evidence.** Of the 100 Sept NULL rows, 11 have the next row within 2 s and 28 within 10 s.

**Fix direction.** Never adopt `priorRow` itself; adopt only a rowid greater than `priorRow`. Once
W-B1 is fixed, read by rowid.

- **Desk:** fake writer: row A `NULL` at t−1 s; arm the gesture; write row B at +0.4 s and flip it
  to `formatted` at +1 s. Assert B is delivered.
- **VM:** double-tap the hands-free chord 300 ms apart with no audio, then dictate. Inspect
  `state.wispr.row`.

### W-B8 · A hung Wispr resumes and starts a dictation nobody asked for; the relay adopts it and delivers the room. **PL**

**Path.** A chord posted while Wispr is SIGSTOPped or beach-balled can be processed on resume. By
then the relay has retracted the sentence (W-B6). The open edge is not `lateOpenEdge()`, because
the relay never stopped it (`lastStopAt < gestureAt`, WFS:1692). `edge(on)` therefore adopts it as
Victor's own dictation (WFS:1626–1638): ring up, capture armed. Hands-free runs until someone
toggles it; Wispr's longest take on record is 1196 s. Whatever it hears is delivered to the bound
agent.

**VM:** `kill -STOP`, post the chord, wait 13 s, `kill -CONT`. Poll `wisprHearing` and `outbox`.
Expect: no adoption, or an adoption that is flagged.

### W-B9 · Wispr ends the take by itself while the relay thinks it is recording: the two sides split, and the next stop chord *starts* Wispr. **PL**

**Path.** Suppose the row goes `no_audio` / `dismissed` / `error` while `isRecording` (for example
the Wireless Rx is unplugged mid-sentence), and the 100 ms poll misses the close because
`pollMs == nil` (WFS:1526). Then `pollHistory` → `endCapture` → `didEnd(.silent)` ends the sentence
in AppDelegate, but `isRecording` stays true in the source, and `endCapture` even re-arms a capture
(WFS:2857). His next stop calls `stop()`, which posts the **toggle** chord (`postWisprHandsFree`)
into an idle Wispr. That opens a phantom hands-free dictation of the room.

**Fix direction.** A terminal row while `isRecording` must go through `closeListening` first.
`stop()` must not post a toggle when `state.status` is already terminal.

**VM:** start a relay sentence, then remove BlackHole from Wispr (`sudo killall coreaudiod`) or
dismiss from Wispr's pill. Then send the relay's stop. Assert Wispr's mic stays closed and no new
NULL row appears.

### W-B10 · Smaller

- **`processing` and NULL are never timed out early.** `silenceCeiling` applies only to empty
  `raw_transcript` (WFS:2152), so a row NULL with no mic seen, or `processing` for 10 s, still costs
  the full 30 s during which starts are refused. The 8 s ceiling is also unproven against the
  fallback-ASR path: if that path passes through an empty `raw_transcript` before `formatted` at
  24–28 s, the relay says *No speech was heard* at 8 s and the words are then dropped (W-B2).
  **VM:** `dnctl` 20 s, and watch the sequence with `tools/wispr-row-watch.py`.
- **A transient read error looks like a non-terminal row.** `status(of:)` returns `''` on a nil
  read (WFS:2050), which holds the W-B1 guard. Also, `sqlite3_step ≠ ROW` (BUSY/IOERR) is neither
  logged nor reset (WH:122).
- **`dismissed` that Wispr decided on its own** (not ⌃Esc) → `.cancelled(audio: nil)`: silent, and
  the meter WAV is not offered to Recover.
- **Firewall side effect, not a relay bug:** Wispr's post-paste observer runs against the wrong
  textbox (3001 `dictated_text_not_found` in Sept). With `shouldAutoLearnWords` on, it may "learn"
  from whatever Victor types next. Worth a look at the synced dictionary.
- **`language` is always empty.** The relay should read `detectedLanguage` (filled on 4998 / 5000).
- **VACUUM would renumber the implicit rowid.** A VACUUM mid-capture would point `historyRow` /
  `retiredDiscardRow` at another sentence. Not observed (the rowids are dense and ordered).

---

## 4 · Harness hooks that are missing

1. **`WT_WISPR_DB=<path>`**: `WisprFlowDB.url` is hard-coded (WN:25). With it, a copy of the
   schema (`sqlite3 flow.sqlite .schema History`) can be written by a tiny
   `tools/wispr-fake-row.py {insert|status|text|epoch-timestamp|rename-column}`, which makes every
   desk case above deterministic, with no network and no real Wispr. The pid-at-chord check needs
   `WT_WISPR_FAKE_PID=$$` alongside it (or an off switch).
2. **`POST /test/wispr {"injectCmdV": true}`**: feed `injected(from: "Wispr Flow")` without a
   keystroke, to drive the rescue and late-⌘V paths.
3. **`GET /test/state` → `wispr.lastRow`, `wispr.captureRow` vs `wispr.newestRow`**, plus
   `meterWav` (is there a recording in hand?). W-B1 and W-B7 become one assertion
   (`captureRow ≠ newestRow` while a sentence is live).
4. **`POST /test/wispr {"captureTimeout": s, "speculativeGrace": s}`**, so a desk run need not
   sleep 30 s.
5. **VM network shaping recipe** in `docs/vm-lab.md`: `pfctl` anchor blocking `*.wisprflow.ai` /
   the API hosts (read them from the guest's `lsof -i -P | grep Wispr`), plus `dnctl` pipes for
   20 / 32 / 40 s delays. This one recipe provokes the `processing`, `error`, fallback-ASR and late
   rows on demand.
