# Wispr Flow as the engine — merged findings, work plan, questions (2026-09-28)

Merges the four adversarial reads in this folder — `A-lifecycle.md` (W-A*), `B-errors.md` (W-B*),
`C-firewall.md` (W-C*), `D-state.md` (W-D*) — against the journal's Wispr decisions (*The firewall*
2026-09-22, *`raw_transcript` is a finished sentence*, *Decisions on the test plan's findings* Q1–Q7,
batch 3 §4–5, Q8, **Q9**, Q12, Q13, *Morning of 2026-09-27*) and CLAUDE.md's *Never reintroduce*.
Nothing was run and no code was edited for this file. Line numbers in the four reports have
drifted by ~60 lines in `WisprFlowSource.swift` since they were written: **use the function names**.

**Victor's daily use that the ranking assumes** (from the brief): Engine = Wispr, Q9 standalone
ON (`WT_WISPR_STANDALONE=1`), **right ⌘⌥ held = Walkie's clean caret sentence**, **right ⌘⇧ =
Wispr's own ptt (`54+60`)**, dictating into Claude Code terminals (bound) and at the caret in
Chrome / IntelliJ.

> Caveat: as read from disk on 2026-09-28, the installed Engine was `eleven-live` (A), and the
> Engine menu hides the Wispr row unless it is already the engine (Victor's 2026-09-25 *"ascunde pt
> moment wispr flow"*). W1, W6 (half), W9, W10 and W11 bite **only** with Engine = Wispr; W5 and W7
> bite on every caret sentence whatever the engine.

Labels: **CBR** = confirmed by reading (the code path is traced to the wrong outcome). **PL** =
plausible (depends on Wispr / macOS behaviour or timing nobody has measured). **DB** = seen in
Wispr's own `History` table (read-only, counts only).

---

## 0 · Ranking at a glance

| # | finding | damage | conf. | fix |
|---|---|---|---|---|
| W1 | Right ⌘⌥ held on Engine = Wispr cancels itself ~0.25 s in (our own posted key reads as the release) | words lost | CBR | now |
| W2 | A row with no microphone behind it is taken as "Wispr is recording": Listening over a deaf Wispr, then 30 s stuck | words lost + stuck | CBR + DB | now |
| W3 | Every Wispr failure throws away the recording the relay already has; *No speech was heard* is usually false | words lost | CBR + DB | now + Q1 |
| W4 | His own right ⌘⇧ sentence overlapping a relay Wispr sentence: swallowed, and it blinds the relay's row | words lost / wrong app | CBR | now + Q7 |
| W5 | Every caret sentence overwrites the clipboard | clipboard | CBR | **Q5** |
| W6 | Start/stop are one toggle posted blind: ghost Wispr recordings, starts over his own Wispr sentence | wrong app / lost / stuck | CBR relay, PL Wispr | now |
| W7 | A caret sentence lands in whatever app is in front when the row arrives; 🔽 → presses Return there | wrong app | CBR | **Q6** |
| W8 | Wispr's clipboard write/restore still runs and races the relay's caret paste: his old clipboard can be typed | clipboard / wrong text | PL | now (measure first) |
| W9 | Starts during Wispr's formatting are refused with no flash | words lost (spoken into nothing) | CBR | now + Q4 |
| W10 | The next Wispr sentence force-sends a held / paused / edited prompt panel | wrong app (sent, not held) | CBR | **Q3** |
| W11 | Cold Wispr is deaf for 0.3–6 s while the chip says Listening and the ring breathes | words lost (first seconds) | CBR | **Q8** |
| W12 | A row that finishes after 30 s is dropped and logged as "already delivered" | words lost | CBR + DB | **Q2** |
| W13 | When the firewall misses Wispr's ⌘V (Secure Input, dead tap, fail-open) the sentence arrives twice, silently | duplicated | PL | now |
| W14 | A Wispr update that changes the row's shape fails closed: every relay Wispr sentence lost | words lost | CBR path / PL trigger | now |
| W15 | Chord tables and docs drifted (`54+61` still called Wispr's ptt); nothing cross-checks the Q9 flag against Wispr's config; the old path is still wired | duplicated / stuck if they diverge | CBR | now |
| W16 | `latchedAtCaret` is never reset: a sentence whose close was not seen inherits the last destination | wrong app | CBR state / PL trigger | now |
| W17 | `rescueFromRow` has no freshness check: an old sentence, Command Mode or *paste last* is delivered to the bound agent | wrong app | CBR path / PL trigger | now |
| W18 | A release missed while the tap is blind / rebuilt leaves the held pair "down" | words lost / stuck | PL | now |
| W19 | Wispr not running: stale flags + spawn menu, two readiness tests, ⌃Space to the front app | stuck / cosmetic | CBR | now |
| W20 | The corpus pairs Wispr's words with a different microphone's audio | cosmetic (corpus data) | CBR | now |
| W21 | Wall-clock windows beside uptime timers break across sleep | wrong app (rare) / stuck | PL | later |
| W22 | Firewall on + wrap forced off: the sentence is delivered by nobody | words lost (test config) | CBR | now |
| W23 | Smaller items (language column, Scratchpad text column, markerClock leak, …) | cosmetic | mixed | now / note |

---

## 1 · Merged findings, ranked

### W1 — Right ⌘⌥ held on Engine = Wispr cancels itself

**Sources:** W-D1 (standalone ON half) + W-C6 (a, b) + W-C14. **Damage:** words lost. **Confidence:**
CBR on the relay side (two reviewers traced it independently); PL whether Wispr accepts
fn ⌃ Space while right ⌘⌥ are physically held.

You hold right ⌘⌥. The relay starts a Wispr sentence by *posting* Wispr's hands-free chord
(fn ⌃ Space). That post ends with a modifier event whose flags are empty. The tap's push-to-talk
detector reads **every** modifier event, including the app's own, so it concludes you let go
~0.25 s after you pressed. A hold under 0.35 s counts as "tapped — too short" and the sentence is
cancelled quietly: you talk into nothing, no flash. The same blindness hits back-to-back sentences
on any engine: while you already hold right ⌘⌥ for the next sentence, the relay's ⌘V paste of the
previous one ends with ⌘ up and cuts the new hold short. And after a let-through Wispr paste the
relay posts a ⌘-up that closes a ⌘Tab switcher you are holding.

**Fix:** the pair branch in `HotkeyTap.handle` ignores stamped / own-pid `flagsChanged` and reads the
pair from `CGEventSource.keyState(.hidSystemState, 54/61)`; stamp `TerminalBinding.tap`; the trailing
modifier events of `postWisprHandsFree` and `clearCommandAfterWisprPaste` carry the physically held
flags instead of `[]`.

### W2 — A row is not a microphone: Listening over a deaf Wispr, then 30 s stuck

**Sources:** W-A1 + W-B7 + W-B10 (NULL / `processing` never timed out early). **Damage:** words lost
+ stuck. **Confidence:** CBR + DB (100 NULL rows in Sept on your own mics; 9 of them followed by a
re-press 31–32 s later — the relay's 30 s stall, visible in Wispr's table).

Wispr sometimes takes the chord, writes its row, and never opens the microphone. The relay reads
"a row appeared" as "Wispr is recording": it cancels the 12 s *Wispr ignored the chord* check and
shows Listening for your whole sentence, the ring breathing on the relay's **own** microphone, which
does hear you. At the stop the row stays empty, so the chip says Transcribing for 30 s, every start
is refused, and it ends *No words came back*. A quick re-press within ~2 s makes it worse: the
relay adopts the **dead** row instead of the new one, and the sentence Wispr did transcribe is
never read.

**Fix:** in `WisprFlowSource.pollHistory` / `confirmSpeculative`, confirm only with Wispr's microphone
seen open (`WS.pollMs != nil`) or a row with `duration`; a NULL row with no microphone after
`speculativeGrace` is the retraction (with a flash, and the WAV per Q1). Give NULL-without-mic its
own short ceiling (like `silenceCeiling`). In `beginCapture` adopt only a rowid **greater than**
`priorRow`.

### W3 — Every Wispr failure throws away the recording the relay has

**Sources:** W-B3 + W-D3 + W-A2 + W-B6 + W-B10 (Wispr's own `dismissed`) + W-D13 (fallback row).
**Damage:** words lost. **Confidence:** CBR (every path) + DB (308 of 354 textless `raw_transcript`
rows had `speechDuration` > 0.5 s; 56 on the built-in mic, 10 on the DJI).

For every Wispr sentence the relay also records you (`startMeter`, `wispr-<ts>.wav`). When Wispr
fails — no text, `error`, stuck `processing`, the 30 s timeout, Wispr quitting, or no answer to the
chord at all — the relay ends the sentence as "silent" and the WAV is deleted or left orphaned in
Caches. Nothing goes to the local model, nothing to *Recover*. The banner is often a lie: *No speech
was heard* when Wispr's own row says it heard 5 s of speech; *the sentence is lost* when the audio is
on disk; the 12 s "Wispr ignored it" cut shows **no flash at all**. Meanwhile the sentence's
screenshots are released to the bound agent alone, a picture message for words that were thrown
away.

**Fix (evident part):** read `speechDuration` in `WisprHistory.Entry`; say what happened (*Wispr Flow
returned no words for N s of speech*, *Wispr Flow did not answer the chord*); flash on the 12 s
drop; never orphan the meter WAV. **What to do with the WAV and the pictures is Q1.**

### W4 — His own Wispr sentence overlapping a relay Wispr sentence: both can be lost

**Sources:** W-C4 + W-D4 + W-B1 + W-D7 + W-C12 + W-A5 (rescue reads `newest()`) + A §2 rows 4, 10,
11. **Damage:** words lost / wrong app. **Confidence:** CBR; the trigger is ordinary timing
(dictate to the agent, then at once right ⌘⇧ into a document).

"The relay owns Wispr" is a **time window** — from the relay's gesture until 10 s after its sentence
ends (ceiling 11 min) — not a sentence. Any Wispr ⌘V inside it is swallowed, including the paste of
your own right ⌘⇧ sentence, which Q9 says must be left alone. Two outcomes: while the relay's
capture is open your words are delivered by nobody; in the 10 s tail they are "rescued" and sent to
the **bound Claude Code terminal** instead of the caret. Worse, the relay reads only the **newest**
History row: your newer row hides the relay's own row, so the relay's sentence also waits 30 s and
dies, or is delivered late in the wrong slot. Wispr's Command Mode inside the window is rescued as
a dictation too.

**Fix (evident, the journal's own *Known edge* line in Q9 batch 6 §4):** once a row is adopted,
`pollHistory` / `captureExpired` read `entry(rowid: historyRow)`, never `newest()`; ownership is
keyed on the relay's row id — `HotkeyTap.setWisprRelayOwned` carries the row, and the firewall drops
a Wispr ⌘V only while that row is non-terminal or within `pasteGrace` of its terminal status; no
rescue of unclaimed pastes under standalone. **The residual overlap (both rows open when a ⌘V
arrives) is Q7.**

### W5 — Every caret sentence overwrites the clipboard

**Sources:** W-C2. **Damage:** clipboard. **Confidence:** CBR.

`pasteText` clears the clipboard, writes the sentence, presses ⌘V and never puts your clipboard
back. Under the firewall that is how **every** caret sentence lands (held right ⌘⌥, 🔽, Q4's
target-gone fallback). Before the firewall Wispr pasted those itself and restored your clipboard, so
"dictating costs me nothing" quietly became "dictating overwrites what I copied".
**Not a fix-now:** the journal records "the clipboard is not restored" as a **deliberate** feature of
the caret paste (*Replace Wispr*, *⌘⌃P pastes the last dictation*: "he asked for it", the words stay
one ⌘V away). The brief's assumption conflicts with that entry → **Q5**.

### W6 — Start and stop are one toggle, posted blind

**Sources:** W-A4 + W-B8 + W-B9 + W-D5 + W-D6 + A §2 rows 5–8, 13. **Damage:** wrong app (a ghost
Wispr recording of the room pasted at the caret or delivered), words lost, stuck. **Confidence:**
CBR on the relay side; PL for what Wispr does with a late / queued / extra chord.

The relay starts and stops Wispr with the same chord and never asks Wispr whether it is recording.
If Wispr misses the stop, is slow to start (cold), stops by itself (device change, its own window),
or is hung and replays queued chords, the two sides disagree: Wispr records the room with no ring,
and the next relay click *stops* it instead of starting a sentence (two sentences lost, one 12 s
ring over nothing). With Engine = Wispr the check that refuses a start over **your** running Wispr
sentence is skipped on purpose (`startDictation`: `if source !== wisprSource`), and under Q9 the
relay cannot see your right ⌘⇧ sentence, so ⌘⌃D / 🔼 post a toggle into it. The 🔽 path already
asks Wispr's live microphone before deciding start-vs-stop; the forward paths do not.

**Fix:** `WisprFlowSource.start()` / `stop()` sample `wisprMic.sampleIsRunningInput()` (the 3-read
sampler `wisprMicIsOpen` uses) plus the newest row's state before posting: start over a Wispr that
is already recording and not the relay's → refuse with the existing *one engine at a time* flash
(drop the `source !== wisprSource` skip); stop with no open mic and no open row → close without
posting; a terminal row while `isRecording` goes through `closeListening` first. Decision already
on record: Victor 2026-09-18, *"Trebuie exclusiv, ba unu, ba altu."*

### W7 — A caret sentence lands in whatever app is in front when the words arrive

**Sources:** W-C1. **Damage:** wrong app (and a shell command run with 🔽 →). **Confidence:** CBR
for the path; the trigger is a focus change inside Wispr's 0.5–13.7 s round trip.

The relay pastes the caret sentence into the app in front **at delivery**, not the app you were in
when you let go. Release right ⌘⌥ in Chrome, ⌘Tab to a terminal to watch, and the words land at the
shell prompt; with 🔽 → the Return 0.3 s later **runs them**. The shell guard exists only on terminal
delivery, not on the caret path. The Q2 latch fixes *which terminal*, never *which app*. Whether the
caret should be latched like the terminal is not decided → **Q6**.

### W8 — Wispr's clipboard dance races the relay's paste

**Sources:** W-C3. **Damage:** clipboard / wrong text at the caret. **Confidence:** PL (the measured
timings overlap: Wispr writes ~30 ms before `formatted` and restores within ~250 ms; `pasteText`
runs 5–160 ms after `formatted`).

Dropping Wispr's ⌘V does not stop Wispr from writing its text to the clipboard and restoring your
old clipboard a moment later. The relay writes and pastes inside that window, so the app can read
**your previous clipboard** (the 2026-09-13 *Word rental contract*, inverted) or Wispr's text without
the envelope. Clipboard managers record every sentence.

**Fix:** measure first (pasteboard hook, HK10); then `pasteText` waits for the pasteboard to be quiet
(Wispr's restore seen, or `changeCount` still ≥ 300 ms after the row) before writing.

### W9 — Starts during Wispr's formatting are refused in silence

**Sources:** W-D9 + W-C11 (answers bypass Q12's `runAnswer`) + D fact F3. **Damage:** words lost
(spoken into nothing if he does not watch the chip). **Confidence:** CBR.

On Wispr, 🔼 / ⌘⌃D / right ⌘⌥ during the 0.5–13 s the words are in flight are refused with a log
line only; on ElevenLabs the same press opens a queued sentence (Q12). Batch 3 §4 already decided "a
flag that refuses a gesture says so".
**Fix:** a flash in `onPasteToggle`'s in-flight branch, `startBlocker`, `onCleanHold`'s press.
**Whether Wispr should queue like ElevenLabs is Q4.**

### W10 — The next Wispr sentence force-sends the held prompt panel

**Sources:** W-D8 + W-C11. **Damage:** wrong app (sent where he meant to hold, review or edit it).
**Confidence:** CBR for the bypass; PL for the paused / editing outcome.

With Autosend off, a Wispr sentence that lands while a panel is on screen sends that panel —
including one you paused to read or are editing — because Wispr's answers skip the queue rule
(`runAnswer`) that makes ElevenLabs answers wait. **Q3.**

### W11 — Cold Wispr is deaf while the chip says Listening

**Sources:** W-D2 + A §2 row 1 (+ the `caret-short-cold` harness red). **Damage:** words lost (the
first seconds). **Confidence:** CBR for the mechanism; how often his Wispr is cold is PL.

The relay opens the sentence at the chord. A warm Wispr opens its mic 0.3–0.7 s later, a cold one
5–6 s later. Meanwhile the chip says Listening and the ring breathes on the relay's own mic, so
nothing tells you your first words are going nowhere. **Q8.**

### W12 — A row that finishes after 30 s is dropped as "already delivered"

**Sources:** W-B2 + W-A5 (ownership tail vs Wispr's e2e) + W-B10 (8 s ceiling vs fallback ASR).
**Damage:** words lost. **Confidence:** CBR + DB (Wispr's own fallback ASR finishes at 24–36 s;
its `error` lands at ~33 s: Wispr's budget is longer than the relay's 30 s).

At 30 s the relay gives up (*No words came back*); when Wispr finishes at 33–36 s its paste is
swallowed and the log says the newest row "is one already delivered" — the words sit in Wispr's
History. Past idle + 10 s a very late paste is instead let through into whatever app is in front.
Batch 3 §5 decided "the settle never gives up while the recogniser is still working", but Wispr's
30 s cap was left in place. **Q2.**

### W13 — A ⌘V the firewall did not catch: two copies, silently

**Sources:** W-C8 + A §2 row 15. **Damage:** duplicated (first copy in the wrong app). **Confidence:**
PL (each blind spot is real: Secure Input — the 07:06–07:14 lock-screen "dead tap" —, a dead tap
between canaries, `tapDisabledByTimeout`, fail-open, and 7 DB rows of `extension_paste`).

The relay delivers from the row whether or not it saw Wispr's ⌘V. When the ⌘V escapes, Wispr's copy
lands in the front app and the relay's copy lands in the terminal, and nothing says so.
**Fix:** `capture.sawCmdV`; when a relay-owned row goes terminal with no ⌘V seen within
`pasteGrace`, flash *Wispr's paste was not caught — check <front app>* and expose it in
`/test/state`; the relay's delivery is unchanged (it is the intended copy).

### W14 — A Wispr update that changes the row's shape fails closed

**Sources:** W-B4 + W-B10 (transient read errors, VACUUM). **Damage:** words lost (every relay Wispr
sentence). **Confidence:** CBR path / PL trigger (Wispr auto-updated 1.6.721 → 1.6.957 in Sept).

A renamed column, an epoch `timestamp`, or a replaced DB file makes the reader return nothing — and
in one case log nothing. Every relay Wispr sentence then dies at 30 s while the firewall still eats
Wispr's own paste of it. The canary checks the tap, not the reader.
**Fix:** a reader health check in `WisprHistory` at launch, on Wispr relaunch and on an
`appVersion` change (newest row non-nil, `startedAt` recent, rowid ≥ last seen); while it fails,
open the firewall and flash once; re-stat the file's inode per capture; log BUSY/IOERR. Consistent
with Q9: Wispr must keep working *"even if Walkie dies"*.

### W15 — Chord drift, no cross-check, the old path still wired

**Sources:** W-C7 + W-D1 (standalone OFF half) + A's config note + D's `vm-wispr.md` note.
**Damage:** duplicated / stuck — **only if** the flag and Wispr's config diverge (today they agree:
flag ON, `ptt` = `54+60`). **Confidence:** CBR.

The doc-comment table of Wispr's chords in `HotkeyTap.swift` (~L107) still says `54+61 | ptt`, as do
comments in `HotkeyTap` (~L201, ~L266, ~L4448), `AppDelegate` (~L6254 *"off until Wispr moves"*),
`WisprFlowSource` (~L1549), `.claude/rules/dictation-source.md` (*"built, OFF"*),
`mouse-gestures.md` L42/L58, `replace-wispr-and-halo.md` L468/L705, `docs/vm-wispr.md` L122/L420
(the guest would be set up with the old chord) and `docs/teacher-loopback.md` L65. Nothing checks
that Wispr's `ptt` is `54+60` when the flag is on: if it is ever `54+61` again, right ⌘⌥ opens two
recognisers and the sentence lands twice. The old adoption path the Q9 decision said to delete in a
follow-up commit is still there, and is the door to W16, W17, W18 and half of W4.

**Fix:** Q9 step 2 as decided; fix the tables; a launch / `config.json`-change check that flashes
when Wispr's `ptt` is `54+61` (collides with Walkie's pair).

### W16 — `latchedAtCaret` is never reset

**Sources:** W-C5. **Damage:** wrong app. **Confidence:** CBR for the stale flag; PL trigger (paths
into `deliver` that skip `dictationStoppedListening`: a rescue, a close edge never seen).

The "this sentence goes to the caret" flag survives the delivery, so the next sentence that reaches
delivery without a seen close inherits it: a sentence meant for the bound terminal is pasted into
the app in front, or a caret one is held for a bind.
**Fix:** reset `latchedAtCaret` / `pasteMode` at the end of every `AppDelegate.deliver`.

### W17 — The rescue has no freshness check

**Sources:** W-B5 + W-C12 (Command Mode / *paste last transcript* rescued as a dictation).
**Damage:** wrong app. **Confidence:** CBR path / PL trigger — mostly closed by standalone (an
unclaimed ⌘V now passes) except inside the ownership window (W4).

`rescueFromRow` hands the newest row to delivery whenever it is not `lastRow`, which is in memory
only: after `relay-restart.sh`, an hours-old sentence can go to the bound agent.
**Fix:** delete the unclaimed-paste rescue with Q9 step 2; any rescue that remains takes only rows
whose `startedAt` is within ~60 s and not in `outbox.jsonl`.

### W18 — A missed release leaves the held pair "down"

**Sources:** W-C9. **Damage:** words lost / stuck. **Confidence:** PL.

If you release right ⌘⌥ while the tap is blind, dead or being rebuilt, the relay keeps recording
until the next modifier event, and (old path) `heldPairIsTheEngines` stays true for 30 s.
**Fix:** after every tap rebuild / heal / Secure-Input end, resync the pair from
`keyState(.hidSystemState, 54/61)`.

### W19 — Wispr not running

**Sources:** W-D10 + W-A5 (`isReady` prefix match) + W-D12 (⌃Space with no Wispr, no readiness flash
on the engine pick). **Damage:** stuck / cosmetic. **Confidence:** CBR.

With Wispr down, 🔼↑ still opens the folder menu and leaves `spawnPending`, `pasteMode`,
`caretPrompt` set for a sentence that never starts; a helper-only Wispr passes `isReady` and then
dies 300 ms later as *Wispr Flow quit — the sentence is lost*; 🔽 posts fn ⌃ Space into the front app.
**Fix:** in `startDictation`, set the gesture's flags and `offerSpawnFolders()` only after
`source.start()` is accepted (or reset them on refusal); `isReady` anchored on the main executable
like `abandonForDeadWispr`; the F6 path checks `isReady`; `setEngine` flashes when Wispr is not
running.

### W20 — The corpus pairs Wispr's words with another microphone's audio

**Sources:** W-D11 + W-D13 (`micOpened`). **Damage:** cosmetic (data quality of a corpus that is
never pruned). **Confidence:** CBR.

The corpus row is the relay meter's WAV (XLR) + Wispr's formatted text (Wispr heard the built-in
mic on 2026-09-27). In a room the built-in mic hears participants the XLR does not.
**Fix (non-lossy):** record Wispr's `History.micDevice` beside the meter's device in the corpus row
and flag a mismatch; expose Wispr's device separately from `micOpened` in `/test/state`.

### W21 — Sleep breaks the windows' ordering

**Sources:** W-A3. **Damage:** wrong app (rare) / a phantom ring. **Confidence:** PL (low).
Some windows use uptime, others the wall clock; across a closed lid they drift apart (the 11 min
ownership ceiling can read expired while the capture is still armed). **Fix:** one clock for all
Wispr windows (batch 4 chose uptime for the fail-open); low priority.

### W22 — Firewall on + wrap forced off: delivered by nobody

**Sources:** W-C10. **Damage:** words lost — only with `WT_WRAP_WISPR=0` / `/test/wrap-mode off`.
**Confidence:** CBR. **Fix:** under the firewall `intercepting` is always true (or track delivered
rows instead of `lastRow`).

### W23 — Smaller items

| item | source | fix |
|---|---|---|
| `language` is never filled; `detectedLanguage` is (4998/5000) | W-B10 | read `detectedLanguage` in `WisprHistory` |
| Scratchpad mode delivers `formattedText` (one pass earlier than `pastedText`, differs in 57 %) | B §1 | prefer `pastedText` in `deliverFromRow` |
| `/test/dictation/start {"clock":true}` leaves `markerClock` on a wall-clock ruler until the next engine switch | D W-D13 note | restore it at the end of the desk sentence |
| second-resolution `wispr-<epoch>.wav` can collide on cancel + restart within 1 s | W-D3 | millisecond name |
| fail-open watchdog shares the run loop with `stateLock` holders | W-C15 | keep critical sections short / atomics; note only |
| right-hand ⌘⇧P / ⌘⇧T / ⌘⇧4 start Wispr's ptt (`54+60`) | W-C13 | Q11 (measure) |
| Wispr's post-paste observer watches the wrong textbox (3001 `dictated_text_not_found` in Sept) with auto-learn on | W-B10 | Q10 |
| the Engine menu hides Wispr once you pick another engine | W-D12 | **by design** (Victor 2026-09-25) — no action |
| affect tags, inline picture markers, live caption silently absent on Wispr | W-D13 | inventory only |

---

## 2 · Fix now — ordered work plan

Only what the journal already decides, or where the current behaviour is unambiguously wrong and
the fix changes no decision. Each step is its own commit; the harness case is in §4.

1. **W1 — the pair ignores the app's own modifier events.** `HotkeyTap.handle` (flagsChanged pair
   branch): skip stamped / own-pid events, read the pair with `CGEventSource.keyState(.hidSystemState,
   54/61)`; `TerminalBinding.tap`: stamp its events; `HotkeyTap.postWisprHandsFree` and
   `clearCommandAfterWisprPaste`: trailing flags = the physically held modifiers. **Then run TW1 in
   the VM:** if Wispr does not take fn ⌃ Space while ⌘⌥ are physically held, stop and ask Q9.
2. **W15 — Q9 step 2 (decided 2026-09-26, "follow-up commit").** Delete the tap's
   `onWisprMaybeStarting(.pushToTalk)` / `onWisprPushToTalkReleased` branch, `heldPairIsTheEngines`,
   the hand-started adoption in `WisprFlowSource.gestureSeen` / `edge`, the unclaimed-paste
   `rescueFromRow`, `noteHandStartedAtCaret`, `wisprMicSentence`, and the `wisprStandalone` flag.
   Fix the chord tables and texts listed under W15 (`HotkeyTap.swift`, `AppDelegate.swift`,
   `WisprFlowSource.swift`, `dictation-source.md`, `mouse-gestures.md`, `replace-wispr-and-halo.md`,
   `docs/vm-wispr.md` — **before the first guest run**, `docs/teacher-loopback.md`). Add the launch /
   `config.json`-change check: flash when Wispr's `ptt` is `54+61`.
3. **W4 + W2 (adoption half) — read the capture's own row, own the row not the clock.**
   `WisprFlowSource.pollHistory` / `captureExpired`: `entry(rowid: historyRow)` after adoption;
   `beginCapture`: adopt only rowid > `priorRow`; `HotkeyTap.setWisprRelayOwned` → carries the row
   id, firewall drops a Wispr ⌘V only while that row is non-terminal or within `pasteGrace` of its
   terminal status (the 10 s tail and the 11 min ceiling go). Residual overlap → Q7.
4. **W2 — a row without a microphone is not a sentence.** `confirmSpeculative` only on
   `WS.pollMs != nil` or a row with `duration`; `speculativeDrop` retracts a NULL-with-no-mic row with
   a flash; a short NULL-no-mic ceiling in `pollHistory` beside `silenceCeiling`.
5. **W6 — ask Wispr before toggling it.** `WisprFlowSource.start()` / `stop()` sample the mic (the
   `wisprMicIsOpen` sampler) and the newest row; `AppDelegate.startDictation` drops the
   `source !== wisprSource` skip so the *one engine at a time* refusal covers Engine = Wispr; a
   terminal row while `isRecording` → `closeListening` first (`pollHistory`).
6. **W3 (evident part) — say the truth, keep the file accounted for.** `WisprHistory.Entry` reads
   `speechDuration`; `pollHistory`'s empty-`raw_transcript` branch and the `error` / unknown branch
   name what happened; `speculativeDrop` flashes a reason instead of `.silent("")`;
   `WisprFlowSource.startMeter` never drops an un-handed-over `recording` without deleting or staging
   it (which one = Q1).
7. **W9 — a refusal says so** (batch 3 §4). A flash in `AppDelegate.onPasteToggle` (in-flight
   branch), `startBlocker` / `queueRefusal`, and `onCleanHold`'s press.
8. **W14 — reader health.** `WisprHistory` check at launch / Wispr relaunch / `appVersion` change;
   `HotkeyTap` opens the firewall while it fails; inode re-stat per capture; log BUSY / IOERR in
   `WisprHistory`.
9. **W13 — a witness per sentence.** `capture.sawCmdV` set in `WisprFlowSource.injected`; flash +
   `/test/state` field when a relay-owned row is terminal and no ⌘V came within `pasteGrace`.
10. **W16 — reset the caret latch** at the end of `AppDelegate.deliver`.
11. **W17 — whatever rescue survives step 2** takes only fresh rows (`startedAt` ≤ 60 s, not in the
    outbox).
12. **W18 — resync the pair** from `keyState` after `rebuildTap` / heal / Secure Input end (`HotkeyTap`).
13. **W8 — measure, then wait out Wispr's clipboard restore.** HK10 first (20 runs, VM); if the race
    shows, `AppDelegate.pasteText` waits for a quiet `changeCount` after the row.
14. **W19 — Wispr not running.** `AppDelegate.startDictation` (flags / `offerSpawnFolders` after the
    start is accepted), `WisprFlowSource.isReady` (anchored main executable), the tap's F6 path
    (`isReady`), `AppDelegate.setEngine` (readiness flash).
15. **W20 — corpus row carries both devices** (`VoiceCorpus` write for Wispr; `/test/state`).
16. **W22, W23** (language, Scratchpad column, markerClock, ms WAV name), then **W21** (one clock).

---

## 3 · Întrebări pentru Victor

Comportamentul corect nu e scris nicăieri în jurnal (sau jurnalul spune altceva decât pare
evident). Răspunsurile deblochează W3, W4, W5, W7, W9–W12.

**Q1 — Wispr eșuează, dar a fost vorbire (W3).** Relay-ul are WAV-ul tău înregistrat în paralel
(uneori pe alt microfon decât Wispr). Azi se aruncă. Ce facem?
- A) fallback automat pe modelul local, cu regula Q8/Q13 (doar ≥ 1,5 s voiced), livrat unde mergea
  propoziția, marcat `via: local-fallback`; pozele merg cu textul.
- B) doar *Recover*: WAV păstrat 5 min + flash; pozele așteaptă cu el, nu pleacă singure.
- C) ca azi (pierdut; pozele pleacă singure la agent).
- **Recomand A** (e exact ce face ElevenLabs), iar rândul Wispr se marchează „preluat" ca să nu
  dubleze o livrare târzie.

**Q2 — Rândul Wispr termină după 30 s (W12).** Fallback-ul lui Wispr durează 24–36 s; `error` vine
la ~33 s.
- A) cât timp rândul zice `processing`, relay-ul așteaptă (fără plafon, ca batch 3 §5); rândul NULL
  fără microfon renunță repede.
