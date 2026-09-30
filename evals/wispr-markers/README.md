# Wispr markers — which spoken phrase does Wispr Flow reliably write down? (2026-09-30)

**Verdict: a marker in Victor's own voice works, and a synthetic one does not.** Spliced into a pause
of his dictation and read out of Wispr's **`asrText`**, `screenshot N` came back with the right
number, in place, **37 of 40** times. It came back **20 of 20** when two were back to back.
Every `say` voice lost between a quarter and all of its markers, most of them inside English
sentences. Wispr's recogniser often ignores a second speaker, and its formatter then deletes, moves
or rewrites a good part of what the recogniser did keep. Hence the recommendation:
- his recorded clips, spliced at his **next pause**;
- found in `asrText` and carried into `formattedText` by word alignment;
- replaced only when **every** marker is back, otherwise today's footer.

Brief: `PROMPT.md`. Driver: `run.py`, guest half: `guest.py`, raw rows: `results.jsonl` (one per
Wispr call).

## How it was measured

- **Base audio:** ten of Victor's real dictations, 14–25 s, five Romanian and five English, all from
  `~/.walkie-talkie/voice-corpus/`. None of them says a candidate word (`run.py` `BASES`).
- **Two markers per clip, spliced in as `MicRecorder.insert` does:** 16 kHz mono int16, butted in
  with no padding, at the loudness of his voice (active RMS).
  - One goes into a **pause**: the middle of a silence of at least 0.24 s, near 40 % of the clip.
  - One goes **mid-phrase**: a word boundary with no pause, at least 3 s away from the first.
  - Numbers vary per clip, so every index from 1 to 10 appears in both positions.
- **Into Wispr:** `wt-lab`, Wispr 1.6.957 with Auto-detect set to BlackHole 2ch (every row says so).
  Each clip is one `tart exec` of `guest.py`, which plays into BlackHole 2ch with Wispr's own push
  to talk held (`wispr_loopback.dictate`: 1.3 s lead-in, 0.5 s tail, peak 0.5) and reads the new
  `History` row. The guest relay's bridge is switched off first. Played in real time, with no
  catch-up pacing.
