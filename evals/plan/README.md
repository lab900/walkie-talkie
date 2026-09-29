# evals/plan — the test plan's runner

`harness.py` drives the installed app over its loopback routes (`.claude/rules/desk-testing.md`);
the cases live in `cases_*.py` and register with `@case`. The plan itself is `docs/test-plan.md`;
the lab (Tart guest) runs are `docs/vm-lab.md` and `vm/`.

    python3 evals/plan/harness.py --only 'TW4,TX*' [--skip …] [--changed-since SHA] [--list] [--report PATH]

`--help` and `--list` need no running app.

## Timing: one knob (2026-09-29)

Every wait that ends on a condition takes its timeout from `tmo(path)` = (the measured p99 of that
path × 1.5 + 1 s) × **`WT_HARNESS_SLOW`** — 1.0 at the desk, 1.5 in the guest (`vm/night/run-phase.sh`,
`vm/wispr/run-w5phase.sh` export it). The p99s are one table, `harness.P99`; where each number comes
from and what every case waits on: **`timing-audit.md`**. A case carries no slack of its own. Not
timeouts, never scaled: SIGSTOP lengths, soak gaps, a case's stimulus timing, and watch windows for
something that must not happen.

**`busy` minus the harness's own Recover staging** (`relay_busy()`): a cancelled take holds
`state.busy` for five minutes (the restart gate). The harness ignores a staging made while one of its
cases ran; one it did not make (Victor's) is still waited out.

Soak loop lengths: **`WT_SOAK_N`** — `12` for every TS loop, or `TS1=10,TS3=8`; unset = wave 5's
counts (TS1 30, TS2 20, TS3 20, TS5 10, TS6 10). `WT_SOAK_SCALE` still shrinks them proportionally.

## `--changed-since SHA`: skip what did not change

A case tagged `covers=(…)` is **SKIPped with `unchanged since SHA`** when none of the files it covers
differs between `SHA` and the working tree (committed, uncommitted or untracked). A case without
`covers` always runs. `--list --changed-since SHA` prints the verdicts without driving anything.

An entry in `covers` is one of:

- **a file's stem** — `"WisprFlowSource"` matches `Sources/WalkieTalkie/WisprFlowSource.swift`;
- **a repo path or prefix** — `"helpers/whisper_helper.py"`, `"tools/"`;
- **`"Stem:regex"`** — that file counts only when an added or removed line of its diff matches
  the regex. For the files every commit touches: `"AppDelegate:(?i)wispr|history|ownTake"`.

Always covered, whatever the tag says: `harness.py`, the case's own module and every
`cases_*` / `fake_*` module it imports (transitively), and `fake_scribe.py` for an ElevenLabs case —
a case edited since `SHA` runs.

The areas are composed from `harness.COVER` with `covers("wispr", "local", …)`:

| area | covers |
|---|---|
| `wispr` | `WisprFlowSource`, `WisprState`, `WisprHistory`, `WisprHistoryWatch`, `WisprOwnership`, `WisprWatch`, `WisprNotes`, `WisprSink`, `WisprTestHooks`, `ProcessClock`, `DictationSource`, AppDelegate's Wispr lines |
| `gesture` | HotkeyTap's gesture / chord / ⌘V lines, `ElementPicker` (every `/test/*` route) |
| `recorder` | `MicRecorder`, `InputDevice`, `AudioDevices`, `VoicePrep`, AppDelegate's mic / meter lines |
| `local` | `LocalWhisperSource`, `Transcriber`, `DecodeRate`, `AutoLocal`, `helpers/whisper_helper.py`, AppDelegate's local / fallback lines |
| `eleven` | `ElevenLabsSource`, `ElevenLabsLive`, AppDelegate's ElevenLabs lines |
| `delivery` | `TerminalBinding`, `Outbox`, `PasteHint`, AppDelegate's delivery / latch / queue / Recover lines |
| `chip` | RelayWindow's Listening / Opening / Local-in rows, `OverlayStates` |
| `restart` | `RestartGate`, `QuitGate`, `Relaunch`, `relay-restart.sh`, `tools/restart_gate.py` |

Tagged today: every Wispr case (`cases_wispr`, `_soak`, `_chaos`, `cases_w4real`: wispr + gesture +
recorder + local + delivery + chip; TW21 eleven instead of wispr; TX13 + restart), the auto fallback
(`cases_localauto`), ⌘⌃X (`cases_localnow`) and TM1/TM2. Everything else has no `covers` and always
runs. Add one when a case's reach is clear; a tag too narrow skips a case that should have run, so
when in doubt, leave it off.