- B) plafonul rămâne 30 s, dar ce vine târziu se livrează oricum, marcat *late*, la destinația
  latch-uită.
- C) ce vine târziu se ține pentru *Recover* / ⌘⇧P, cu flash.
- **Recomand A**, plus B pentru ce mai sosește după o renunțare (dacă Q1 = A și fallback-ul a
  livrat deja, rândul târziu doar se loghează).

**Q3 — Propoziție Wispr nouă cât un panou de prompt e ținut / pe pauză / în editare (W10).**
- A) propoziția nouă așteaptă în spatele panoului (Q12: panourile unul câte unul, în ordine).
- B) ca azi: panoul vechi e trimis forțat.
- C) pornirea e refuzată cu flash cât panoul e în editare.
- **Recomand A.**

**Q4 — Start cât Wispr încă formatează propoziția anterioară (W9).**
- A) refuz vizibil (flash *Wispr Flow takes one sentence at a time*) — și atât.
- B) coada Q12 și pe Wispr (max 2 în zbor), fiecare propoziție cu rândul ei.
- **Recomand A acum, B după fix-ul pe rowid (pasul 3)** — azi două rânduri deschise se orbesc
  reciproc.

**Q5 — Clipboard-ul după o propoziție la caret (W5).** Jurnalul zice intenționat „nu se
restaurează — textul rămâne în clipboard ca să-l poți lipi iar". Dar înainte de firewall Wispr îți
restaura clipboard-ul, iar acum ai ⌘⇧P pentru re-paste.
- A) restaurez clipboard-ul după orice propoziție a Engine-ului la caret; ⌘⇧P rămâne re-paste-ul.
- B) ca azi (sentința rămâne în clipboard).
- C) restaurez doar la right ⌘⌥ ținut.
- **Recomand A.**

