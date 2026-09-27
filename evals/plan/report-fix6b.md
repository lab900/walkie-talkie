# Test plan run — 2026-09-27 08:04

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

FAIL 5 · PASS 12

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TL15 | **PASS** | 58 | a slow upload (45 s) keeps the settle up past the old 30 s ceiling — it waits while the recogniser works (2026-09-26, item 5) — and both start gestures refuse while the words are in flight, saying so; the late reply lands in the latched terminal (since Q12, batch 6: both gestures START the next sentence, queued; the late reply still lands). Before: the settle gave up at 32 s, forward-click refused, forward-right started a sentence the late reply then landed in | queue on · eleven-live: at 33 s after the stop settling=True phase=transcribing/uploading; forward-click STARTED, forward-right STARTED; late reply landed, lastDelivery.to=terminal:ttys000 (bound ttys000); invariants ok |
| TL18 | **PASS** | 29 | the restart gate blocks while audio is staged for Recover; today: --dry-run opens (busy:false) and a restart would wipe cancelled/ | staged 5.8 s; busy=True busyWhy=['audio staged for Recover (300 s left)']; dry-run exit 3 after 20.4 s (⛔️ still waiting for the sentence in flight: audio staged for Recover (279 s left) after 20 s — gave up (--max-wait 20); nothing was restarted); recoverable still set=True |
| TG7 | **PASS** | 64 | the same 🔽/🔽→ pair on Engine = wispr stops Wispr's sentence at +60 ms and at +500 ms (the arm is set on the tap thread — the asymmetry with T-G6) | +70 ms: stop branch=True, sink [] · +502 ms: stop branch=True, sink [] · Wispr closed after each: True/True · sent back-click@0.001s back-right@0.071s back-click@31.671s back-right@32.173s |
| TG29 | **PASS** | 59 | `sessionFlags == []` within 300 ms after every gesture and after the app's own posters (`postReturn` via 🔽→ at idle; `postWisprHandsFree` / `postWisprCancel` when Wispr runs) | 13 steps, every one bare within 300 ms · postWisprHandsFree exercised; postWisprCancel not reached (🔽← took the relay-cancel branch); Wispr closed=True · sent back-right@0.000s forward-left@0.718s back-down@1.443s forward-down@2.165s forward-click@2.896s forward-right@3.251s forward-up@3.773s back-up@4.601s back-click@5.456s back-left@6.280s postWisprHandsFree (start)@6.737s back-left@7.248s postWisprHandsFree (stop)@12.331s |
| TG40 | **FAIL** | 16 | 🔽 in the settle of a relay prompt says the words are in flight (or nothing). Predicted defect: the misleading `Back click ignored — finish the sentence you are dictating first` banner. Since Q12 (batch 6, `state.sentenceQueue`): it starts the next plain sentence, no refusal | queue on · refused line=False (before the delivery=False), 'words still in flight' line=True, state just after: listening=False settling=True, a new sentence opened=False · sent forward-right@3.706s forward-right@10.115s back-click@10.231s |
| TL16 | **FAIL** | 12 | 3 s of silence → 'returned no words', the WAV kept for Recover, nothing delivered (fixed 2026-09-26, §3.8: an empty answer is `.failed(heardNothing)` with the audio, no local fallback — Q8: under 2 s voiced; the BUG branch is the old loss) | no-words line False, ↪️ True, audio kept False, recoverable False, delivered True |
| TL29 | **FAIL** | 17 | live socket drop mid-sentence (fault live:drop) → ≤ 1 'send failed' line (today ~11/s); batch still delivers | drop injected False, 0 'send failed' lines (~0.0/s over ~8 s), batch via local-fallback (the socket never opened, so the drop never fired) |
| TL30 | **PASS** | 14 | live socket that never opens (live:never-open stands in for no key) → the band never opens, `pending` stays ≤ 64; the batch delivers (was: band open and empty the whole sentence, `pending` unbounded — §3.14, F13) | band open 0/27 samples, max words 0, socket {'connecting'}, pending [0] → [64], batch via local-fallback |
| TR13 | **PASS** | 30 | empty Scribe answer on 20 s of speech → (Q8, batch 6) ≥ 2 s voiced, so the local model stands in and delivers it; before batch 6: WAV staged, Recover returns it | 'returned no words' on speech → local fallback delivered via local-fallback (Q8) |
| LC13 | **FAIL** | 12 | live integration: band words > 0 while isRecording; the band closes when listening goes false | max band words while recording 0; after stop: listening false at 0.083 s, band closed at 0.083 s |
| B1 | **FAIL** | 15 | first live caption word ≤ 2 s after speech starts in the recording (plan: ≤ 1.5 s) | could not place the speech — first band word None s after the speech in the recording (onset 1.8 s into it); None s by the old clock (play() + 0.5); cold, caught up 1 chunk(s) at session open; handshake 0.27 s (upgrade 0.27 s) on its own URLSession; chunks 17 |
| Q1 | **PASS** | 22 | a start while the last sentence transcribes opens the microphone (it used to be refused: batch 3); state.sentences lists 2; both sentences delivered, the first first | second microphone opened=True, parked line=True, sentences listed=2, delivered 2 (first is A=True) |
| Q2 | **PASS** | 28 | with two sentences in flight a third start is refused: the `two sentences are already in flight` line and the flash, no third microphone; both still delivered | refused line=True, a third microphone opened=False, sentences listed=2, both delivered=True |
| Q3 | **PASS** | 25 | the second sentence lands first (the first's upload `delay` 9 s): it waits (`landed before`), and the outbox/witness get A then B | B waited=True, outbox order=['A', 'B'], witness has A=True |
| Q4 | **PASS** | 52 | 🔼← while B records and A transcribes cancels B (the recording), and A is still delivered | cancel line=True, delivered 1 row(s), A only=True |
| Q5 | **PASS** | 61 | 🔼← with nothing recording and two in flight cancels the most recent (B, disowned), A delivered | cancel line=True, delivered 1 row(s), A only=True |
| Q6 | **PASS** | 21 | Autosend off: the panels come one at a time, in order — A's panel first while B waits (`waits for the prompt panel`), B's after A's is sent (POST /test/prompt send) | first panel is A=True, B waited=True, second panel=True, outbox order=['A', 'B'] |

## Notes (2026-09-27 morning, batch 6 + voice affect installed)

ElevenLabs credits exhausted all run (`HTTP 401 quota_exceeded`, the live socket `quota_exceeded`
right after `session_started`); every batch upload fell back to the local model. Run with
`HANDS_OFF=1` under `hands-off`; TL15/TL16/TL18/TR13 added to the brief's list (gesture-tagged, so
they SKIP without the locks).

- **B1 — quota.** The socket opens (handshake 0.27 s, upgrade 0.27 s — Q11's new lines work) and
  is closed by the server with `quota_exceeded`: no band word to time.
- **LC13 — quota.** Same: 0 band words while recording.
- **TL29 — quota.** The socket never stayed open, so the `live:drop` fault had nothing to drop.
- **TL16 — quota.** 3 s of silence: the batch call answered 401 (not an empty answer), which is an
  ordinary failure → local fallback → 14 chars delivered to the witness. Q8's 2 s voiced floor
  guards only the *empty-answer* path; a transport/HTTP failure on silence still reaches the local
  model (and its hallucinations). Worth a look once credits are back.
- **TG40 — case contradicted Q12, fixed.** The back click came 0.12 s after the stop, inside
  Q12's 0.8 s double-click guard (`queueStartAfterStop`), so it was refused with *words still in
  flight* — correctly. The case now waits 1 s with `state.sentenceQueue`: `report-fix6c.md` PASS.
- **TL18** BUG → PASS, **Q1–Q6** PASS (new), **TL15 / TL30 / TR13 / TG7 / TG29** PASS as before.
