# C — Wispr as the engine: firewall, paste and delivery (adversarial read, 2026-09-28)

Reviewer C. Dimension: **the ⌘V Wispr posts, the swallow that drops it, and the relay's own delivery
of the same words**. Read only: nothing was run, no synthetic input was posted. Wispr's own
`flow.sqlite` was queried read-only (`mode=ro`) for **status counts only**, no text.

Labels: **CONFIRMED-BY-READING** = the code path does it, given the trigger; **PLAUSIBLE** = depends on
a timing, or on Wispr/macOS behaviour not measured here; **DATA** = seen in Wispr's DB.

Line numbers are the tree as read on 2026-09-28 morning. Another agent is editing `HotkeyTap` /
`AppDelegate` right now (tap self-heal, `POST /test/tap`, Secure-Input `blind`), so lines drift;
function names are the stable anchor.

---

## 1. One Wispr sentence, chord to delivery, with every guard

Default config: firewall **on**, `historyIsTheRoute` **on**, Q9 standalone **off**, Wispr's `ptt`
= `54+61` (right ⌘⌥), `popo` = `49+59+63` (fn ⌃ Space). Two variants are walked at once:
**(B)** Victor's own fn ⌃ Space with the relay bound to terminal 2 while app1 is in front (the
firewall's founding case), and **(C)** held right ⌘⌥ with Engine = Wispr (always a caret sentence).

```
Victor/HID      HotkeyTap (tap thread)             WisprFlowSource (main)          Wispr Flow            AppDelegate (main)             target
   |                  |                                  |                              |                       |                            |
   |-- chord -------->| G0 tapDisabled* → re-enable, pass |                              |                       |                            |
   |                  | G1 failingOpen() (MainStallGate:  |                              |                       |                            |
   |                  |    main silent ≥3 s → PASS ALL)   |                              |                       |                            |
   |                  | G2 canary stamp → swallow         |                              |                       |                            |
   |                  | G3 flagsChanged: right⌘+right⌥ bits (C) ── no stamp/pid filter ──► W-C6                  |                            |
   |                  |    backUsesOwnEngine||standalone? → onCleanHold : onWisprMaybeStarting(.pushToTalk)       |                            |
   |                  | G4 keyDown fn⌃Space, !stamp → onWisprMaybeStarting(.handsFree)   (B)                     |                            |
   |                  |---- event passes on ------------------------------------------->| starts mic            |                            |
   |                  |                                  | gestureSeen(relay:false)      | row created (357 ms,  |                            |
   |                  |                                  |  standalone&&!relay → return  |  status '')           |                            |
   |                  |                                  |  intercepting = wrapWispr     |                       |                            |
   |                  |                                  |  focusPid = front (unused: .off)                      | didMaybeBegin/didBegin:    |
   |                  |                                  |  beginCapture → armInjectionCapture(swallow)          |  noteHandStartedAtCaret    |
   |                  |                                  |  row poll 150 ms, adopt row if startedAt ≥ openedAt-2 |  (unbound → pasteMode)     |
   |-- stop --------->| (C) pair up → onWisprPushToTalkReleased / (B) 2nd fn⌃Space → closeListening            |                            |
   |                  |                                  | didStopListening ------------------------------------>| LATCH (Q2): latchedAtCaret |
   |                  |                                  |                               |                       |  = pasteMode; latch=target |
   |                  |                                  |                               | t0+~400 ms: pasteboard := W (saves V)             |
   |                  |<========= ⌘V  kc 9, flags 0x20100000, pid=Wispr ================| t0+407–506 ms        |                            |
   |                  | G5 key-redirect (Scratchpad only; Wispr pid exempt)              |                       |                            |
   |                  | G6 pid≠0 && !stamp && kc9 && ⌘ && isWispr(pid) (name now, Team ID C9VQZ78H85 async)    |                            |
   |                  |    standalone && !relayOwned && !armed → PASS (Q9)               |                       |                            |
   |                  |    else onInjectedPaste + SWALLOW keyDown AND keyUp              |                       |                            |
   |                  | G7 keyUp passed from Wispr → clearCommandAfterWisprPaste (flags [])                     |                            |
   |                  |                                  | injected(): retiredDiscardRow? / !capturing → rescueFromRow / discard / "dropped"     |
   |                  |                                  |                               | <250 ms: pasteboard := V (restore)                 |
   |                  |                                  | poll: row 'formatted' (t0+458–540 ms; ⌘V ≈30 ms earlier)                           |
   |                  |                                  |  rawTextSettled (raw_transcript + words, 0.8 s)                                    |
   |                  |                                  |  guard intercepting else .silent                                                   |
   |                  |                                  |  historyIsTheRoute → deliver(.route, e.text, focusPid:nil) -> didTranscribe -> deliver(result)
   |                  |                                  |                               |                       | transcriptDisowned? drop   |
   |                  |                                  |                               |                       | latched = latch; latch=nil |
   |                  |                                  |                               |                       | if pasteMode||clean →      |
   |                  |                                  |                               |                       |   latchedAtCaret = true    |
   |                  |                                  |                               |                       | atCaret → pasteText:       |
   |                  |                                  |                               |                       |  clear+set pasteboard (NO  |
   |                  |                                  |                               |                       |  restore), ⌘V to FRONT ---->| app in front NOW
   |                  |                                  |                               |                       |  (🔽→: Return +0.3 s) ------>|
   |                  |                                  |                               |                       | else send→panel→commit→    |
   |                  |                                  |                               |                       |  deliverToTerminal(latch): |
   |                  |                                  |                               |                       |  shell/carrier guard,      |
   |                  |                                  |                               |                       |  stripControls, do script  |
   |                  |                                  |                               |                       |  + Return (+3rd Return if  |
   |                  |                                  |                               |                       |  'press Enter to send'     |
   |                  |                                  |                               |                       |  after the echo) --------->| terminal 2
   |                  |                                  |                               |                       |  outbox on .delivered only |
   |                  |                                  |                               |                       | nil target & unbound →     |
   |                  |                                  |                               |                       |  holdForBind (5 min queue) |
```