**Q6 — Ai schimbat aplicația între eliberare și sosirea cuvintelor (W7).**
- A) lipesc în aplicația care era în față la eliberare (latch ca la Q2, paste adresat pid-ului ei).
- B) dacă fața s-a schimbat, nu lipesc: țin propoziția, cu hint ⌘⇧P.
- C) ca azi, unde e caret-ul acum (cum face și Wispr).
- **Recomand A** (B dacă aplicația aceea a dispărut) și, oricum, 🔽 → nu apasă niciodată Return
  într-un prompt de shell.

**Q7 — Propoziția ta right ⌘⇧ se termină cât rândul relay-ului e încă în lucru (W4, rest).** ⌘V-ul
nu spune al cui e.
- A) relay-ul ia rândul tău și îl lipește la caret, exact unde l-ar fi lipit Wispr.
- B) îl lasă în History-ul Wispr, cu flash „⌘⌃W lipește ultima transcriere".
- C) ca azi (pierdut tăcut).
- **Recomand A.**

**Q8 — Wispr rece: primele 0,3–6 s nu le aude, dar chip-ul zice Listening (W11).**
- A) chip-ul zice *Opening…*, fără inel care respiră, până se deschide microfonul lui Wispr.
- B) A + începutul lipsă transcris local din WAV-ul relay-ului și lipit în față (cusătură, complex).
- C) ca azi.
- **Recomand A.**

