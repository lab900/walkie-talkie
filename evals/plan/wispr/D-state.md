# D-state — the relay's own state machine with Engine = Wispr Flow

Adversarial, read-only review (2026-09-28, Opus). Dimension: **the relay's state machine when
`source === wisprSource`** — every gesture in every relay state, the Q12 queue, engine switches,
Wispr quitting, microphone ownership, and what silently degrades. Nothing was run.

Line numbers are the working tree at 2026-09-28 07:27. `AppDelegate.swift` and `HotkeyTap.swift`
had uncommitted edits from another session landing *during* the read (the tap rebuild; AppDelegate
shifted ~+97 lines after ~L1700), so every reference also names its function. Abbreviations:
**AD** `AppDelegate.swift`, **WFS** `WisprFlowSource.swift`, **HT** `HotkeyTap.swift`, **DS**
`DictationSource.swift`, **RW** `RelayWindow.swift`, **SI** `StatusItem.swift`, **MR** `MicRecorder.swift`.

Verdict tags: **CBR** = confirmed by reading (the code path is unambiguous); **PLAUSIBLE** = the
mechanism is in the code, but the trigger depends on Wispr's behaviour, timing or config that
reading cannot settle.

---

## 0. Ten facts that shape every cell

These are what make Wispr different from ElevenLabs/local. Every matrix cell below derives from one.

| # | fact | ref |
|---|---|---|
| F1 | **The relay opens the sentence at the chord, not at Wispr's microphone.** `start()` → `gestureSeen(confident: true, relay: true)` → `isRecording = true; didBegin?()` synchronously. `listening` goes up before Wispr has heard anything; a cold Wispr opens its microphone 5–6 s later (measured 2026-09-12, WFS `speculativeGrace` doc). `speculative` stays true inside the source until the row/poll/edge confirms it. | WFS `start` L734, `gestureSeen` L1276–1400 (L1345) |
| F2 | **Start and stop are the same toggle chord** (`fn ⌃ Space`, `wrapMode` is `.off` under the firewall). The relay never learns Wispr's own on/off state before posting it; `stop()` closes `listening` at once (`closeListening`) and trusts the chord. | WFS `stop` L1052–1105 |
| F3 | **Wispr does not queue** (`queuesSentences` defaults to false, DS L410). Every relay start while its words are in flight goes through `queueRefusal()` → `"Wispr Flow takes one sentence at a time"`. | AD `queueRefusal` ~L9864, `startBlocker` ~L4189 |
| F4 | **Wispr's answers bypass the queue.** `wireDictationSource` installs the queue-aware `source.didTranscribe` (→ `runAnswer`), then overwrites it for `wisprSource` with a bare `deliver(result)` / `dictationEnded(end)`. With Engine = Wispr those are the same object, so `runAnswer`'s order and "one panel at a time" rules never run. | AD `wireDictationSource` ~L2907–2994 (generic ~L2913, override ~L2992) |
| F5 | **The relay records its own WAV beside Wispr on the relay's device**, which is not necessarily Wispr's. `startMeter` → `MicRecorder.start(to: wispr-<epoch>.wav)` → `InputDevice.resolve()` (xlr ▸ rx ▸ stage ▸ bose ▸ mac, or the `/test/mic` override). Wispr hears whatever `overrideAudioDeviceId` names; on 2026-09-27 its row said *Built-in mic* while the relay recorded the XLR (journal, *Morning of 2026-09-27*). | WFS `startMeter` L1722, MR `start` ~L488–625 |
| F6 | **That WAV only leaves the source on success.** `recording` is handed over only in `deliver` (WFS L2754); on every other end (`.silent`, `.cancelled`) it is either deleted (`stopMeter(keep: false)` when cancelling) or left in `recording` and orphaned by the next `startMeter` (`self.recording = nil`, L1741, no `removeItem`). `recordsOwnAudio` is false (DS L398) so there is no local fallback and nothing for Recover. | WFS L1463, L1741, L1765, L2754 |
| F7 | **No word timings, no hops.** `DictationResult` from Wispr carries `words: nil`, `voiceHops: nil`, `language: nil`; `audioOffset` is nil (DS L394). `acceptsAudioMarkers` is true (WFS L322) but spoken markers are gated off by `ShotMarker.isEnabled`. | WFS L2757–2774, AD `reserveMarkerLocked` |
| F8 | **Q9 standalone is ON on the host since 2026-09-27** (`WT_WISPR_STANDALONE=1` in `elevenlabs.env`). Right ⌘⌥ then goes to `onCleanHold` *whatever the Engine* (HT L2944), and Wispr's own sentences (right ⌘⇧, its own chord) are invisible to `wisprSource` (`gestureSeen`/`edge` return early). | HT L2944, WFS L1286–1303, L1611–1617 |
| F9 | **"Relay-owned" is a time window, not a sentence.** From the relay's Wispr gesture to its machine's `idle` + 10 s (ceiling 11 min), *every* Wispr ⌘V is dropped by the firewall, including one from a standalone sentence of his own. | HT `setWisprRelayOwned` L4464–4476, ⌘V branch L3077–3100 |
| F10 | **The Engine menu hides the Wispr row unless Wispr is the engine**; the switch in is HTTP / `WT_SOURCE` / the persisted default only, and one menu pick away is one-way. | SI L1474 |

---

## 1. Action × state matrix, Engine = Wispr

States (columns). "Relay-started" = 🔼, 🔼→, ⌘⌃D, ◀️+🔼, right ⌘⌥ (standalone), `/test/wispr-handsfree`.

