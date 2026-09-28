# Wispr Flow's integration surfaces: what the relay can listen to (2026-09-28)

Host-side, read-only survey of Wispr Flow 1.6.957 (`/Applications/Wispr Flow.app`, running as pid 5285).
Nothing was quit, restarted, typed or shown. `flow.sqlite` (+`-wal`/`-shm`) was APFS-cloned (`cp -c`)
into the scratchpad before it was opened. `app.asar` was extracted there with `npx @electron/asar`.
Nothing was written into Wispr's folders and the VM was not touched.
Question: is there a signal faster or more reliable than polling `History` every 150 ms?
And what explains the wave-2 losses (rows stuck `processing`, NULL rows, finding A)?

## Verdict in one paragraph

No surface Wispr offers is both *push* and *carries the text*. It opens no localhost port, has no XPC or
Mach service and posts no distributed notifications. File logging is off in the packaged build, and the
official API is cloud transcription only. The biggest win is not a new signal: the relay misreads the
signal it already has. From Wispr's own code, `raw_transcript` is **final**, a NULL row means **the stop
path never ran**, and `processing` means **the result was dropped** once a newer dictation or a dismiss
superseded it. Those rules let the relay call a row dead within one tick instead of 30 s (or never,
under Q24). Second: wake on the WAL file instead of the timer. Third: read Wispr's promised pasteboard
item at the swallowed ⌘V. Fourth, for control rather than observation: Wispr has **state-guarded deep
links** `wispr-flow://start-hands-free` / `stop-hands-free`. They could replace the blind fn⌃Space
toggle behind the ghost microphone (W6).

## Ranked candidates

| # | signal | latency vs today | reliability | effort | verdict |
|---|---|---|---|---|---|
| 1 | **Row lifecycle rules** on the rows already read (NULL / `processing` / `raw_transcript` semantics, newer-rowid and pid tests) | dead rows: 30 s → ≤ 1 tick | high: taken from Wispr's source | S | **do now** |
| 2 | **kqueue on `flow.sqlite-wal`** (`DispatchSource` vnode `.write/.extend/.delete/.rename`) + `PRAGMA data_version` gate, 1 s safety timer | −75 ms avg (poll tick 150 ms), near-0 idle CPU | high; WAL is rewritten on every commit | S | **do now** |
| 3 | **Promised pasteboard item at the ⌘V** (Wispr uses delayed rendering) | text ~74 ms before the row (p50; p90 135 ms) | medium: only on the paste path, not for empty/failed rows | S–M | do with ownership fix (B) |
| 4 | **Deep links** `start-hands-free`, `stop-hands-free`, `switch-mic?mic_name=` | unmeasured (Apple Event via LaunchServices) | idempotent, guarded by Wispr's own state | M | measure in the VM, then replace the toggle |
| 5 | `log stream` on the helper: `data requested for type public.utf8-plain-text` (paste consumed), `TCCAccessRequest` (start) | push, ~tens of ms | heuristic, no text, generic messages | M | lab diagnostics only |
| 6 | Dev JSONL sidecars (`prefs.user.internal.shouldSaveAxText: true` → `~/Library/Logs/Wispr Flow/dictation-event-debug.jsonl`, events `init/commit/context/result` with status + pastedText) | push, per event | internal switch, may vanish; also saves AX text/HTML of every field to disk and DB | S to enable | **no** (privacy), lab-only if ever |
| 7 | CoreAudio `kAudioProcessPropertyIsRunningInput` | already used (`WisprWatch`) | the mic is held by the Chromium AudioService helper (pid 5999, `--utility-sub-type=audio.mojom.AudioService`); the prefix match already covers it | — | keep |

Dead ends (evidence):
- **No port.** `lsof -iTCP -sTCP:LISTEN` shows no Wispr process listening. Main holds one TLS socket to AWS.
- **No IPC we can join.** The Swift helper `com.electron.wispr-flow.accessibility-mac-app` talks to main over
  stdio unix sockets (fd 0–3). Its 97 message names (`DictationStart`, `PasteText`, `PasteOutcome`,
  `ClipboardChanged`, `MicrophoneHoldersChanged` …) are private.