**Q9 — Doar dacă testul TW1 arată că Wispr nu ia fn ⌃ Space cât ții ⌘⌥ apăsate (W1).**
- A) pe Engine = Wispr, right ⌘⌥ merge pe modelul local (sau ElevenLabs), nu pe Wispr.
- B) right ⌘⌥ refuză cu flash pe Engine = Wispr.
- **Recomand A.**

**Q10 — Wispr „învață" din textbox-ul greșit (W23).** 3001 rânduri `dictated_text_not_found` în
septembrie, cu auto-learn pornit.
- A) opresc auto-learn în config-ul Wispr.
- B) mă uit întâi în dicționarul sincronizat.
- **Recomand B**, apoi A dacă e gunoi acolo.

**Q11 — ⌘⇧P / ⌘⇧T / ⌘⇧4 tastate cu mâna dreaptă pornesc Wispr (W23).**
- A) las așa, număr rândurile goale o săptămână.
- B) mut ptt-ul lui Wispr pe altă combinație.
- **Recomand A.**

---

## 4 · Harness hooks and the case outline

### 4.1 Hooks, merged (A: H1–H6 · B: §4 1–5 · C: §4 · D: GW1–GW6)

`/test/tap {"kill": …}` (C) **exists now** (unschedule / invalidate / disable / secure) — not listed
again.