| id | state | how you know (`GET /test/state`) |
|---|---|---|
| **I** | idle, Wispr running | `listening:false settling:false capturing:false wispr.state:"idle"` |
| **W** | idle, Wispr **not** running | `/engine.ready:false` |
| **O** | opening — relay `listening`, Wispr's mic not yet open (warm 0.3–0.7 s, **cold 5–6 s**) | `listening:true isRecording:true speculative` (source-side), `wispr.state:"warming"`, `historyRow:null` |
| **L** | listening, relay-started (prompt / bound / spawn) | `listening:true relayStarted:true` |
| **C** | listening, clean (🔽 raw chord; right ⌘⌥ via `onCleanHold`) | `listening:true`, clean flags; 🔽: `relayStarted:false` |
| **S** | settle — mic closed, capture open, row intermediate (Wispr p50 2.2 s, p99 7.1 s, max 13.7 s) | `settling:true capturing:true phase:"transcribing"` |
| **X** | cancelled in flight — capture standing with `discardOnArrival` (≤ `captureTimeout` 30 s / retired swallow 5 s) | `capturing:true settling:false wispr.state:"idle"` |
| **P** | prompt panel held / paused / editing | `prompt.held:true` |
| **H** | held for a bind (5 min) | `awaitingBind` non-empty |
| **N** | spawn pending / folder menu open | `spawnPending:true` |
| **F** | a standalone Wispr sentence of **his** running (right ⌘⇧) — Q9 | relay idle, Wispr's own row open; `wisprHearing:false` (ignored) |

Cell legend: `=` same as ElevenLabs · **≠** differs from ElevenLabs · **?** undefined / not decided anywhere
· (CBR)/(PL) as above · finding ids point to §2.

| gesture ↓ / state → | I | W | O | L | C | S | X | P | H | N | F |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **🔼 F7** click (`onPasteToggle`) | caret prompt; **≠ `listening` before Wispr's mic (F1)** W-D2 | **≠** flash *Wispr Flow is not running*; `pasteMode`/`caretPrompt` left set (CBR) W-D10 | stop = toggle posted before Wispr's mic is up **? ghost dictation** (PL) W-D6 | stop (toggle) = | stop = | **≠ log-only refusal**, EL queues (CBR) W-D9 | start allowed, old capture retired = | **≠ new sentence force-sends the held/paused/edited panel** (CBR) W-D8 | = | = (resets spawn) | **≠ not refused; chord posted into his running Wispr sentence** (CBR skip / PL outcome) W-D5 |
| **🔼→ F10 / ⌘⌃D** (`toggleDictation`) | bound sentence; ≠ as I above | **≠** as W above | stop / aim at bound; **?** as O above | stop / aim = | stop (aim if bound) = | **≠ log-only refusal** (CBR) W-D9 | = | **≠** as P above W-D8 | = | = | **≠** as F above W-D5 |
| **🔼← F11 / 🔽← F3** cancel | nothing = | nothing = | **≠ ⌃Esc before Wispr's mic opened** — Wispr may still open and record (PL) W-D6 | **≠ ⌃Esc; `.cancelled(audio:nil)`; the relay's WAV is deleted; log says "nothing had been recorded yet"; Recover empty** (CBR) W-D3 | ≠ same as L W-D3 | **≠ swallow armed, `.cancelled(nil)`; WAV orphaned, Recover empty** (CBR) W-D3 | nothing (guard) = | cancels the panel (Q6) = | = | cancel + clearSpawn = | nothing; Wispr keeps it (Q9, by design) = |
| **🔼↑ F8** spawn | spawn + folder menu, then start = | **≠ folder menu opens, `spawnPending` stays true, no dictation** (CBR) W-D10 | convert = | convert = | ignored (caret) = | silent = | = | new spawn **≠** force-sends panel W-D8 | = | = | **≠** as F above |
| **🔼↓ F9** kamikaze | = | = | toggles = | toggles = | ignored (clean) = | toggles = | = | marks panel (Q6) = | = | = | = |
| **🔽 F6** (Engine = Wispr → the tap posts Wispr's raw chord, not `onCleanToggle`) | **≠ clean sentence via `noteRawChord` — bypasses `startDictation`/`startBlocker`** (CBR) | **≠ `fn⌃Space` posted with no Wispr → ⌃Space reaches the front app (input-source switch, TG42)** (PL) W-D12 | shutter (ownDictation) = | shutter = | stop (raw chord) = | shutter / "finish the sentence" banner; **≠** EL: `onCleanToggle` queues | **? raw chord → `gestureSeen`; `retireDiscardedCapture`** = | **≠** new clean sentence, force-send on landing W-D8 | = | = | **≠ `backStopsWispr` → posts the toggle into HIS sentence, then the relay adopts a clean one** (PL) W-D5 |
| **🔽→ F5** | Return = | Return = | Return while Wispr warms (known, §2.6) | live Return (known) | stop + Return (TG7: correct on Wispr) = | Return before the words (known) | Return = | sends the panel (known) | = | = | Return into his dictation target **?** |
| **🔽↑ F4 / wheel crop** | flash = | = | film/crop = | = | refused (clean) = | stop only = | = | = | = | = | = |
| **🔽↓ F12** unbind | = | = | → held at close = | = | nothing = | latched (Q2) = | = | = | = | = | = |
| **⌘⌃B / ◀️+🔼** | bind; ◀️+🔼 then starts (≠ as I) | bind ok, dictation flash **≠** | redirect (deliberate) = | redirect = | chip lie (caret forced) — known | latched (Q2) = | = | = | releases = | = | = |
| **right ⌘⌥ held** (standalone ON → `onCleanHold`) | **≠ start posts `fn⌃Space`; its own trailing `flagsChanged` reads as the pair's release ≈0.25 s later → quiet cancel** (CBR) W-D1 | **≠** flash, nothing else | n/a | left alone = | n/a | **≠ log-only refusal** (EL queues) W-D9 | = | **≠** force-send W-D8 | = | = | pair is Walkie's (Q9) = |
| **right ⌘⌥ held** (standalone OFF) | **≠ tap → Wispr PTT branch, but Wispr's `ptt` is `54+60` since 09-27 → no row → 12 s ring, then "ignored"** (CBR config drift) W-D1 | — | — | — | — | — | — | — | — | — | — |
| **⌘⇧P** | = | = | = | = | = | = | = | known R17 | = | = | = |
| **`POST /engine` wispr → eleven** | ok; **≠ the menu then has no Wispr row (one-way)** (CBR) W-D12 | ok | refused = | refused = | refused = | refused = | **allowed while a discarding capture stands** — harmless (wisprSource stays wired) = | allowed = | allowed = | allowed (no sentence yet) = | allowed = |
| **`POST /engine` eleven → wispr** | ok | ok, pick flashes nothing about readiness **≠** (no `keyless` row for Wispr, AD `setEngine` ~L489) | — | refused = | refused = | refused = | = | = | = | = | = |
| **Wispr quits** | every gesture: flash = | — | **≠ `abandonForDeadWispr` ≤ 300 ms: "the sentence is lost" while the relay's WAV exists; pictures flushed alone** (CBR) W-D3 | ≠ same | ≠ same | ≠ same | capture closed = | unaffected = | unaffected = | ≠ spawn cleared, pictures flushed | his sentence gone (Wispr's) |

