# Wispr catch-up — does Wispr write down the whole sentence when it starts listening late?

Brief, started by hand on 2026-09-30 at 19:30 (Victor: "start now") in tmux
`wt-wispr-catchup`. You are an interactive Claude Code session; nobody is
watching. Work alone, in the VM, and leave a report.

## Why

Victor, 2026-09-30 (dictated): *"Yesterday we have implemented a feature which is supposed to record
the audio from the moment I open the dictation and feed it to Wispr Flow engine whenever it becomes
available, and in the meantime keep it in the buffer, and then when it is available basically pass
the missed part of the audio as a compressed sound so that it catches up with the current time, so
the final effect should be that the full clip should be transcribed by Wispr Flow. Write a bit of an
eval on this."*

The feature is commit `67cc341` (2026-09-29 09:42): `AudioBridge` holds every buffer from the
gesture until Wispr's input runs, then `BridgePacer` cuts the silence before the first word (0.3 s
pad), shortens pauses to 0.25 s and plays at 1.1× (time-pitch) while more than 0.2 s is queued; the
stop waits for the queue (8 s ceiling). It has unit tests (`BridgePacerTests`) and **has never been
measured end to end** — no lab wave ran after it (wave 5 was built from `5661ca4`, earlier).

**The question:** with Wispr starting 0.5 s … 6 s late, does Wispr's `History` row hold **every word**
of the clip — the head it missed live, the middle it heard sped up, and the tail after the stop?
And what does the compression cost in recognition, against the same clip fed at live speed?

## Read first (do not re-derive what is measured)

- `Sources/WalkieTalkie/BridgePacer.swift`, `AudioBridge.swift`, the bridge parts of
  `WisprFlowSource.swift` (`feedWatchTick`, `release()`, `bridgeDrainSeconds`, `stopWaitsForInput`).
- `.claude/rules/dictation-source.md` → *The bridge feeds From Walkie* (env switches `WT_BRIDGE`,
  `WT_BRIDGE_DEVICE`, `WT_BRIDGE_RATE`; log lines `🔀 bridge released …`, `🔀 bridge caught up …`;
  `GET /test/state` → `wisprLive.bridge`).
- `.claude/rules/desk-testing.md` — the loopback routes; **`POST /test/mic {"device": …}`** points the
  relay's recorder at any CoreAudio input, process-local.
- `docs/vm-wispr.md` (*Done 2026-09-28* and after) and `docs/vm-lab.md` — Wispr in `wt-lab`: its
  microphone is Auto-detect → **BlackHole 2ch**; **`tart exec` for anything that must hear audio**
  (SSH has no microphone grant — exact zeros); `open -b com.electron.wispr-flow`; rows out of Wispr's
  `History`. **Finding A**: two readers/writers on devices of the *same* BlackHole driver share
  statics — the fix is a device from a **separate driver bundle** (e.g. `blackhole-16ch`).
- `evals/plan/harness.py`, `evals/plan/cases_wispr.py` (TW*), `tools/vm-lab.sh deploy` — how the
  relay is built into and driven in the guest. Reuse; do not write a second harness.

## The rig (in the guest)

- **Wispr is not touched**: its microphone stays BlackHole 2ch (another session uses the guest at
  20:00 on that assumption — see *Sharing the VM*).
- **The bridge writes into BlackHole 2ch**: launch the guest relay with `WT_BRIDGE=1
  WT_BRIDGE_DEVICE="BlackHole 2ch"` (no From Walkie device needed in the guest).
- **The relay's "microphone" is a second BlackHole from a separate driver** (`blackhole-16ch`;
  install with brew, `sudo killall -9 coreaudiod` instead of a reboot) — `POST /test/mic
  {"device": "BlackHole 16ch"}`; the harness plays the clip into it (`sounddevice`, via `tart exec`).
  Keep the **system default input BlackHole 2ch** afterwards, and confirm a Wispr row still says
  `micDevice = Auto-detect (BlackHole 2ch)`.