| id | route (suggested) | merges | what it does | for |
|---|---|---|---|---|
| HK1 | `POST /test/wispr-row {"op":"insert"｜"set","status","text","speechDuration","micDevice","startedAt","afterMs"}` + env `WT_WISPR_DB=<path>` | A-H1, B1, D-GW1 | process-local fake `History` rows for desk runs; `WT_WISPR_DB` + `tools/wispr-fake-db.py` only for a doctored schema copy | W2, W3, W4, W12, W14, W17 |
| HK2 | `POST /test/wispr-proc {"signal":"stop"｜"cont"｜"kill"｜"relaunch","afterChordMs","forMs"}` · `{"fake":{"main":bool,"helper":bool}}` | A-H2, D-GW2, B1's `WT_WISPR_FAKE_PID` | real signals on Wispr's anchored main pid (VM), or a faked `isReady` / main pid (desk) | W3, W6, W19 |
| HK3 | `GET /test/state.wispr` += `truth{micOpen,newestRow{rowid,status,startedAt,speechDuration}}`, `captureRow`, `lastRow`, `lastDeliveredRow`, `meter{recording,url,device}`, `owned{rowid,since,releasedAt}`, `injectionArmed`, `speculative`, `sawCmdV{rowid,msAfterClose}` | A-H3, B3, C (`sawCmdV`, `wisprRelayOwned`, `injectionArmed`), D-GW5 | relay belief vs Wispr's truth in one read | W2, W3, W4, W6, W13, W20 |
| HK4 | `POST /test/wispr-paste {"via":"tap"｜"source"}` | B2 `injectCmdV`, C `unclaimedPaste`, D-GW3 | a ⌘V attributed to Wispr: through the tap's firewall decision, or straight into `injected(from:)` | W4, W13, W17, W22 |
| HK5 | `POST /test/wispr {"relayStopOnly":true}` · `{"postOnly":true}` | A-H4 | a lost stop / an extra toggle, deterministically | W6 |
| HK6 | `POST /test/wispr {"captureTimeout":s,"speculativeGrace":s}` | B4 | desk runs without 30 s sleeps | W2, W12 |
| HK7 | `POST /test/clock-skew {"wallSeconds":n}` | A-H5 | fake a sleep on the wall-clock windows | W21 |
| HK8 | `POST /test/modifiers {"hold":["rcmd","ropt"｜"rshift"],"seconds":n,"stamped":bool}` | A-H6, C `/test/modifiers`, D-GW6 | a held right-hand pair with device bits (right ⌘⇧ = his Wispr ptt); `stamped:true` = the unit variant | W1, W4, W6, W18, W23 |
| HK9 | `POST /test/wispr-mic {"open":bool}` | D-GW4 | override `wisprMic.sampleIsRunningInput` | W6 |
| HK10 | `GET /test/state.pasteboard` | C | `changeCount` timeline during a capture (writer, time, length, sha1 — never the text) | W5, W8 |
| HK11 | `GET /engine.wisprShortcuts` | C | Wispr's `ptt` / `popo` from `config.json` beside the flag, with a mismatch flag | W15 |
| HK12 | `POST /test/front {"bundle","afterStopMs"}` | C | activate an app N ms after the close | W7 |
| HK13 | `tools/wispr-net.sh block｜delay <s>｜clear` + recipe in `docs/vm-lab.md` | B5 | `pfctl` / `dnctl` on Wispr's API hosts in the guest: `processing`, `error`, fallback-ASR and late rows on demand | W3, W12 |