**Queue column (Q12) with Wispr:** there is none. `sentences` has at most one live entry with
`take: null` (AD `dictationBegan`: `take: source.queuesSentences && … ? source.take : nil`). Two
Wispr sentences in flight happen only through paths the relay does not gate (his chord pre-Q9, a
mic edge, 🔽 after the settle ended while the capture stands) — see W-D7.

---

## 2. Findings, ranked by damage

Each: what · why (refs) · verdict · **VM test** (Tart guest, real Wispr pinned to BlackHole 2ch,
`--no-audio`, relay recorder on `POST /test/mic {"device":"BlackHole"}` so both hear one stream,
corpus WAVs played into BlackHole with `sounddevice`) · **desk test with fakes** (host, no Wispr
audio; the gaps it needs are in §2.99).

### W-D1 — Right ⌘⌥ held on Engine = Wispr cancels itself (standalone ON) or rings for nothing (standalone OFF)

- **What.** Under Q9 the pair is `onCleanHold` for every Engine (HT L2944). On Wispr, the press
  runs `startDictation(paste:true, clean:true)` → `wisprSource.start()` → `HotkeyTap.postWisprHandsFree()`.
  That post waits ≤ 45 ms + 200 ms for a bare wire (HT L4256–4263) — which never comes, because
  he is holding right ⌘⌥ — then posts the chord and ends with `modifier(VK_FN, leaving: [])`, a
  `flagsChanged` whose flags carry no right-⌘/⌥ device bits. The PTT branch has **no stamp check**
  (HT L2927–2958; the test plan's §2.5 row already says the app's own `flagsChanged` counts as a
  release) → `ptt` false → `onCleanHold(.release)` ≈ 0.25 s after the press → `held < cleanHoldFloor`
  (0.35 s, AD) → `cancelDictationInFlight(quiet: true)` → ⌃Esc. No flash. He talks into nothing.
  If the post lands after 0.35 s instead, the release is taken as the *end* of the sentence → a
  0.3 s sentence and a second toggle 0.1 s after the first.
- **Standalone OFF:** the pair goes to the Wispr PTT branch (`onWisprMaybeStarting(.pushToTalk)`,
  unconfident), but Wispr's own `ptt` moved to `54+60` on 2026-09-27 → no row → the ring stands
  12 s (`speculativeGrace`) → "Wispr never created a row … it ignored it".
- **Verdict:** CBR (standalone ON path, modulo the exact device bits of the posted event); CBR for
  the config drift (standalone OFF).
- **Also:** the posted chord goes out with right ⌘⌥ physically down — whether Wispr matches
  `fn⌃Space` with extra modifiers in the session state is **?**.
- **VM:** Engine=wispr, standalone on, key-trace on. Hold right ⌘⌥ 3 s (CGEvent script, under
  `hands-off`), play `CLIP_EN` into BlackHole during the hold. Assert within 0.5 s of the press:
  no `🧼 … released` line before the real release; `listening:true` for ≥ 2.5 s; one Wispr row
  `formatted` containing "wonder"; `lastDelivery.to == "caret"`. Today expected: a release line
  at ~0.25 s, `🗑️ dictation cancelled via right ⌘⌥ tapped (0.2x s)`, no row text delivered.
- **Desk:** `POST /engine {"id":"wispr"}` with Wispr running; the same hold with no audio; assert
  on the log line order only (`🧼 held` → `🧼 released` gap < 0.35 s = BUG). A pure unit test is
  better: feed the PTT branch a stamped `flagsChanged` with flags `[]` while `enginePairHeld` →
  must not fire `.release` (needs gap GW6).

### W-D2 — A cold Wispr is deaf for the first seconds while the relay shows Listening and breathes

- **What.** F1: `didBegin` → `dictationBegan` at the chord: chip `Listening to … → (W)`, context
  shot, ⌘C probe, halo up. The halo breathes on `wisprSource.meter` (AD `liveMeter` L224), i.e.
  **the relay's own microphone**, which opens at the chord too (`startMeter` in `gestureSeen`). So
  he sees a live, swelling ring while Wispr's Electron is still waking (5–6 s cold, 0.3–0.7 s
  warm). Whatever he says in that window is absent from Wispr's transcript — and present in the
  relay's WAV, which is never used (F6).
- **Nothing tells him.** `speculative` is source-private; the chip has no *warming* row for this
  case (the `Opening, deaf` state of the test plan §2.2 exists for EL too, but for ~0.3 s).