Guard owners: G0–G7 `HotkeyTap.handle` (`failingOpen` ~2320, flagsChanged ~2927, firewall ~3075–3107,
Wispr keyUp ~3125–3132); `isWispr` ~4506; canary `proveAlive` ~4582 (+ launch/wake/unlock in
`AppDelegate`, heal in progress); `gestureSeen` `WisprFlowSource.swift` ~1276; `pollHistory` ~2061;
`injected` ~2548; `rescueFromRow` ~2611; `AppDelegate.deliver` ~3454; `pasteText` ~9520;
`TerminalBinding.tap` ~1423.

Measured timings this diagram rests on (journal *The firewall*, 2026-09-22; *Word rental contract*,
09-13): row `formatted` 458–540 ms after close; ⌘V 407–506 ms, "arrived 30 ms before `formatted`";
words landed 5–10 ms after the relay saw the row (row poll 150 ms); Wispr restores the clipboard
inside ~250 ms of writing it; Wispr e2e p50 2.2 s / p99 7.1 s / max 13.7 s.

---

## 2. Findings, ranked by damage

Order: text in the wrong app / Victor's clipboard lost > duplicates > missed words > cosmetic.

### W-C1 — A caret sentence lands in whatever app is in front when the row arrives, and 🔽 → then presses Return there
*Wrong app, and possibly a shell command run.* **CONFIRMED-BY-READING** (path); trigger = a focus change inside the round trip.

- `WisprFlowSource.deliver` builds the result with `focusPid: startedMode == .scratchpad ? focusPid : nil`
  (~2773). Under the firewall `startedMode` is always `.off`, so `focusPid` is **always nil**.
- `AppDelegate.deliver` → caret → `pasteText(line, to: nil)` → `TerminalBinding.pressPaste()` = ⌘V into
  **the front app at delivery time**, not the app at the close. The Q2 latch fixes *which terminal*,
  never *which app* for the caret.