### 4.2 D's `cases_wispr.py` outline, mapped onto W numbers

| case | was | now | note |
|---|---|---|---|
| TW1 | W-D1 | **W1** | VM; also decides Q9 |
| TW2 | W-D1 | **W1** | desk unit, HK8 `stamped` |
| TW3 | W-D1 (standalone off) | **W15** | retire with Q9 step 2 (the flag goes); replace by the HK11 mismatch check |
| TW4 | W-D2 | **W11** | VM, cold Wispr |
| TW5 | W-D2 | **W11** | desk, documents the chip today |
| TW6a–d | W-D3 | **W3** | assertions follow Q1's answer |
| TW7 | W-D3 | **W3** (+W19) | desk, HK2 `fake` |
| TW8a–b | W-D4 | **W4** | VM; (b) after step 3 expects no swallow at all in the tail |
| TW9 | W-D5 | **W6** | VM, HK8 right ⌘⇧ + ⌘⌃D |
| TW10 | W-D6 | **W6** | VM, cold Wispr |
| TW11 | W-D7 | **W4** | standalone-off run; after step 2 rewrite as a relay 🔽 during the settle |
| TW12 | W-D7 | **W4** | desk, HK1 |
| TW13 | W-D8 | **W10** | desk + VM; assertions follow Q3 |
| TW14 | W-D9 | **W9** | assertions follow Q4 |
| TW15 | W-D10 | **W19** | |
| TW16 | W-D10 | **W19** | |
| TW17 | W-D11 | **W20** | |
| TW18 | W-D12 | **W23** | **drop**: the one-way menu is by design |
| TW19 | engine switch | — | keep as a regression guard, no finding |
| TW20 | Wispr quit mid-sentence | **W3** | |
| TW21 | markerClock leak | **W23** | |