- **Verdict:** CBR for the mechanism; the latency is the code's own measurement (WFS
  `speculativeGrace` doc, 2026-09-12). How often Wispr is cold on his host (hidden in Dock,
  `openAtLogin`) is PLAUSIBLE.
- **VM:** quit Wispr, `open "/Applications/Wispr Flow.app"`, wait until `/engine.ready`, then
  within 1 s: 🔼→ (bound witness tab), play a 12 s clip that starts speaking at +0.2 s, stop at +13 s.
  Assert: time from `⚡ … opening the dictation on the gesture` to `wispr history: row N is this
  dictation's` (the confirm) and from chord to `IsRunningInput` true (`wispr.lags`); the words
  of the first 3 s present in `lastDelivery`/witness text. Record `listening:true` samples where
  `wispr.state == "warming"` — each one is a moment the chip lied. Repeat warm ×5 for the baseline.
- **Desk:** `POST /test/wispr {"hotkey": true}` (the chord with no microphone) and poll
  `/test/state` at 20 Hz for 3 s: assert the chip row and `ringUp` while `wispr.state == "warming"`
  and `historyRow == null` — documents the lie without audio. `POST /test/wispr-state/simulate` for
  the machine's own transitions.

### W-D3 — Every Wispr failure throws away the one recording the relay has; Recover is always empty

- **What (F6).** Paths and what happens to the relay's WAV (`wispr-<epoch>.wav` in
  `Outbox.shotsDir`):

  | end | source call | WAV | Recover | user sees |
  |---|---|---|---|---|
  | cancel while recording | `cancel` → `closeListening` with `cancelling` → `stopMeter(keep:false)` | **deleted** (L1463/L1766) | nothing; log *"nothing had been recorded yet"* (AD `dictationEndedForGood`) — false | 🗑️ Cancelled |
  | cancel in the settle | `cancel` capturing branch → `.cancelled(audio:nil)` (L1146) | **orphaned** in `recording` (kept at close), never staged | nothing | 🗑️ Cancelled |
  | Wispr quits / pid changes | `abandonForDeadWispr` → `.silent("Wispr Flow quit — the sentence is lost")` (L2330–2345) | orphaned | nothing | 8 s flash *the sentence is lost* — **false, the audio is on disk** |
  | 30 s, no row / no words | `captureExpired` → `.silent("No words came back")` | orphaned | nothing | flash |
  | `raw_transcript` empty 8 s | `.silent("No speech was heard")` | orphaned | nothing | flash |
  | `empty` / `no_audio` / unknown status | `.silent(…)` | orphaned | nothing | flash |
  | dismissed by hand | `.cancelled(nil)` | orphaned | nothing | — |

  `.silent` then runs `abandonDictation("the source returned nothing")`, which releases the
  sentence's pictures to the bound terminal as a bare screenshot message (the flush the cancel path
  avoids on purpose) — **the agent receives pictures of a sentence whose words were thrown away.**
  Orphaned WAVs are dropped by the next `startMeter` (`self.recording = nil`, no `removeItem`) and
  stay in Caches; the second-resolution name `wispr-<epoch>.wav` can also collide on a
  cancel-and-restart within one second (the kept URL then points at the next take's audio).
- **Contrast.** ElevenLabs on the same failures: fallback to the local model on the same WAV, or
  `.failed(audio:)` → *Recover* (dictation-source.md, *A cloud engine that fails keeps the sentence*).
  The protocol already says why Wispr is excluded — `recordsOwnAudio` false because "Wispr's audio
  never reaches this app" — but the relay *does* have a recording of the same voice (on its own
  device, F5), and today it is discarded.
- **Verdict:** CBR (every row of the table). Whether the relay's device heard the same speech is
  PLAUSIBLE per F5.
- **VM:** four sub-cases, each with a 6 s clip into BlackHole and the relay recorder on BlackHole:
  (a) 🔼← at +3 s → assert `recoverable != null` (today null) and log line not "nothing had been
  recorded"; (b) stop, 🔼← at +0.3 s after the stop; (c) stop, then `pkill -9 -f "Wispr Flow.app/Contents/MacOS/Wispr Flow"`
  at +0.2 s → assert `lastFailure`/flash and `recoverable != null`; count `wispr-*.wav` in
  `~/Library/Caches/ro.victorrentea.wispr-relay/` before/after (today +1 each); (d) same as (c) with
  one `/test/area` shot taken mid-sentence and the witness bound → assert the witness received **no**
  bare screenshot message (today it does).
- **Desk:** `/test/wispr {"hotkey":true}` (meter opens on the relay mic, no audio needed), then
  `/test/cancel` → `recoverable` null + the log line; for the quit path, gap GW2 (fake
  `wisprMainPid`) → assert the flash text and the file count.

### W-D4 — Q9 is broken inside the relay-owned window: his own Wispr sentence is dropped or re-routed by the relay

