# Wispr markers — which spoken phrase does Wispr Flow reliably write down?

Scheduled brief, started unattended on 2026-09-30 at 20:00 (one-shot LaunchAgent
`ro.victorrentea.wt-wispr-markers`). You are an interactive Claude Code session in tmux; nobody is
watching. Work alone, in the VM, and leave a report.

## Why

Victor, 2026-09-30 (dictated): *"Pe Wispr Flow nu poți să inserezi markeri audio în text … Teoretic,
ar fi posibil. … o investigație despre cum aș putea să inserez în WAV-ul pe care îl dau către Wispr
Flow o secțiune care să … rezulte întotdeauna în mod reliable în, de exemplu, „image". Sau …
„Screenshot!" Experimentează diverse fraze pe care le putea insera în WAV, ca Wispr Flow să le
poată traduce. Exact cum face 11 Labs, practic. Nu, 11 Labs … folosește timestamp-urile cuvintelor
produse. Wispr Flow nu-mi dă chestia asta."*

With ElevenLabs a 📸n token lands where he pressed the shutter, from the word timings. Wispr gives
text only, so today every picture goes to the footer with a clock (`[📸2 at 0:08 = …]`). If a
phrase spliced into the audio Wispr hears comes back in its text **every time, recognisably, and
nowhere else**, the relay can replace it with the token in place.

## Read first (do not re-derive what is measured)

- `Sources/WalkieTalkie/ShotMarker.swift` — the marker that already exists: `screenshot one` …
  `ten`, `selected text N`, `picked element N`, TTS clips, `resolve`. `WisprFlowSource.mark` splices
  it into the stream Wispr is fed (`AudioBridge`, `MicRecorder.insert`) when the bridge is up.
  Its doc says it was measured on Wispr on 2026-09-14 (twice out of two), and the rules say spoken
  markers were **retired 2026-09-18** (`WT_SHOT_MARKERS=1` revives them) — played *over* his voice
  they were masked, and Scribe heard `Pict element one`. Find both in `docs/journal.md` and start
  from them: the splice (not the overlay) is the path now, and the question is *reliability at
  scale*, not *can it*.
- `evals/marker-phrases.py` — the same question asked of the local Whisper; reuse its `say` /
  splice / gap-finding code rather than writing new.
- `.claude/rules/dictation-source.md` (the Wispr firewall, `History` row, markers).
- `docs/vm-wispr.md` (*Done 2026-09-28* and after) and `docs/vm-lab.md` — how Wispr runs in the
  `wt-lab` guest: BlackHole as its microphone, **`tart exec` for anything that must hear audio**
  (SSH has no microphone grant — exact zeros), `open -b com.electron.wispr-flow`, reading rows out
  of Wispr's `History` table. `tools/wispr_loop.py`, `tools/wispr_loopback.py` are the harness.

## What to measure

Base audio: Victor's real dictations from `~/.walkie-talkie/voice-corpus/` (both Romanian and
English ones; pick ~10 of 10–40 s). Splice a candidate marker into a pause (and, as a harder case,
mid-phrase), play the result into the guest's BlackHole with Wispr's push-to-talk held, read the
row. Per candidate × position × language:

1. **recovered** — the marker is findable in `formattedText` by a regex you would ship (tolerate
   `Screenshot 1.`, `screenshot one,`, casing, a trailing full stop, digits vs words);
2. **index right** — `two` stays 2 (up to 10; also two markers back to back);
3. **in place** — lands between the same two words it was spliced between;
4. **no damage** — the words around it unchanged against the same clip without the marker;
5. **no false positives** — run the regex over Wispr's text of the un-spliced clips and over
   Victor's real History rows (host DB is read-only to you; copy it, never open it live).

Candidates, at least: the current `screenshot one`; `image one`; `picture one`; `snapshot one`;
`Screenshot!` alone (index from order); `marker one`; a NATO-style `photo alpha`; a coined word
(e.g. `walkieshot one`) **with and without** an entry in Wispr's custom dictionary in the guest
(Wispr's dictionary may be exactly what makes a coined word reliable — check its config for how
entries are stored; `shouldAutoLearnWords` is false in the guest). Several `say` voices, rates and
levels; a short tone before the phrase if you want a separator. Add your own ideas.

Budget: every row is a Wispr cloud call. Keep it to roughly 300 clips; stop early if a candidate is
clearly perfect or clearly dead.

## Rules

- **VM first.** The VM is taken while `~/.walkie-talkie/scheduled/wt-lab.busy` exists **or**
  `tart list` shows `wt-lab` running (re-check every 10 min; use it as soon as it is free).
  Tonight the `evals/wispr-catchup/` job may hold it from 19:30 and hands it over by 21:30.
- **If the VM is taken, you may use this Mac itself** (Victor, 2026-09-30 19:57: *"If the VM might
  be taken by the other session, feel free to use the current hard physical machine itself."*).
  Then these hold, all of them:
  - **Only while he is away**: `ioreg -c IOHIDSystem` `HIDIdleTime` ≥ 10 min **and** the host relay's
    `GET /test/state` → `busy` false. Re-check before **every** clip; the moment either fails, stop,
    put everything back and wait (at 11:47 today a desk test cancelled his sentence and posted a
    stray Return — `docs/journal.md`, *On Wispr the prompt starts with his words*).
  - Wrap the whole host session in `~/bin/hands-off start "<what and why, in words he understands>"`
    … `hands-off end` (see `~/.claude/CLAUDE.md`); his double-click on the 🔒 is a stop — obey it.
  - **Wispr may paste nothing into his apps.** Drive sentences through the relay's own routes
    (`desk-testing.md`) so the firewall swallows Wispr's ⌘V, with the relay bound to a throwaway
    Terminal tab running `cat > /dev/null` (as `evals/test_envelope.py`'s `_nowhere()` does), and his
    previous binding restored at the end. Feed audio into **From Walkie** (what Wispr listens to —
    `../from-walkie`'s `feed-player`), never out of the speakers.
  - Never restart the host relay or Wispr, never change Wispr's settings or dictionary on the host
    (the custom-dictionary arm is VM-only), never delete History rows. Keep test runs from teaching
    the real timing/corpus lines (`desk-testing.md`, `fake`/`test` switches); list the History rowids
    you created in the report so the corpus harvest can exclude them.
- That job leaves a **BlackHole 16ch** installed in the guest. Before your first clip, check which
  input Wispr's Auto-detect picked (the row's `micDevice`); if it is not `BlackHole 2ch`, pin Wispr
  back to it — your clips play into BlackHole 2ch. Leave the 16ch driver installed.
- `wt-lab` is the never-clone VM: no `tart clone`, no reset, no delete. Stop it when you are done.
- No app source changes tonight — this is research. A recommendation (phrase, regex, splice point,
  level) goes in the report.
- Git: stage your own files by explicit path (never `git add -A`, never `git stash` — other
  sessions share this tree), commit, push.

## Deliverable

`evals/wispr-markers/README.md`: the table (candidate × recovered / index / in place / damage /
false positives, with n), what surprised you, the recommendation, and the exact commands to re-run.
Raw rows in `evals/wispr-markers/results.jsonl`, the driver as `evals/wispr-markers/run.py`. A
short dated section in `docs/journal.md` pointing at it. Then shut the VM down and exit.