**Cases the merge adds** (no TW yet):

| case | W | hooks | shape |
|---|---|---|---|
| TW22 | W2 | HK1, HK6 | desk: NULL row that never moves → `isRecording` false by the grace, a flash, no 30 s `transcribing`; re-press variant adopts the newer row |
| TW23 | W5 | HK8, HK10 | VM: sentinel on the clipboard, held right ⌘⌥ at the caret → `pbpaste` per Q5 |
| TW24 | W7 | HK12 | VM: release in TextEdit, Terminal to front at +300 ms → per Q6; never a Return at a shell prompt |
| TW25 | W8 | HK8, HK10 | VM ×20: TextEdit never contains the sentinel |
| TW26 | W12 | HK1 + HK6 (desk) / HK13 32 s (VM) | row `formatted` after the timeout → per Q2, never the "already delivered" line |
| TW27 | W13 | `/test/tap {"kill":"secure"}` | one copy per place + the *not caught* flash |
| TW28 | W14 | HK1 `WT_WISPR_DB` doctored copy | flash + firewall opened, Wispr's paste passes |
| TW29 | W16 | HK4 `source` | caret sentence, then a rescued one while bound → terminal, not the caret |
| TW30 | W18 | HK8 + `/test/tap {"kill":"unschedule"}` | release inside the kill → the sentence ends at the release |
| TW31 | W21 | HK7 | 12 min skew during a `processing` row → no paste in the front app |