- **What (F8, F9).** A relay Wispr gesture sets `setWisprRelayOwned(true)` (WFS L1303); it is
  released only when the machine goes `idle`, plus a 10 s tail (HT L4462), ceiling 11 min. During
  that window *every* Wispr ⌘V is dropped (HT L3084–3100 — the standalone pass-through requires
  `!relayOwned`), including the paste of a sentence he started with right ⌘⇧ (Q9: *"Wispr's alone
  … even if Walkie is dead"*). The dropped key then reaches `injected(from:)`:
  - relay capture still open (his sentence finished before the relay's) → firewall branch →
    *"the History row delivers"* → but the relay's capture is keyed to **its own** row → **his
    sentence is lost**, silently;
  - relay capture already closed (the 10 s tail) → `rescueFromRow` → the newest terminal row
    that is not `lastRow` → **his** row → `didTranscribe` with no sentence open → AD `deliver`
    with whatever flags stand: `latch` nil, `pasteMode` false → `send` → **the bound agent's
    terminal** (or held for a bind) — the opposite of Q9's "pastes where the caret is".
- **Verdict:** CBR for the drop and both branches; the timing overlap is realistic (dictate to the
  agent, then immediately dictate into a document with right ⌘⇧).
- **VM:** Engine=wispr, standalone on, witness bound, TextEdit in front. (a) 🔼→, clip A (6 s),
  stop; at +1 s after the stop hold right ⌘⇧ and play clip B (3 s). Assert: B's words in TextEdit,
  not in the witness, not in `outbox.jsonl`; A in the witness. (b) the same with B started at
  +5 s after A's delivery (inside the 10 s tail) → assert B not rescued (`🛡️ rescue:` absent) and
  pasted by Wispr (`🛡️ ⌘V from Wispr Flow passed — its own sentence`).
- **Desk:** needs GW1 (fake History rows) + GW3 (a stamped fake "Wispr" ⌘V post the tap attributes
  to Wispr): open a relay sentence with `/test/wispr-handsfree`, fake its row to `formatted`, then
  post the fake ⌘V within 10 s with a second fake row → assert `lastDelivery` unchanged.

### W-D5 — The relay starts over his running Wispr sentence (the exclusivity check is skipped on Engine = Wispr)

- **What.** `startDictation` refuses when Wispr's microphone is open — but only `if source !==
  wisprSource` (AD ~L4098; the comment argues Wispr's own `isRecording` is the better answer).
  Under Q9 his standalone sentence never sets `isRecording` (`gestureSeen` returns early), so on
  Engine = Wispr nothing sees it. 🔼 / 🔼→ / ⌘⌃D / right ⌘⌥ then post `fn⌃Space` into a Wispr that is
  mid-PTT (right ⌘⇧). What Wispr does with a hands-free toggle during PTT is **?**; the relay then
  adopts the newest row only if `startedAt >= openedAt − 2` (WFS `pollHistory`), so a PTT started
  > 2 s earlier is refused and the relay waits for a row that may never come (12 s ring, "ignored").
  Same for 🔽 (HT `backStopsWispr` → `wisprMicIsOpen` → posts the toggle into his sentence).
- **Verdict:** CBR (the skip, and `isRecording` false under standalone); outcome PLAUSIBLE.
- **VM:** hold right ⌘⇧ (his Wispr PTT), play clip B; at +1.5 s press ⌘⌃D (bound). Expect (per
  2026-09-18 *"exclusiv, ba unu, ba altu"*): `⚠️ Wispr Flow is listening — one engine at a time`,
  no chord posted (key trace), B pasted by Wispr at the caret. Today: record what Wispr does and
  where B lands.
- **Desk:** a standalone-row fake (GW1) + `wisprMic` forced open (GW4) → ⌘⌃D → assert the refusal
  flash; today `listening:true`.

### W-D6 — Toggle desync: a stop or cancel before Wispr's microphone is up leaves a ghost Wispr dictation

- **What.** F2: the relay's stop/cancel is a chord Wispr receives whenever it gets to it. In state
  **O** (cold, 5–6 s) a 🔼 click or 🔼← posts the second toggle / ⌃Esc before Wispr has opened
  anything; the relay `closeListening`s at once. If Wispr processes *open* after *close* (or ignores
  ⌃Esc before it records), it records with nobody listening. Under standalone its later mic edge
  is ignored (`edge` returns early), its ⌘V falls in the relay-owned window → dropped → rescued and
  delivered (W-D4 path) — **a sentence he cancelled arrives in the terminal**; outside the window
  Wispr pastes it at the caret. The same shape: Wispr ends a hands-free dictation on its own
  (its window, a device change) before the 100 ms poll had a credential (`state.pollMs == nil`) →
  the relay's next stop posts a toggle that **starts** one.
- **Also:** `postWisprCancel`/`postWisprHandsFree` post at the HID tap (HT L3843, L4280): with no
  Wispr shortcut registered (hung, just quit) the front app receives ⌃Esc / ⌃Space.
- **Verdict:** PLAUSIBLE (depends on Wispr's handling of queued chords while warming).
- **VM:** quit+relaunch Wispr (cold); 🔼 click, then 🔼 click again at +1.0 s (or 🔼← at +1.0 s);
  play a clip from +1.5 s for 5 s. Assert over 40 s: Wispr `History` has **no** new row with
  words, `wisprHearing` never true after the stop, `lastDelivery` unchanged, witness empty.
- **Desk:** not reproducible without Wispr; the fake-row gap GW1 can assert the relay side
  (a row appearing 5 s after a cancel with `startedAt` after the cancel must not be delivered).

### W-D7 — Two Wispr sentences overlap on ungated paths; the first's words take the second's envelope, the second can be lost

- **What.** The relay's own gestures refuse in the settle (F3), but `dictationBegan` is also
  reached by `wisprSource.didBegin` from paths nothing gates: his own chord with standalone OFF,
  a CoreAudio open edge, the 🔽 raw chord once `settling` is down while the capture still stands.
  Then (AD `dictationBegan`) `endSettling("a new dictation started")` + `abandonDictation` — the
  first sentence's pictures go out alone — and the fields (latch, flags, pictures) are the new
  sentence's; the first sentence's row lands → `deliver` runs on them. In the source, the new
  gesture keeps the old capture (`retireCaptureIfSettled`, row not terminal) and `beginCapture`
  returns early (`guard !capturing`), so the new sentence has **no capture** until the old ends;
  the late re-arm takes `priorRow = newest` — if the new sentence's row is already terminal by
  then (short sentence), `isNew` is false, it is never adopted, and after 30 s → *No words came
  back*; its ⌘V was dropped by the firewall meanwhile. **Lost.**
- **Verdict:** CBR (relay side and source side); trigger PLAUSIBLE, mostly closed by Q9 standalone
  (keep it as the regression guard for the day standalone is off or the adoption path returns).
- **VM (standalone OFF run):** 🔼→ bound + clip A 8 s, stop; at +0.3 s press Wispr's own chord and
  play a 1.5 s clip B, stop at +2 s. Assert: A → witness with A's envelope (its `/test/area` shot),
  B delivered or held (never lost), no bare screenshot message.
- **Desk:** GW1 fake rows: row A `processing`, open a second via `/test/wispr {"on":true}` (edge),
  make row B `formatted` before A → assert both `lastDelivery` entries, in order, with their own
  envelopes.

### W-D8 — The next Wispr sentence force-sends the held (or paused, or edited) prompt panel

- **What.** F4: Wispr answers skip `runAnswer`, whose `panel` rule (`source.queuesSentences && (held
  != nil || panelsComing > 0)`, AD ~L9945) is what makes an ElevenLabs answer wait for the panel on
  screen (Q12: *"with Autosend off the panels one at a time, in order"*). A Wispr start while a
  panel is held is not refused (`startBlocker` has nothing), and when its words land
  `showSentPrompt` calls `resolvePrompt(send: true)` (RW L4469) — the first panel is **sent**,
  including one he paused to read or is editing (the edit's state at that instant). With Autosend
  off that removes the only chance to ✕ it.
- **Verdict:** CBR for the bypass and the force-send; paused/editing outcome PLAUSIBLE (read
  `resolvePrompt`'s editing branch before writing the assertion).
- **VM:** autosend off (`/test/autosend {"on":false}`), 🔼→ + clip A → panel held; `/test/prompt
  {"do":"edit"}` (field open); 🔼→ + clip B, stop. Assert: A still `prompt.held` (or at least not in
  the witness) until `/test/prompt {"do":"send"}`; then A, then B, in order.
- **Desk:** `/test/dictation {"text":"A"}` (panel held) then `/test/wispr-handsfree` + GW1 row
  `formatted` "B" → same assertions; this is the cheapest case in the file.

### W-D9 — On Wispr every start in the settle is refused in silence

- **What.** 🔼 (AD `onPasteToggle` ~L2177: `Log.info("🔼 forward click while the words are still in
  flight — nothing to start …")`), 🔼→/⌘⌃D (`startDictation` → `🚫 start refused`), right ⌘⌥
  (`onCleanHold` press: `left alone`) all refuse during Wispr's 0.5–13.7 s formatting with **no
  flash** — the flash exists only for `two sentences`. On ElevenLabs the same press opens a queued
  sentence. TR18's rule (*a refusal says so*) is met in the log and not on the chip.
- **Verdict:** CBR.
- **VM:** 🔼→ + clip 10 s, stop; ⌘⌃D at +0.4 s. Assert a flash/chip row naming the wait
  (`chip` contains "in flight"/"one sentence at a time") and no second `⚡ … opening`.
- **Desk:** `/test/wispr-handsfree` + GW1 row stuck at `processing` → `/test/gesture forward-right`
  → assert the chip.

### W-D10 — "Wispr Flow is not running" leaves the gesture's flags and the spawn menu standing

- **What.** `startDictation` sets `spawnPending`, `spawnFolder`, `pasteMode`, `caretPrompt` and calls
  `offerSpawnFolders()` **before** `source.start()`; on the refusal only `cleanSentence` /
  `ownCleanSentence` are reset (AD ~L4144–4151). With Wispr down, 🔼↑ opens the folder menu for a
  sentence that never starts; a folder pick then acts on `spawnFolder`/`spawnPending`. The stale
  `spawnPending` also makes `noteHandStartedAtCaret` skip and a later latch say `new session`
  (e.g. for a rescued row, W-D4). Also `isReady` checks any process whose bundle id starts with
  `com.electron.wispr-flow` (WFS L315, L623) while death is judged on the anchored main executable
  (L2307–2313): with only a helper alive, `start()` is accepted and `abandonForDeadWispr` fires
  ~300 ms later with *"Wispr Flow quit"* — for a Wispr that was never running.
- **Verdict:** CBR (flags, menu, the two different readiness tests); consequences PLAUSIBLE.
- **VM:** quit Wispr; 🔼↑ → assert `spawnPending:false` and no folder menu within 0.5 s (today
  true + menu); ⌘⌃D → flash only. Then kill Wispr's main process but leave a helper (if one
  survives) → ⌘⌃D → assert the *not running* flash, not *the sentence is lost*.
- **Desk:** GW2 (`isReady` false) → `/test/gesture forward-up` → `spawnPending`.

### W-D11 — The corpus pairs Wispr's words with a different microphone's audio, forever

- **What (F5).** Corpus row = the relay meter's WAV (its device) + Wispr's **formatted** text
  (Wispr's device, formatting pass, custom dictionary), tag `wispr`. On 2026-09-27 those were
  XLR vs *Built-in mic*. In a training room the built-in mic hears participants the XLR does not —
  a pair whose text holds words the audio lacks, in a corpus that is never pruned. `micOpened` in
  `/test/state` is `MicRecorder.lastOpened`, a **static** shared by all recorders (MR L178, L623):
  under Wispr it names the meter's device, not what Wispr heard — any test asserting "the right mic"
  on Wispr from `micOpened` is testing the wrong recorder. The halo swells on the same meter, so
  a relay device that is off or far away gives a flat ring while Wispr hears fine (and vice versa).
  Opening a BT headset's input for the meter while Wispr uses another mic drops the headset to HFP.
- **Verdict:** CBR (mechanism); poisoning rate PLAUSIBLE. The chip's device glyph *is* Wispr's
  (`History.micDevice`) — honest; `TO Wispr` maps to the relay's device (`glyph(wisprName:)`), which
  is true only with `WT_BRIDGE=1`.
- **VM:** Wispr on BlackHole, relay recorder left on the guest's own input (not BlackHole): one
  sentence → the corpus row's WAV is silence while its text has words. Assert a guard: a Wispr
  corpus row is written only when `History.micDevice` maps to the relay's device (or is skipped with
  a log line).
- **Desk:** `/test/mic {"device": X}` ≠ Wispr's device, a real Wispr sentence (host, Victor idle)
  → inspect the new `corpus.jsonl` row (`engine`, device) — needs G10 `harness` stamp first.

### W-D12 — Smaller: one-way Engine menu, HID-level chords, ⌃Space with no Wispr

- The Engine submenu lists Wispr only while it is the engine (SI L1474): after one menu pick away,
  the way back is `POST /engine` or `WT_SOURCE`. CBR. Either document it or keep the row.
- `setEngine` has no readiness flash for Wispr (`keyless` table covers ElevenLabs only): picking
  Wispr while it is quit says `🎙️ Wispr Flow` and the first gesture finds out. CBR.
- 🔽 with Engine = Wispr and Wispr quit posts `fn⌃Space` raw; the tap's F6 path does not ask
  `isReady` (TG42 in the test plan already asks what ⌃Space does). PLAUSIBLE.

### W-D13 — What silently degrades on Wispr (inventory)

| feature | on ElevenLabs | on Wispr | told? | ref |
|---|---|---|---|---|
| voice affect `[?]` / `[voice: hesitant]` | from `words[]` + hops | **nothing** (`words`, `voiceHops` nil; the meter's hops exist and are dropped) | no — the tag is just absent | AD `deliver` → `applyingAffect`; WFS L2757 |
| picture markers inline | `[screenshot N]` at the word (`ShotMarker.place`) | none; frames listed under the words by `mm:ss` | no | DS L394, AD `reserveMarkerLocked` |
| live caption band 💬 | `eleven-live` only | none (`streamsLive` false) | the row simply never opens | DS L396 |
| local fallback on failure | yes | **no** (W-D3) | "the sentence is lost" | AD `fallBackToLocal` guard `recordsOwnAudio` |
| Recover after cancel/failure | WAV staged 5 min | **never** (W-D3) | Recover row finds nothing | AD `keepCancelled` |
| cost counter | `elevenCost` | not counted (subscription) — fine | — | — |
| sentence queue (Q12) | 2 in flight, ordered | 1; refusals silent (W-D9); panel order not kept (W-D8) | no | F3, F4 |
| decode estimate bar | `DecodeRate` | learnt per Wispr since 09-23 — fine | — | WFS L2748 |
| `language` in the envelope | Scribe's | nil (`[Dictated in RO or EN]` generic) | — | WFS L2759 |
| `micOpened` in state | the recorder | the **meter**, not Wispr's mic (W-D11) | — | MR L623 |

Test-fidelity note (not Wispr-specific, found on the way): `POST /test/dictation/start {"clock":true}`
replaces `markerClock` with a wall-clock ruler (AD ~L2267) and nothing restores it until the next
`wireDictationSource` (engine switch or launch) — every **real** sentence after a desk run then
places markers on the wrong ruler (harmless on Wispr, wrong on ElevenLabs by the mic-open latency).
CBR.

### 2.99 Gaps a Wispr suite needs (desk variants)

| gap | route / hook | for |
|---|---|---|
| **GW1** | `POST /test/wispr-row {"status","text","micDevice","startedAt"?,"after_ms"?}` — a fake `WisprHistory` newest-row provider (process-local, `WisprHistory.testRows`) | every desk variant: drive `pollHistory` without Wispr |
| **GW2** | `POST /test/wispr-process {"main":bool,"helper":bool,"pid"?}` — overrides `isReady` and `wisprMainPid` | W-D3 (quit), W-D10 |
| **GW3** | `POST /test/wispr-paste` — a ⌘V the tap attributes to Wispr (`isWispr` test override for one pid) | W-D4 |
| **GW4** | `POST /test/wispr-mic {"open":bool}` — `wisprMic.sampleIsRunningInput` override | W-D5 |
| **GW5** | state: `wisprMeter {recording, url, device}`, `wisprOwned {since, releasedAt}`, `wisprSpeculative` | W-D2/3/4/11 assertions |
| **GW6** | `POST /test/flags {"flags":[…],"stamped":true}` — a stamped `flagsChanged` into the tap | W-D1 as a unit test |

---

## 3. `evals/plan/cases_wispr.py` — outline (not written)

**Module shape.** Same as `cases_queue.py`: `from harness import *`, `@case(id, tags, expect=…)`.
Helpers: `_engine_wispr()` (POST `/engine {"id":"wispr"}`, restore the previous id in cleanup),
`_wispr_up()` (`/engine.ready`), `_cold_wispr()` (quit via its menu / `kill -TERM` main pid, then
`open "/Applications/Wispr Flow.app"`, wait `ready`), `_row(n0)` (newest `flow.sqlite` History row
after rowid n0, read-only `mode=ro`), `_wav_count()` (Caches `wispr-*.wav`), `play_blackhole(wav)`.
**Skip rules:** SKIP unless `state.source == "Wispr Flow"` can be set and Wispr is running; SKIP the
standalone cases unless `state.wisprStandalone` matches the case; host runs only with Victor idle
(Wispr is his dictation tool — every host case posts real chords) — prefer the Tart guest
(`tools/wt-night.sh`, Wispr on BlackHole 2ch, **guest `ptt` must be `54+60`**: `docs/vm-wispr.md`
§1 still lists `54+61`, fix before the first guest run). Every case under `hands-off run` +
`caffeinate`; cleanup: `/test/cancel` if `listening||capturing`, `/test/autosend` back, `/test/mic
{"device":null}`, `/engine` back, witness unbound, and `wisprHearing:false` for 2 s.

Invariants asserted after every case (on top of the plan's two):
`capturing == false` within 35 s of the last stop · `speculative == false` · `wisprOwned` released
within 10 s of `wispr.state == "idle"` (GW5) · no new `wispr-*.wav` left in Caches (W-D3) ·
`sessionFlags == []`.

| id | tags | finding | preconditions | steps | assertions (`GET /test/state` unless noted) |
|---|---|---|---|---|---|
| TW1 | vm, gesture, audio | W-D1 | standalone on, key-trace on | hold right ⌘⌥ 3 s, clip during hold | no `🧼 … released` before the real release; `listening` true ≥ 2.5 s; `lastDelivery.to=="caret"`, `via=="wispr-history"` |
| TW2 | desk, unit | W-D1 | GW6 | `enginePairHeld`, post stamped `flagsChanged []` | no `onCleanHold(.release)` line |
| TW3 | vm, audio | W-D1 (off) | standalone off | hold right ⌘⌥ 2 s | either a Wispr row within 1 s **or** a flash that the pair is not bound; never a 12 s ring (`ringUp` false at +3 s) |
| TW4 | vm, audio, cold | W-D2 | Wispr cold | 🔼→ within 1 s of `ready`, 12 s clip | words of the first 3 s in the witness; fraction of `listening` samples with `wispr.state=="warming"` reported; chip shows a *warming* row while `historyRow==null` |
| TW5 | desk | W-D2 | Wispr running | `/test/wispr {"hotkey":true}`, 20 Hz poll 3 s | record `ringUp`/`chip` while `wispr.state=="warming"` (documents; expected-fail today) |
| TW6a–d | vm, audio | W-D3 | recorder on BlackHole | cancel mid / cancel +0.3 s after stop / kill Wispr +0.2 s after stop / same with a shot | `recoverable != null` each time; no *"nothing had been recorded"*; `_wav_count()` unchanged; (d) witness has no bare screenshot message |
| TW7 | desk | W-D3 | GW2 | `/test/wispr-handsfree`, `/test/wispr-process {"main":false}` | flash text, `recoverable`, `_wav_count()` |
| TW8a–b | vm, audio | W-D4 | standalone on, witness bound, TextEdit front | relay sentence A, then his right ⌘⇧ sentence B at +1 s / at +5 s after A lands | B in TextEdit only; outbox has only A; no `🛡️ rescue:` line |
| TW9 | vm, audio | W-D5 | standalone on | his right ⌘⇧ sentence running, ⌘⌃D at +1.5 s | flash *one engine at a time*; no chord in key trace; B at the caret |
| TW10 | vm, cold | W-D6 | Wispr cold | 🔼 click, 🔼 click at +1.0 s (and variant 🔼← at +1.0 s), clip from +1.5 s | no History row with words after the stop; `wisprHearing` false; `lastDelivery` unchanged for 40 s |
| TW11 | vm, audio | W-D7 | **standalone off** | 🔼→ A 8 s + `/test/area`, stop; his chord + B 1.5 s at +0.3 s | A with its shot in the witness; B delivered or held (`awaitingBind`), never lost; no bare screenshot message |
| TW12 | desk | W-D7 | GW1 | row A `processing`; `/test/wispr {"on":true}`; row B `formatted` before A | two deliveries, spoken order, own envelopes |
| TW13 | vm+desk | W-D8 | autosend off | panel A held (desk: `/test/dictation`), `/test/prompt {"do":"edit"}`, Wispr sentence B | `prompt.held` still A until `/test/prompt send`; outbox order A, B |
| TW14 | vm | W-D9 | — | 🔼→ + 10 s clip, stop; ⌘⌃D at +0.4 s; 🔼 at +0.6 s | chip names the wait; no second `opening the dictation` line |
| TW15 | vm+desk | W-D10 | Wispr quit (desk: GW2) | 🔼↑; ⌘⌃D | `spawnPending:false`, no folder menu; flash *not running*; next hand/rescued sentence's `lastDelivery.to` not `spawn:` |
| TW16 | vm | W-D10 | only a helper alive (if reproducible) | ⌘⌃D | flash *not running*, not *the sentence is lost* |
| TW17 | vm, audio | W-D11 | Wispr on BlackHole, relay on another input | one sentence | no corpus row, or one flagged device-mismatch; `micOpened.device` ≠ Wispr's `micDevice` recorded in the report |
| TW18 | desk | W-D12 | Engine wispr | pick `eleven` via Codex menu (S1) | Engine submenu still offers Wispr (expected-fail today) |
| TW19 | desk | engine switch | — | `/engine wispr` mid `listening` / in `settling` / in state X | 409-style flash + `source` unchanged for L/S; accepted in X with the discarding capture still swallowing (`capturing:true`) and nothing delivered in the next 30 s |
| TW20 | vm, audio | Wispr quit mid-sentence | recorder on BlackHole | 🔼→, clip, `kill -9` Wispr main at +2 s | ≤ 0.6 s: `listening:false`, `settling:false`, flash; then `open` Wispr → next 🔼→ delivers (no stale `capturing`, `wispr.state` idle) |
| TW21 | desk | markerClock leak (§W-D13 note) | Engine eleven | `/test/dictation/start {"clock":true}`, cancel, then a real sentence with a shot | `⏱️ marker cue` offset equals the recorder offset (±0.1 s), not wall clock |

Order to run: the desk ones first (TW2, TW5, TW7, TW12, TW13-desk, TW19, TW21 — need GW1–GW6),
then the guest (TW1, TW3, TW4, TW6, TW8–TW11, TW14–TW17, TW20), host only for TW18 (Codex menu).