- Engine = Wispr in the guest relay; a relay gesture over the loopback routes (start at clip start,
  stop at clip end + the usual tail).

## What to measure

Clips: ~10 of Victor's real dictations from `~/.walkie-talkie/voice-corpus/` (host, read-only —
copy them in), 8–40 s, Romanian and English, some that **start speaking within 0.3 s** of the
recording (the head is the part at risk).

Per clip:

- **B — baseline:** the clip played straight into BlackHole 2ch with Wispr's push-to-talk held
  *before* playback (no relay, no bridge) → Wispr's text = the reference. Twice, to know Wispr's own
  run-to-run noise.
- **L — late start, real app:** relay gesture at t=0, clip starts at t=0, Wispr made late by
  - warm (it is running, ~0.3–0.7 s naturally),
  - cold (Wispr quit before the gesture, ~5–6 s),
  - and if you can do it without an app change, a middle value (~2–3 s).
- **P — pacing alone (optional, cheap):** render offline what the pacer would hand over for a lag of
  2 s and 6 s (cut lead, pauses → 0.25 s while lagging, `ffmpeg atempo=1.1` while lagging), play it
  straight into BlackHole 2ch as in B. Separates "the speed-up hurts Wispr" from "the plumbing drops
  audio".

Record per run: Wispr's `formattedText`, row duration, the `🔀 bridge released … held, cut, behind
live` and `🔀 bridge caught up … live X s after` lines, the release delay after the gesture, and
`wisprLive.bridge` at stop.

Score, against B:

1. **head kept** — the first 3 words of B are the first 3 words of L (normalised: case, punctuation,
   digits vs words);
2. **tail kept** — the last 3 words of B are in L (the drain waited long enough);
3. **word error** — WER(L, B) against WER(B₁, B₂) — Wispr's own noise is the floor, not zero;
4. **caught up** — the seconds from release to `caught up`; and whether it ever did before the stop;
5. **no hole** — no word of B missing mid-sentence in L (a starved queue puts silence in a word).

**Pass** (Victor's "the full clip is transcribed"): head and tail kept in every warm and cold run,
WER(L, B) within Wispr's own noise + 5 points. Anything else is a finding: which part went missing,
at which lag, and the log line that shows why.

Budget: every row is a Wispr cloud call. Roughly 100 rows; stop early if the answer is clear.

## Sharing the VM (coordination with `wt-wispr-markers`, 20:00)

Another scheduled session (`evals/wispr-markers/PROMPT.md`) uses the same `wt-lab` guest from 20:00
and waits while it is running.

- On start, write `~/.walkie-talkie/scheduled/wt-lab.busy` (one line: `wt-wispr-catchup <pid>
  <start time>`); delete it when the VM is shut down. The markers session waits while it exists.
- **Hand the VM over by 21:30**: stop taking new runs at 21:10, write what you have, restore the
  guest (Wispr's mic untouched, default input BlackHole 2ch, the guest relay quit), `tart stop`,
  delete the busy file. An unfinished measurement goes in the report as unfinished — do not come back
  to the VM later tonight.

## Rules

- **VM only.** Never touch the host's Wispr Flow, microphone, mouse, keyboard or the host's Walkie
  Talkie (no `relay-restart.sh`, no `/test/*` on the host).
- `wt-lab` is the never-clone VM: no `tart clone`, no reset, no delete.
- No app source changes tonight — a fix you would make goes in the report as a recommendation.
- Git: stage your own files by explicit path (never `git add -A`, never `git stash` — other
  sessions share this tree), commit, push.

## Deliverable

`evals/wispr-catchup/README.md`: the table (clip × lag × head / tail / WER / caught-up s, with n),
the verdict on Victor's question in one sentence at the top, what surprised you, recommendations,
and the exact commands to re-run. Raw rows in `evals/wispr-catchup/results.jsonl`, the driver as
`evals/wispr-catchup/run.py`. A short dated section in `docs/journal.md` pointing at it. Then shut the
VM down, delete the busy file, and exit.
