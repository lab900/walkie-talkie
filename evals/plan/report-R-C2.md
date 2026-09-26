# Test plan run — 2026-09-26 18:32

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 15

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TL14 | **PASS** | 33 | blackhole (fake timeout after 20 s): failure at 20±1 s, no retry, 'still uploading — 8 s in', fallback delivers | failure 20.0 s after stop, retries 0, 'still uploading — 8 s in' True, via local-fallback (the fake's delay, not URLSession's own timeout — G13 for that) |
| TL16 | **PASS** | 8 | 3 s of silence → 'returned no words', the WAV kept for Recover, nothing delivered (fixed 2026-09-26, §3.8: an empty answer is `.failed(heardNothing)` with the audio, no local fallback; the BUG branch is the old loss) | no-words line True, ↪️ False, audio kept True, recoverable True, delivered False |
| TL29 | **PASS** | 16 | live socket drop mid-sentence (fault live:drop) → ≤ 1 'send failed' line (today ~11/s); batch still delivers | drop injected True, 1 'send failed' lines (~0.1/s over ~8 s), batch via elevenlabs-scribe |
| TL30 | **PASS** | 12 | live socket that never opens (live:never-open stands in for no key) → the band never opens, `pending` stays ≤ 64; the batch delivers (was: band open and empty the whole sentence, `pending` unbounded — §3.14, F13) | band open 0/26 samples, max words 0, socket {'connecting'}, pending [0] → [64], batch via elevenlabs-scribe |
| TL32 | **PASS** | 8 | normal cancel keeps the audio: 'N s of audio kept', one cancelled-*.wav | 'audio kept' 5.8 s, recoverable cancelled-18-33-29.wav exists True, delivered False |
| TR9 | **PASS** | 12 | offline (transport ×2 + live drop) → ↪️, via local-fallback, no 'abandoned' | ↪️ True, abandoned False, via local-fallback, witness 231 chars |
| TR13 | **PASS** | 28 | empty Scribe answer on 20 s of speech → WAV staged, Recover returns it (fails today: 'returned no words', audio deleted) | 'returned no words' True, staged cancelled-18-34-07.wav (22.772171020507812 s), Recover via test |
| TR23 | **PASS** | 21 | three more chords during the settle (within 0.5 s) → no new dictation, one delivery | new microphones after the stop 0, deliveries 1, recording at the end False |
| TR24 | **PASS** | 19 | bind B during the settle → the words go where the latch said at the stop (A); R11 predicts they follow the bind | A (ttys036) 231 chars, B (ttys037) 0 chars, delivery to terminal:ttys036 |
| LC13 | **PASS** | 12 | live integration: band words > 0 while isRecording; the band closes when listening goes false | max band words while recording 9; after stop: listening false at 0.071 s, band closed at 0.071 s |
| B1 | **PASS** | 11 | first live caption word ≤ 2 s after speech starts in the recording (plan: ≤ 1.5 s) | first band word 1.62 s after the speech in the recording (onset 1.84 s into it); 2.48 s by the old clock (play() + 0.5); warm socket (open 6 s); chunks 34 |
| B2 | **PASS** | 12 | a VAD commit → '💬 live correction: … → scribe_v2', live.corrections ≥ 1, elevenCost.total grows, band corrections ≥ 0 | correction started True, applied True (0.76 s), live.corrections 1, cost 0.31784 → 0.31822, band corrections 3 words 11 |
| B3 | **PASS** | 18 | stop while a correction is in flight (500 after 4 s, then the real retry) → no update after close, no crash (pid unchanged), the sentence delivers | fault taken True, retry after close True, correction applied after close False, pid 96476 → 96476, delivered via elevenlabs-scribe (no discard line exists in the code) |
| B4 | **PASS** | 18 | correction failure (500 ×2, the call and its retry) → 'after 5 s' hold, cut unchanged, the next upload ≥ 5 s later covers the longer span | hold 5.47 s, cut after the failure 0, spans [6.5, 12.7] |
| B5 | **PASS** | 12 | elevenCost.total grows by (live s × 0.39 × (1 + 0.2 with keyterms) + batch s × 0.22)/3600 (±25 %) | Δ $0.001732 vs expected $0.001749 (recording 7.2 s, corrections 6.1 s, keyterms 50); label $0.32 → $0.33 |