- `submitAfterCleanWords` (~7136, 🔽 →) posts a bare Return 0.3 s later, to the same front app.
- Interleaving: Victor holds right ⌘⌥ in Slack, lets go, ⌘Tabs to Terminal (a zsh prompt) to watch;
  Wispr's row is 0.5–13.7 s behind (p50 2.2 s) → the words are pasted into the shell prompt; with 🔽 →
  the Return **runs them**. The shell guard exists only on `deliverToTerminal`; the caret path has none.
  Wispr on its own aims at insertion time too, but never presses Return.
- **VM test:** witness TextEdit doc (app1) front; a Terminal tab at a bare `zsh` prompt in `/tmp/wc1`
  (not bound). Real Wispr hands-free via `POST /test/gesture {"name":"back-click"}` (Engine = Wispr),
  play the corpus clip into `🎓 TO Wispr`, `POST /test/gesture {"name":"back-right"}` (🔽 →), then
  within 300 ms `osascript -e 'tell app "Terminal" to activate'`. Assert: TextEdit empty; Terminal
  history (`fc -l`) contains the sentence → **FAIL = bug**. Variant without 🔽 →: the words sit at the
  zsh prompt (text in wrong app). Log: `📋 N chars on the clipboard — pasting at the caret` with no
  `addressed to pid`.
- **Desk:** held right ⌘⌥ in Notes, release, ⌘Tab to a Terminal prompt immediately. With 🔽 → do it
  only in a throwaway tab.
- Fix direction: latch the front pid at the close (`dictationStoppedListening` / `pushToTalkReleased`),
  pass it as `focusPid` for every caret sentence; if the front changed, `pressPaste(to:)` that pid or
  refuse with the `⌘⇧P` hint; never post the 🔽 → Return into a front app whose tty foreground is a shell.

### W-C2 — Every caret Wispr sentence destroys Victor's clipboard
*Clipboard lost.* **CONFIRMED-BY-READING.**