- **No notifications** (no `NSDistributedNotificationCenter` names in either binary). **No usable local server.** `EVAL_SERVER=1` starts a local server, but its only route is
  `/eval/instruct_mode`. `ax-inspect-server.mjs` is a dev dashboard over the same `flow.sqlite`.
- **No file logs.** `transports.file.level = !app.isPackaged && "silly"`, and `main.log` is deleted at start.
  `~/Library/Logs/Wispr Flow/` is empty.
- **Unified log.** It carries only system-framework lines (network, TCC, AppKit pasteboard), confirming
  the 2026-09-12 journal.
- **No dictation URL schemes.** The only ones are `wispr-flow://open`, `auth/…`, `billing/…`, `linkedin/…`
  and the three in #4.
- **Official API.** REST transcription, exclusive access, no desktop events ([quickstart](https://api-docs.wisprflow.ai/quickstart),
  [platform](https://platform.wisprflow.ai/login), [developers](https://wisprflow.ai/developers)); the only "SDK" is a
  reverse-engineered cloud client ([wisprflow-sdk](https://github.com/ThisisShashwat/wisprflow-sdk)).
- **Release notes.** Nothing on integrations ([changelog](https://roadmap.wisprflow.ai/changelog), [what's new](https://wisprflow.ai/whats-new)).

## Item 3: the `History` row, from Wispr's own code (`.webpack/main/index.js`)

Schema: 68 columns, PK `transcriptEntityId`, **no triggers, no `updated_at`**, WAL mode. The only time
column is `timestamp`, the *start*. `duration` / `speechDuration` / `audio` are written by the stop path,
and `app` / `pastedText` / `e2eLatency` by the final update. Lifecycle:

1. **Start.** Right after the `AudioStart` IPC to the hub renderer, *before* the mic is open:
   `HistoryManager.updateItem(uuid, {timestamp, timezoneOffsetMinutes})`. `updateItem` is UPDATE-else-CREATE,
   so the row is born with `status = NULL`. On the host the main process's `TCCAccessRequest` lands 46 ms
   before the row timestamp, and the AudioService helper's power assertion ~400 ms after.
2. **Stop.** One of three writes, via `saveAudio(uuid, wav, status, duration, speech)`:
   - dismissed: `status='dismissed'`, **except when the audio is < 16 000 bytes (≈ 0.5 s)**: then nothing
     is written and the row stays NULL;
   - zero packets: `no_audio`;
   - otherwise `processing`, together with the audio blob and `duration`
     (`"Transitioning Stopping → Processing"`).
3. **Transcription.** gRPC, then the HTTP fallback, then `openai_fallback`. The result is abandoned with
   `"Skipping finalization — dictation was superseded while transcribing"` when the live uuid changed, the
   dictation timed out, or **a dismiss arrived during processing**. The row then stays `processing` for ever.
   On quit/crash mid-dictation, `saveInProgressDictationAudioForTeardown` also writes `processing`.
4. **Paste, then final row.** `PasteText` goes to the helper, **then** `updateItem` writes the final
   `status` / `asrText` / `formattedText` / `pastedText` / `app` / `e2eLatency`.
   - Final statuses: `formatted`, `raw_transcript`, `empty`, `error`, `fallback`, `verification_failed`,
     `timeout`, `extension_*`.
   - `raw_transcript` = the formatter did not finish, or the OpenAI fallback answered. It is in Wispr's own
     *pasteable* set `[Formatted, RawTranscript, VerificationFailed, ExtensionPaste, Fallback]` and its *ok*
     set `{RawTranscript, Formatted, Empty, Fallback}`. With no text it raises Wispr's `RawTranscript` alert.
     **It is terminal**, and `WisprState.intermediateStatuses` lists it as progress
     (`rawTextSettled` papers over this).

Measured on the copy (17 893 rows; `raw_transcript`-empty e2e p50 301 ms / p99 1.6 s over 30 days,
i.e. it lands fast):

| status | rows (all / 30 d) | `duration` set | next row starts < 3 s later | reading |
|---|---|---|---|---|
| NULL | 814 / 101 | **0** | 198 (24 %) | the stop path never ran: a sub-0.5 s dismiss, a start superseded before stop, a kill. 1–6 %/month before the relay (Jan–Jul), 0.9 % in Aug |
| `processing` | 31 / 17 | 31 | 0 (p50 15 s) | superseded or dismissed mid-transcription, or quit; 17 of 31 are Sept (relay tests) |
| `raw_transcript` | 1140 / 425 | 1140 | 28 | 688 with no text (final empty); 355 of those in the last 30 d, mostly 3–10 s clips (rig audio) |

"How long rows stay `processing`" cannot be measured from the DB: there is no finalize timestamp.
The proxy is Wispr's `e2eLatency`: `formatted` p50 0.84 s, p90 2.7 s, p99 4.4 s (30 d), max 36 s.
A `processing` row older than ~40 s is dead by construction.
`PRAGMA data_version` works, but only on the relay's own open handle, and it says only that *someone*
committed. It is a cheap gate before the query, not an event.

## Item 5: pasteboard and insertion

- **Insertion is ⌘V with delayed rendering.** The Swift helper (`DelayedClipboardProvider`, an
  `NSPasteboardItemDataProvider`) saves the current pasteboard types, then declares an item. The data is
  produced only when an app asks for it. It then posts ⌘V (`Detected V key code`, IOHIDPostEvent) and
  restores the old clipboard 500 ms later.
- **Wispr treats "data requested" as "paste succeeded".** If nobody asks within its timeout, it logs
  `failed paste likely` (feature flag `failed-paste-notification` is on). So every ⌘V the relay swallows
  *without reading the pasteboard* is a failed paste in Wispr's own books.
- **Types.** Only `public.utf8-plain-text` (the unified log shows it requested, then `NSStringPboardType`).
  There is **no Wispr marker UTI**: `org.nspasteboard.ConcealedType` appears only in its ConsentChat path.
  Today's clipboard holds one plain item.
- **Unified-log evidence of a paste.** At 20:00:51.625 the helper (pid 5959) logged
  `data requested for type public.utf8-plain-text`, 953 ms after the 66.9 s dictation's stop (the row's
  `e2eLatency` is 953 ms). The relay logged `⌘V … passed` in the same second.
- **No AXInsertText on the dictation path.** `AXValue` set is used only for ConsentChat (`direct AXValue
  set did not stick, falling back to clipboard paste`).
- **Terminals.** A `shift-insert` flag exists (on) next to Windows-only flags; unverified whether it changes
  the Terminal paste key on macOS. That is the only candidate left for the 09-12 "no ⌘V" insertions.
- **⌘V vs the row.** From `relay.log`: 1286 pairs of *⌘V dropped* then *row formatted* (09-22 → 09-27).
  The row was seen p10 25 / p50 74 / p90 135 / max 1035 ms after the ⌘V. The row lags the paste by less
  than one poll tick, so #3 buys ownership and robustness more than speed.

## Item 6: finding A (the relay's recording silent ~5 s after a Wispr launch)

What Wispr does to audio at launch:
- The hub renderer's `MediaManager.initialize()` runs once the window loads, seconds after the process
  starts. It calls `enumerateDevices`, installs `ondevicechange`, and builds
  `new AudioContext({sampleRate: 16000, latencyHint: "interactive"})` with a recorder worklet connected to
  `destination`.
- That **opens a running output stream on the default output device** from the Chromium AudioService
  process. Chromium sizes the IO buffer small for "interactive".
- Per dictation it calls `getUserMedia({deviceId: exact, sampleRate: 16000, echoCancellation: false,
  noiseSuppression: false, autoGainControl: false})`. There is no voice-processing IO for dictation
  (AEC `"all"` is used only for the Notetaker meeting mic).
- There is no aggregate device and no *setter* for `NominalSampleRate`: the helper only *reads* the output
  rate to detect Bluetooth codec changes.

Readings, most to least likely:
- **A1: the relay's `AVAudioEngine` is stopped by a device reconfiguration.** In the guest, BlackHole 2ch
  is both the clip's output and the relay's input. A new output client on the same device with a different
  IO buffer size reconfigures the device, AVAudioEngine stops and posts
  `AVAudioEngineConfigurationChange`, and no more buffers arrive → `0.0 s voiced`.
  - The `tart exec` probe used a stream opened *before* the relaunch, which is consistent if that tool
    survives reconfiguration.
  - TX9's sentences 1 s after a relaunch (2.7 s voiced) came before the hub's `initialize()` had run.
  - The uncommitted `MicRecorder.restartTap` (another session) targets exactly this; its log line
    `🔁 mic: … AVAudioEngineConfigurationChange` at a relaunch confirms A1.
- **A2: Wispr's Volume Manager zeroes the default output's volume at dictation start.** It does so when
  `shouldMuteAudio` is on and "audio is playing" (`isAudioPlaying source: deviceScan`, i.e. any device
  running; the relay's own capture counts). If the guest's default output is BlackHole, the loopback turns
  silent while buffers keep flowing. The stall watchdog cannot see that.
  - `shouldMuteAudio` defaults to **false on macOS** (`shouldMuteAudio: isWindows`); it is false on the host.
  - A restore owed across a Wispr kill is lost (`Dropping owed volume restore`).
  - Check in the guest: `prefs.user.shouldMuteAudio` in `config.json`, then the output volume before/after
    a chord. A WAV of exact zeros with no `🔁` line is A2.
- Wispr itself logs `Received first real audio packet {warmupChunks}` and `Audio recovered after sustained
  silence`: a cold graph is deaf to *Wispr* for a while too (W11), which is why its rows are NULL.

## Recommended change to `WisprFlowSource`

1. **Correct the vocabulary** (`WisprState.swift:128`): `intermediateStatuses = ["", "recording",
   "processing"]`, and add `fallback`, `verification_failed`, `timeout` to `terminalStatuses`.
   `raw_transcript` with no text ends the sentence as a Wispr failure, so Q14 stands in at once.
2. **A dead-row verdict**, evaluated in `pollHistory()` (`WisprFlowSource.swift:2171`) on every wake.
   The adopted row is **dead now** (→ `endWithRecording(…)`, Q14/Recover) when any of these holds:
   - status is `""`/`processing` **and** a row with a larger rowid exists (Wispr will never finalize a
     superseded dictation);
   - the Wispr pid differs from the one at adoption;
   - the relay itself sent the dismiss and the row is still `processing` 1 s later;
   - status is `""` and the mic has been closed > 3 s with `duration` still NULL (the stop path did not
     run).

   This bounds Q24's "wait without cap" to rows that can still finish. It also ends TW22/TW4-style waits
   without the 30 s cap.
3. **Wake on commits, not a timer.** Replace `historyPoll` (`Timer(timeInterval: historyTick = 0.15)`,
   line 2006) with a `WisprHistoryWatch`:
   - `open(".../flow.sqlite-wal", O_EVTONLY)` →
     `DispatchSource.makeFileSystemObjectSource(eventMask: [.write, .extend, .delete, .rename], queue: .main)`
     → `pollHistory()`;
   - re-arm on `.delete/.rename` (WAL recreated after a checkpoint on quit);
   - before querying, compare `PRAGMA data_version` on `WisprFlowDB`'s handle;
   - keep a 1 s safety tick.

   The same watch serves `pollRetiredDiscard` and `pollDiscardClose`.
4. **At the swallowed ⌘V** (the drop in `HotkeyTap` / the Q19 claim at line ~2495):
   - take `WisprHistory.newest()` **at that instant**: the pasted dictation's row already exists (it is
     created at start) but still says `processing`;
   - a rowid newer than the relay's adopted row is his, and should be pasted at the caret, not dropped;
     that is finding B's fix, keyed by rowid instead of the 10 s tail;
   - then read `pasteboardString()` once: it hands the relay the text ~74 ms before the row, and it closes
     Wispr's delayed-render timer so Wispr stops counting relay sentences as failed pastes.
5. **Later, after a VM measurement:**
   - post `wispr-flow://start-hands-free` / `stop-hands-free` through `NSWorkspace.open(_:configuration:)`
     with `activates = false`, instead of fn⌃Space;
   - Wispr acts on start only when `Idle`/`Dismissed` and on stop only when locked and active, so a late or
     duplicate command is ignored (it logs `…Ignoring.`) instead of toggling a ghost microphone on (W6);
   - in the guest, `switch-mic?mic_name=BlackHole%202ch` pins Wispr's input without the GUI.

   Do **not** try the deep links on the host: they start his real dictation.

Evidence (scratchpad, not committed): `asar/.webpack/main/index.js` (stop path ≈ 4 073 400, start write ≈ 4 171 574, deep links ≈ 8 871 021), `renderer/hub/index.js` (`MediaManager`), helper `strings`.