- **Baselines:** each base clip unspliced, twice (Wispr's own run-to-run noise).
- **Scoring** (`run.py score`):
  - **Recovered:** a regex a relay would ship (`PATTERNS`) finds the marker. It accepts casing,
    punctuation, `number`/`#`, and digits or English/Romanian number words.
  - **Index:** the number is right.
  - **±1 word:** it sits within one word of where it was spliced, in Wispr's formatted baseline.
    The position comes from local Whisper word timings on the base clip, aligned to Wispr's words.
  - **Damage:** the three words either side of that point differ from the baseline.
  - **Anchor:** the marker is found in `asrText`, and its position is carried into `formattedText`
    by aligning the two with the markers removed. It counts when that lands within one word.
  - **Clean clip:** every marker of the clip comes back, each number once and in splice order, with
    nothing extra. This is the all-or-nothing rule Victor asked for (see *Recommendation*).
- **Volume:** 221 rows in the VM plus a probe, 5 rows dropped (two drivers played into the device
  at 21:02–21:03; see *Surprises*), and 3 host rows. About 230 Wispr calls.

## The table

`run.py score --summary`, 20 markers per candidate (40 for the doubled ones). `f/i/±1` means
found / number right / within one word. The clean-clip columns count clips.

| candidate | clips | markers | formatted f/i/±1 | asrText f/i | anchor ±1 | clean clips (formatted) | clean clips (asr + anchor) |
|---|---|---|---|---|---|---|---|
| **his voice** `screenshot N` | 20 | 40 | 35 / 35 / 33 | **37 / 37** | **37** | 10/20 | **14/20** |
| **his voice**, two back to back (N, N+1) | 10 | 20 | 20 / 20 / 19 | **20 / 20** | **20** | 7/10 | 7/10 |
| his voice `picked element N` | 10 | 20 | 16 / 14 / 13 | 19 / 17 | 17 | 5/10 | 7/10 |
| his voice `selected text N` | 10 | 20 | 18 / 14 / 13 | 18 / 14 | 14 | 4/10 | 5/10 |
| `say -v Daniel` `screenshot N` | 10 | 20 | 15 / 15 / 14 | 17 / 17 | 17 | 4/10 | 7/10 |
| `say` Samantha, 1 kHz blip + `screenshot N` | 20 | 40 | 22 / 22 / 21 | 26 / 26 | 26 | 7/20 | 12/20 |
| Samantha `snapshot N` | 10 | 20 | 13 / 13 / 11 | 14 / 14 | 14 | 3/10 | 6/10 |
| Samantha `screenshot N`, rate 150 | 10 | 20 | 11 / 11 / 11 | 13 / 13 | 13 | 4/10 | 6/10 |
| Samantha `screenshot N`, +6 dB | 10 | 20 | 12 / 11 / 10 | 13 / 12 | 12 | 2/10 | 4/10 |
| Samantha `marker N` | 10 | 20 | 10 / 10 / 10 | 12 / 12 | 12 | 3/10 | 4/10 |
| Samantha `screenshot N` (the shipped TTS) | 10 | 20 | 8 / 8 / 8 | 11 / 11 | 11 | 2/10 | 5/10 |
| Samantha `picture N` | 10 | 20 | 9 / 9 / 8 | 11 / 11 | 11 | 2/10 | 4/10 |
| Samantha `screenshot N`, 0.3 s of silence around | 10 | 20 | 11 / 11 / 9 | 11 / 11 | 11 | 2/10 | 4/10 |
| Samantha `image N` | 10 | 20 | 5 / 5 / 4 | 6 / 6 | 6 | 1/10 | 2/10 |
| Samantha `photo alpha…juliet` | 10 | 20 | 5 / 5 / 5 | 5 / 5 | 5 | 1/10 | 1/10 |
| Samantha `Screenshot!` alone (index from order) | 10 | 20 | 5 / – / 5 | 6 / – | – | 0/10 | 0/10 |
| Samantha `walkieshot N` (coined), no dictionary | 10 | 20 | 0 | 0 | 0 | 0/10 | 0/10 |
| the same, **with** `walkieshot` in Wispr's dictionary | 10 | 20 | 0 | 0 | 0 | 0/10 | 0/10 |

**By position**, for his `screenshot N`:
- **In a pause:** formatted 19/20, `asrText` 19/20. The one miss is a row where Wispr lost both
  markers and misheard the whole sentence (`lcrezesc`).
- **Mid-phrase:** formatted 16/20, `asrText` 18/20.
- Mid-phrase splices also cut the word they land in: `sunt de vreo trei- Screenshot eight. Sute de
  mii` (`trei sute` split in two).
- For every TTS candidate the mid-phrase column is far worse. For example Samantha
  `screenshot N` inside English sentences: 0/5 in the formatted text.

**Damage**, the three words either side of the marker, his `screenshot N`:
- different from the baseline in 16/40 markers, against 2/40 between Wispr's own two baselines;
- Wispr rewrites the clause a marker sits in, e.g. `This one should not` became `(this one) should not`;
- this is one reason not to trust `formattedText` for the position.

**False positives:**
- **In the 20 baseline texts:** zero, for every regex.
- **In Victor's real `History`:** a copy of the host `flow.sqlite` (15 761 rows with text), read only.
  - The one genuine hit: `screenshot` → *"I could **screenshot three** times"* (2026-07-08). The
    all-or-nothing count check would keep it, unless exactly three markers were spliced in that
    same sentence.
  - `image`: *"screenshot repeated **images one** after the other"*.
  - `picture`: two hits, both him talking about these markers on 2026-09-14.
  - `snapshot`, `marker`, `photo-nato`, `selected text`, `picked element`, `bang`: none.
  - The other 94 `screenshot` hits are the teacher batch replaying corpus clips that had markers
    spliced into them (TextEdit rows, 09-14 to 09-27). They are the same experiment in the wild,
    not false positives. They also show every shape the regex must accept: `*Screenshot one.*`,
    `**Screenshot one**`, `„Screenshot one.”`, `(screenshot 1)`, `- Screenshot one`,
    `<li>Screenshot 1</li>`, `ca în Screenshot one`.

## What surprised me

1. **Wispr's recogniser drops a synthetic voice.** Not a regex or formatting problem: the TTS
   marker is simply absent from `asrText` in about half the clips, and in almost all English ones.
   One base clip (`09-12-47`, English) lost every Samantha marker in every candidate. Louder
   (+6 dB), slower (rate 150), padded (0.3 s) or behind a blip: none moved it much. A male voice
   (Daniel) did, from 11 to 17 of 20. His own voice is 37/40: a recogniser keeps the speaker it
   is transcribing. This is the same finding `ShotMarker.recorded` made on the local Whisper
   (16/18 against 7/18).
2. **The formatter takes markers out of `asrText`.** In the raw text but not the formatted:
   - `Image six.`, `Picture six.` and a mid-phrase `should not screenshot one have been` were
     deleted outright.
   - `Image nine` was moved to the end of the sentence.
   - `the arrows screenshot ten head` became *"the arrows **in screenshot 10** tend to move"*.
   - `stay screenshot five put` became *"stay put, **as in screenshot 5**"*.
   - `marker ten` was swallowed into *"the arrow marker's head"*.

   Position must come from `asrText`.
3. **Four of his 30 recorded markers are mis-cut** (`~/.walkie-talkie/markers/`, cut 2026-09-15):
   - `screenshot-3.wav` (4.9 s) says *"screenshot 3 … screenshot 4"*;
   - `selected-text-6.wav` says *"…6. Selected text 7"*;
   - `selected-text-8.wav` says *"…8, selected text 9"*;
   - `picked-element-6.wav` says *"6 picked element 7"*.

   Every clip that used `screenshot-3` came back with a phantom `Screenshot four`, and the count
   check caught it every time. Leaving out the clips that used index 3, his screenshot markers
   were clean **20 of 22 clips** via `asrText`. Of the two failures:
   - one is the row where Wispr lost everything;
   - the other came back as `screenshot fourth`. An ordinal is not accepted, deliberately
     (*take the screenshot first*).

   The index errors in `selected text` / `picked element` are these files, plus his `three` /
   `four` / `ten` heard as `tree` / `for` / `then`.
4. **A coined word is worse than a real one, and the dictionary does not rescue it.** `walkieshot`
   came back as `Wakey should four`, `Wakisha seven`, `WAKISH 10`: never the word, before or after
   the Dictionary entry. The entry syncs through his account, and the guest had the host's 88 rows.
5. **`Screenshot!` alone gets absorbed into the grammar.** `indeed. Screenshot: I have to pay…`, or
   `Screenshot.` merged into the next sentence. It has no index to hold it apart, and anchoring
   cannot work without one.
6. **Two drivers at once corrupt the clip.** A debug run started while the background driver was
   still playing: Wispr's rows mixed two clips (*"…progress bar here, the same information. În
   wiki pe care le creez…"*). Those 5 rows were dropped, and `run.py drive` now takes a lock.

## Recommendation (no app change was made for this report)

1. **Voice: his own recordings, never `say`.** Re-record (or re-cut) the four mis-cut files before
   relying on indices 3, 6 and 8. `ShotMarker.synthesise` already prefers `recorded(_:)`. For an
   index he has not recorded, the Daniel voice is the least bad fallback (17/20), still well
   below his.
2. **Phrase: keep `screenshot N`, `selected text N`, `picked element N`.**
   - They survive as well as anything tried.
   - Their false-positive rate in 15 761 real rows is one sentence.
   - `ShotMarker.resolve`'s pattern already matches every shape Wispr produced here.
   - Numbers 1–10 as words or digits; no ordinals; no homophones except behind the existing
     punctuation discriminator.
3. **Splice point: his next pause.** Victor, 2026-09-30: *"I'd prefer waiting the next pause to
   insert the marker to missing the marker."*
   - Today the bridged path splices at the next buffer (`WisprFlowSource.mark`), i.e.
     mid-phrase, and that is where both the misses and the cut words are.
   - Wait for `quietSeconds ≥ gapNeeded` with no ceiling while the take is open. If the take
     closes first, splice at the close.
4. **Level:** match his voice's active RMS. +6 dB bought nothing, and padding bought nothing.
5. **Where to read it:**
   - Search the row's `asrText` for the markers.
   - Carry each position into `formattedText` by aligning the two word streams with the markers
     removed; `run.py`'s `asr_anchor` is the reference.
   - Delete whatever marker residue the formatter left in `formattedText`.

   Via `asrText` 37/40 land within one word; via `formattedText` alone 33/40.
6. **All or nothing, with the footer as the safety net** (Victor, 2026-09-30):
   - Replace the markers only when the numbers found in `asrText` are exactly the ones spliced,
     each once and in splice order.
   - Otherwise deliver today's shape: frames in the footer with `at m:ss`.
   - Always strip the marker phrases from the words; they are the relay's, not his.
   - The footer rows stay in both cases.
7. **Combine it with the catch-up pacer.**
   - A spliced marker enters the bridge through the same `schedule()` door as his voice, so its
     1.5–2 s lands in `queued`. `BridgePacer` then already reads it as lag and speeds up
     (1.1×–1.25×) and shortens pauses until Wispr hears him live again.
   - Victor asked for exactly this: *"every time you insert a bit of a clip, you speed up a bit.
     We need to catch up."*
   - One refinement: play the marker itself at 1.0× and start the catch-up after it. A marker at
     1.25× is unmeasured.

## Re-run

```sh
# host: clips (needs mlx_whisper → /usr/local/bin/python3), then phase 2 and 3
/usr/local/bin/python3 evals/wispr-markers/run.py build
/usr/local/bin/python3 evals/wispr-markers/run.py phase2
/usr/local/bin/python3 evals/wispr-markers/run.py phase3
# the guest (wt-lab never cloned; see docs/vm-lab.md)
echo "wt-wispr-markers $$ $(date '+%F %T')" > ~/.walkie-talkie/scheduled/wt-lab.busy
TART_HOME=~/tart tools/vm-lab.sh up
tar -C evals/wispr-markers -cf - guest.py clips | ssh admin@$(TART_HOME=~/tart tart ip wt-lab) \
  'mkdir -p ~/wt-lab/evals/wispr-markers && tar -C ~/wt-lab/evals/wispr-markers -xf -'
TART_HOME=~/tart WISPR_DEV="BlackHole 2ch" /usr/local/bin/python3 evals/wispr-markers/run.py drive [--phase N]
# score
/usr/local/bin/python3 evals/wispr-markers/run.py score [--summary | --detail]
/usr/local/bin/python3 evals/wispr-markers/run.py fp <a COPY of flow.sqlite>
```

The host path (`host-setup`, `host-drive`, `host-teardown`) exists, and three clips ran on it at
20:51 before its gate stopped it. It has two conditions:
- **Only while Victor is away:** `human_watch` idle for 5 minutes, the relay idle, the sink tab in
  front.
- **Not with the screen locked.** Wispr recorded `com.apple.loginwindow` as the front app, so its
  paste would aim at the lock screen, not the sink tab.

## What this run left behind

- **Host `History` rows created:** rowids **18027, 18028, 18029** (20:51, marked `"host": true` in
  `results.jsonl`, excluded from the scores). Nothing else on the host: no corpus or outbox line,
  no relay delivery. The binding, bridge and pasteboard were put back at 20:53.
- **Guest:** one Dictionary entry, **`walkieshot`** (manual, no replacement,
  id `1b26c4ca-a310-4436-87f3-3aecfc2e9313`, 2026-09-30 19:42 UTC). Victor OK'd it syncing into
  his dictionary and staying there. Backup of the guest DB before it:
  `~/Library/Application Support/Wispr Flow/flow.sqlite.bak-2026-09-30-before-walkieshot`.
  The guest `History` rows are the `row` ids in `results.jsonl`.