- `pasteText` (~9520) does `clearContents` + `setString` and **never restores** — by design for ⌘⇧P and
  Replace Wispr (*"he asked for it"*). Under the firewall it is also the delivery of **every caret
  sentence**: held right ⌘⌥ (Victor's commonest dictation, *"always the caret"*), the back click's clean
  sentence, a hand-started chord while unbound (`noteHandStartedAtCaret`), Q4's target-gone fallback.
- Before the firewall, Wispr pasted those itself and **restored** the clipboard afterwards. So the
  firewall silently changed *"dictating costs me nothing"* into *"dictating overwrites what I copied"*.
- **VM test:** `printf 'SENTINEL-%s' $RANDOM | pbcopy`; TextEdit front; a held right ⌘⌥ Wispr sentence
  (post the pair as `flagsChanged` with device bits 0x10|0x40 via Quartz — see hooks) with the clip
  playing; after `lastDelivery.to == caret`, `pbpaste` must equal the sentinel. Expected today: it
  equals the sentence → **FAIL**.
- **Desk:** copy a URL, dictate with right ⌘⌥ into Notes, ⌘V somewhere else.
- Fix direction: `pasteText(…, restore: true)` for engine deliveries (save `string(forType:)` +
  `changeCount`, restore after ~400 ms only if `changeCount` is still ours — `TerminalBinding.paste`
  already does half of this), keep no-restore for ⌘⇧P only.

### W-C3 — Wispr's clipboard dance still runs under the firewall, inside the relay's paste window: his OLD clipboard can be what gets pasted
*Wrong text at the caret / clipboard lost.* **PLAUSIBLE** (timings overlap on the measured numbers; Wispr's restore policy not measured).

- Dropping the ⌘V does not stop Wispr's `pasteboard := W → ⌘V → pasteboard := V` sequence. It starts
  ~30 ms **before** `formatted`; `pasteText` runs 5–160 ms **after** `formatted` (150 ms poll + main
  hop). Wispr's restore lands within ~250 ms of its write (09-13 measurement). So the relay's write +
  ⌘V fall inside Wispr's write→restore window routinely.
- Interleavings:
  1. relay `setString(E)` + ⌘V posted → Wispr restores V → the front app services ⌘V and reads **V** →
     his previous clipboard (the 09-13 *Word rental contract*, inverted) is typed at the caret; the
     clipboard ends as V.
  2. Wispr writes W after the relay's `setString(E)` but before the app reads → **W** pasted: for the
     forward click's caret prompt the envelope (frames, selection) is lost; Wispr restores E → his V is
     gone (W-C2).
  3. Victor's own ⌘V inside Wispr's window pastes W wherever he is (into app1 — the app the firewall
     protects); clipboard managers (Raycast/Paste) record every sentence.
- Aggravated with standalone **off** and Engine = ElevenLabs: right ⌘⌥ is also Wispr's `54+61`, so
  Wispr transcribes **every** clean hold too (its ⌘V is dropped, `heldPairIsTheEngines` stops the
  rescue — but the clipboard dance still runs, 0.5–13 s after release, overlapping Scribe's own
  `pasteText` when Wispr is slow).
- **VM test (run 20×, it is a race):** sentinel on the clipboard; TextEdit front, empty; held right ⌘⌥
  Wispr sentences with a 3–6 s clip. Per run record: TextEdit content, `pbpaste`, key-trace. Assert
  TextEdit == the row text and never contains `SENTINEL`. Add a `NSPasteboard.changeCount` timeline
  (hook below) to see the three writers' order. Second series with Engine = ElevenLabs, standalone off.
- **Desk:** copy a distinctive paragraph; ten quick right ⌘⌥ sentences into a scratch Notes page; look
  for the paragraph appearing instead of words.
- Fix direction: deliver caret words with `postToPid` + AX insert, or wait for Wispr's restore
  (`changeCount` quiet ≥ 300 ms after the row) before writing; never read-modify the pasteboard inside
  Wispr's window.

### W-C4 — Standalone (Q9) on: Victor's own Wispr sentence is swallowed during the relay's ownership window, then lost or delivered to the bound agent
*Wrong app or missed words.* **CONFIRMED-BY-READING** (the condition), trigger = timing.

- Tap (~3086): Wispr's ⌘V passes only if `wisprStandalone && !relayOwned && !armed`. `relayOwned` runs
  from the relay's gesture to its machine's `idle` **+ 10 s** (`wisprOwnedTail`), ceiling 11 min;
  `armed` = `injectionArmed`, set by `beginCapture`, kept by `retireDiscardedCapture` for a cancelled row.
- His own 54+60 sentence (`gestureSeen(relay:false)` returns early, no capture of its own) finishing
  inside that window → swallowed → `injected()`:
  - relay capture still open & intercepting → `"🛡️ ⌘V … dropped — the History row delivers"` → the
    relay delivers **its** row; **his sentence is delivered by nobody** (lost).
  - no capture (in the 10 s tail) → `rescueFromRow` → `didTranscribe` → `AppDelegate.deliver` with
    `latch == nil` → current binding (or the caret, per stale `latchedAtCaret`, W-C5): a sentence he
    aimed at Slack **goes into Claude Code**.
- The window can grow to 11 min: `idle` comes only from `state.reset` (`endCapture` skips it while
  `isRecording || speculative` — a Wispr close edge never seen keeps `isRecording`).
- **VM test (standalone on, Wispr `ptt`=54+60 in its config.json):** bound witness `cat` tab; F10 a
  relay Wispr sentence (short clip); at `lastDelivery` + 3 s post right ⌘⇧ held (Quartz flagsChanged
  54+60 with device bits) with a second clip into `🎓 TO Wispr` in TextEdit. Assert TextEdit has clip 2
  and the witness has clip 1 only. Expected: witness has both (rescue) or TextEdit empty (lost). Repeat
  with clip 2 started **during** clip 1's transcription.
- **Desk:** ⌘⌃D sentence to Claude, then within 5 s a Wispr right ⌘⇧ sentence into Notes.
- Fix direction: key ownership on **the row** (the relay's row id), not on time — swallow a Wispr ⌘V
  only while the relay's own row is non-terminal or within `pasteGrace` of its terminal status; never
  rescue in standalone.

### W-C5 — `latchedAtCaret` is never reset: a sentence whose close the relay did not see inherits the previous sentence's destination
*Wrong app (bound to terminal 2, pasted into app1) or held instead of caret.* **CONFIRMED-BY-READING** (stale state); trigger PLAUSIBLE.

- Written at `dictationStoppedListening` (~3244) and forced true in `deliver` (~3544,
  `if pasteMode || clean`); never cleared after a delivery (only the Q12 envelope swap touches it).
- Paths into `deliver` without `dictationStoppedListening`: `rescueFromRow` (a ⌘V with no capture); a
  sentence opened only by a mic edge whose close edge never came (`WisprWatch` 0–6 s late, "often
  silent"); the unconfident right ⌘⌥ path the comment at ~3540 describes.
- Interleaving: sentence N = held right ⌘⌥ (caret) → `latchedAtCaret = true`. Sentence N+1 is Wispr
  started by a route the tap does not know (Wispr's floating bar, its menu, F18, `54+60` with the Q9
  flag still off — W-C7) while bound to terminal 2 and app1 in front → ⌘V swallowed → rescue →
  `atCaret = true` → `pasteText` into **app1**. The exact case the firewall was built to prevent.
  Mirror: N went to a terminal (`false`), N+1 is a hand-started unbound sentence → `latch` nil →
  `holdForBind` instead of the caret (words wait 5 min).
- **VM test:** bound witness tab + TextEdit front. (1) held right ⌘⌥ sentence → TextEdit (expected).
  (2) start Wispr from its menu-bar item via `osascript`/AX (not a chord) with a clip; stop from the
  same item. Assert (2) lands in the witness, TextEdit unchanged, `GET /test/state.atCaret` false
  before delivery. Expected today: (2) pasted into TextEdit.
- Fix direction: reset `latchedAtCaret`/`pasteMode` at the end of every `deliver`; a rescued sentence
  computes its own destination (binding, else caret for a hand-started one).

### W-C6 — The push-to-talk detector reads this app's own posted modifier events: a held right ⌘⌥ is "released" by our own paste or chord
*Missed words (sentence cut or cancelled); in one config the gesture is dead.* **CONFIRMED-BY-READING** (tap side); Wispr's side PLAUSIBLE.

- `HotkeyTap` flagsChanged branch (~2927) computes `ptt` from **any** `flagsChanged`'s raw flags — no
  `backButtonStamp` / pid filter (the keyDown chords have one). Our posts carry no device-right bits and
  end in `flags = []`: `TerminalBinding.tap` (⌘ down / V / **⌘ up with []**, unstamped, HID tap, ~1423),
  `postWisprHandsFree` (trailing fn-up with [] , ~4254), `clearCommandAfterWisprPaste` ([], ~674).
- **(a) Standalone + Engine = Wispr (the two flags both true — nothing forbids it):** right ⌘⌥ →
  `onCleanHold(.press)` → `startDictation(paste:true, clean:true)` → `WisprFlowSource.start()` (`.off`)
  → `postWisprHandsFree`: waits its 200 ms for a bare wire that never comes (he is holding ⌘⌥), posts
  fn ⌃ Space, then `flagsChanged []` → tap sees `ptt = false` → `onCleanHold(.release)` ≈ 0.25–0.3 s
  after the press < `cleanHoldFloor` 0.35 s → `cancelDictationInFlight("tapped — too short")`. Every
  right ⌘⌥ in that config dies. (Also: fn⌃Space posted while ⌘⌥ are physically down — Wispr may not
  match `49+59+63` at all.)
- **(b) Any config:** sentence N at the caret is pasted (`pasteText` → `tap(⌘V)`) while he already holds
  right ⌘⌥ for N+1 → our `onWisprPushToTalkReleased`/`onCleanHold(.release)` fires mid-sentence, and
  Wispr (listening on 54+61, reading the same event stream) very likely sees ⌘ go up and ends its ptt.
  N+1 is truncated at the moment N lands. Back-to-back right ⌘⌥ sentences are his commonest rhythm.
- Side effect: `sessionFlags` reads `[]` while keys are physically down.
- **VM test (a):** `WT_WISPR_STANDALONE=1`, Engine = Wispr; post right ⌘⌥ down (flagsChanged 54 then
  61, flags `0x100000|0x80000|0x10|0x40`), hold 4 s with a clip, release. Assert a sentence at the
  caret; expected log `🧼 right ⌘⌥ released` ~0.25 s after the press, then `too short to be speech`.
  **(b):** two held-pair sentences, the second pressed 300 ms after the first's release (clip 1 long
  enough that its row arrives during hold 2). Assert both texts complete; watch key-trace for a
  `flagsChanged` from our pid inside hold 2 and `wispr history` of hold 2's row `duration`.
- **Desk:** two quick right ⌘⌥ sentences in a row; is the second cut short?
- Fix direction: ignore stamped/own-pid `flagsChanged` in the ptt branch, or read the pair from
  `CGEventSource.keyState(.hidSystemState, 54/61)`; stamp `TerminalBinding.tap`; make the trailing
  `flagsChanged` carry the physically held flags instead of `[]`.

### W-C7 — The Q9 flag and Wispr's own `ptt` shortcut are not cross-checked
*Duplicates at the caret, or sentences routed where he did not intend.* **CONFIRMED-BY-READING** (no check exists).

- The rule says *"flip it only after Wispr's `ptt` is `54+60`"*, but nothing enforces it; the app
  already parses Wispr's `config.json` (`scratchpadIsConfigured`, `open_scratchpad` by action name).
- Flag **on**, Wispr still `54+61`: right ⌘⌥ is `onCleanHold` (Engine) **and** Wispr's ptt. Wispr's
  ⌘V: not relay-owned, not armed → **passes** (the tap never consults `heldPairIsTheEngines`) → the
  sentence appears **twice** at the caret (Wispr's copy + the Engine's), Wispr's copy wherever focus is.
- Flag **off**, Wispr moved to `54+60`: the tap never sees Wispr's start (it watches 54+61), the ring
  is late or absent, the ⌘V is swallowed, the words come by mic edge or rescue → **the binding**, not
  the caret (*"să rămână întotdeauna neinfluențat de nimic"*), with W-C5's stale latch.
- **VM test:** both mismatches, one held-pair sentence each, TextEdit front + bound witness; count
  copies. Hook: `GET /engine.wisprShortcuts`.
- Fix direction: at launch and on `config.json` change, read `ptt`; refuse standalone (flash) unless it
  is `54+60`, and warn when it is `54+60` with the flag off.

### W-C8 — No per-sentence witness that the firewall caught *this* sentence's ⌘V: when it did not, Wispr's copy lands in the front app and the relay delivers a second copy
*Duplicate, first copy in the wrong app.* **PLAUSIBLE** (mechanism by reading; each blind spot below is real).

- The history route delivers at `formatted` whether or not `injected()` ever fired for that row. Every
  way the ⌘V escapes produces the same silent duplicate:
  1. Tap **blind**: Secure Input held by any app — the lock screen at wake (the 07:06–07:14 "dead tap"
     is most likely this), a password field, Terminal's *Secure Keyboard Entry*, 1Password. The other
     agent's heal now says `blind` and flashes the holder, but the delivery is not told.
  2. Tap **dead** between canaries (launch / wake / unlock / on demand only — nothing per sentence).
  3. `tapDisabledByTimeout` (G0): events pass until the callback re-enables.
  4. **Failing open** (main silent ≥ 3 s): documented *"may deliver twice"*.
  5. Wispr inserts **without** ⌘V: `extension_paste` / `extension_other` are in `terminalStatuses` and
     delivered like `formatted` (~2161). **DATA:** 7 such rows in Wispr's DB (last 2026-03-21, apps
     `com.conductor.app`, Word, Wispr) — rare, not zero. Or a future Wispr on `CGEventPostToPid`
     (journal flags it as the endgame risk).
- **VM tests:** (1) `POST /test/tap {"kill":"secure","seconds":20}` (the other agent's hook) then a real
  hands-free Wispr sentence, TextEdit front, bound witness → count copies; also Terminal ▸ *Secure
  Keyboard Entry* on with Terminal front. (4) `POST /test/stall {"seconds":8}` right after the stop
  chord. Expected: two copies, no warning on the chip, `lastDelivery.kind == route`.
- Fix direction: `capture.sawCmdV` (+ time); at `formatted + pasteGrace` with no ⌘V seen, mark the
  delivery `insertedElsewhere`, flash *"Wispr's paste was not caught — check <front app>"*, and expose it
  in `/test/state`; run a canary at every Wispr chord (1–4 ms); re-probe on `History.appVersion` change.

### W-C9 — A release missed while the tap is dead or being rebuilt leaves the held pair "down"
*Missed words.* **PLAUSIBLE.**

- `wisprPTTDown` / `enginePairHeld` are instance state updated only by seen `flagsChanged` events. If
  the release of right ⌘⌥ happens while the tap is blind/dead/rebuilding (the new `rebuildTap`), the
  clean sentence records until the next modifier event, and `heldPairIsTheEngines` stays true — so
  every Wispr sentence meanwhile has its mic edge ignored (`edge()` returns) and its ⌘V dropped
  without rescue: lost.
- **VM test:** held pair down (Quartz), `POST /test/tap {"kill":"unschedule","seconds":3}`, release
  during the kill, then a Wispr hands-free sentence. Assert the clean sentence ended at the release and
  the Wispr sentence is delivered.
- Fix direction: after any rebuild/heal, resync the pair from `keyState(.hidSystemState, 54/61)`.

### W-C10 — Firewall on + wrap forced off: the sentence is delivered by nobody
*Missed words.* **CONFIRMED-BY-READING** (race-dependent).

- `WT_WRAP_WISPR=0` or `POST /test/wrap-mode {"mode":"off"}` → `wrapWispr = false` → `intercepting =
  false`. The firewall still swallows. `injected()` (capturing, not intercepting) → `rescueFromRow`;
  its first attempt sees `processing` (the ⌘V is ~30 ms early) and retries in 150 ms; meanwhile
  `pollHistory` hits `guard intercepting else { … .silent("") }` → `endCapture` sets `lastRow = row`
  (~2796) → the retry finds `e.rowid == lastRow` → *"the newest row is one already delivered —
  nothing to put anywhere"*.
- **VM test:** `/test/wrap-mode off`, firewall on, `/test/wispr-handsfree {"hand":true}` + clip, TextEdit
  front. Assert words somewhere. Expected: nowhere, log line above.
- Fix direction: under the firewall `intercepting` is always true, or track *delivered rows* rather than
  `lastRow`.

### W-C11 — Wispr's answers bypass the Q12 sentence routing and share one set of per-sentence fields with the Engine
*Wrong destination / wrong envelope.* **PLAUSIBLE.**

- `wisprSource.didTranscribe = { deliver(result) }` (~2992) — no `runAnswer(for: sentence(forTake:))`.
  With Engine = ElevenLabs, a hand-started Wispr sentence (fn ⌃ Space) landing while an ElevenLabs
  sentence is in flight consumes `latch`, `latchedAtCaret`, `cleanSentence`, `caretPrompt`,
  `kamikaze`, pending shots of the Engine's sentence; the Engine's answer then finds `latch == nil`
  and goes to *the next bind* / current binding.
- **VM test:** Engine = ElevenLabs with `POST /test/eleven {"fail":"delay","delayMs":4000}`; F7 forward
  click sentence (caret prompt, context shot) → stop → within 1 s a Wispr `/test/wispr-handsfree
  {"hand":true}` sentence (bound witness). Assert each text with its own envelope and destination.

### W-C12 — Wispr features that end in ⌘V but are not dictations are swallowed and rescued as dictations
*Wrong app / missed action.* **PLAUSIBLE.**

- Wispr Command Mode (select text, speak an instruction, Wispr pastes the rewrite — `transcriptCommand`
  column exists) and *paste last transcript*: the ⌘V is dropped; with no capture, `rescueFromRow`
  sends the rewritten text to the **bound agent** as a sentence, and the selection in the front app is
  never replaced.
- **VM test:** select a word in TextEdit, trigger Wispr's command mode with a clip ("make this
  uppercase"), bound witness. Assert what lands where.

### W-C13 — `54+60` (right ⌘ + right ⇧) collides with right-hand ⌘⇧ shortcuts
*Cosmetic / stray ring, occasionally a stray short paste.* **PLAUSIBLE.**

- ⌘⇧P (our own re-paste; the P is swallowed but Wispr reads the modifiers), ⌘⇧T, ⌘⇧4/5, ⌘⇧Z typed
  with the right-side modifiers start Wispr's ptt; in standalone the result is Wispr's own and passes.
- **Desk:** ten right-hand ⌘⇧P / ⌘⇧T; count Wispr rows created (`dismissed`/`empty`/short `formatted`).

### W-C14 — The ⌘-clear after a let-through Wispr paste cancels a ⌘ he is really holding
*Cosmetic.* **PLAUSIBLE.** `clearCommandAfterWisprPaste` posts ⌘-up with `flags = []` whenever
Wispr's ⌘V keyUp passes (standalone, firewall off, failing open): a ⌘Tab switcher he is holding closes,
a ⌘-click becomes a click. Same fix family as W-C6 (post the physically held state).

### W-C15 — The fail-open watchdog runs on the tap thread, which can block on `stateLock`
*Low.* **PLAUSIBLE.** The callback takes `HotkeyTap.stateLock` in the firewall block (~3079) and
elsewhere; the 10 Hz watchdog is on the same run loop. A main thread wedged *inside* a `stateLock`
section stalls both, macOS disables the tap by timeout, and events pass unfiltered — fail-open by the
OS, not by `MainStallGate`, and `/test/stall` (which holds no lock) does not model it. Critical sections
look short today; keep them so, or read the firewall flags with atomics.

---

## 3. Standalone vs Engine = Wispr (asked explicitly)

- **Both can be true**; nothing refuses the combination (`wisprStandalone` is a launch-time `static let`,
  the Engine is a menu pick).
- What arms the swallow then: the relay's gesture → `gestureSeen(relay:true)` →
  `setWisprRelayOwned(true)` (~1303) + `beginCapture` → `armInjectionCapture(swallow:true)`; the tap
  drops a Wispr ⌘V while `relayOwned || armed` (W-C4 for the window's width).
- What breaks in it: right ⌘⌥ → `onCleanHold` → `WisprFlowSource.start()` posts fn ⌃ Space under
  physically held ⌘⌥, and the trailing `flagsChanged []` cancels the hold (W-C6a).

## 4. Harness hooks missing

- **`POST /test/tap {"kill": …}`** — being added by the other agent right now (unschedule / invalidate /
  disable / secure, `/test/firewall` answers `alive|open|blind|dead`). W-C8, W-C9 depend on it.
- **`POST /test/modifiers {"hold": ["rcmd","ropt"|"rshift"], "seconds"}`** — post a held right-hand pair
  as `flagsChanged` with device bits, released on its own. `/test/gesture` cannot hold modifiers; W-C2,
  W-C3, W-C4, W-C6, W-C7, W-C9 need it (until then: a Quartz one-liner in the guest).
- **`GET /test/state.pasteboard`** — `changeCount` timeline during a capture (who wrote, when, length,
  sha1 — never the text). Needed to order Wispr's write/restore against `pasteText` (W-C2, W-C3).
- **`GET /test/state.capture.sawCmdV`** (+ ms after close) and **`state.wisprRelayOwned {since,
  releasedAt, active}`**, **`state.injectionArmed`** (W-C4, W-C8).
- **`GET /engine.wisprShortcuts`** — Wispr's `ptt` / `popo` from `config.json` beside `wisprStandalone`
  (W-C7).
- **`POST /test/wispr {"unclaimedPaste": true}`** — call `injected(from:)` with no capture, to drive the
  rescue deterministically (W-C4, W-C5, W-C10, W-C12).
- **`POST /test/front {"bundle", "afterStopMs"}`** — activate an app N ms after the close (W-C1); in the
  guest `osascript … activate` does it.
- `GET /test/state.atCaret` already exposes `latchedAtCaret` (W-C5) and `sessionFlags` the window
  server's modifiers (W-C6) — no hook needed.
