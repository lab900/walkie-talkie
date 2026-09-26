# Lab night run — 2026-09-26/27, the whole suite inside the Tart guest

The full test plan (`evals/plan/harness.py`, phases A → B → C → D exactly as the host's regression
run split them) ran **inside `wt-lab`** — no synthetic input, no witness tab and no test audio on
Victor's screen. Compared with the host's regression run of the same evening,
`evals/plan/report-regression-2026-09-26.md` (its merged table's verdict column, with the TR11/TR14
re-runs).

**Result: nothing regressed in the app.** Of the 133 case runs, 100 PASS in the lab. Every verdict
that moved away from the host has a cause outside the app, and 9 of the 14 have the same one: **the
ElevenLabs account ran out of credits** (`HTTP 401 quota_exceeded`, "2 credits remaining, 8
required"; the host's own log shows the same since 20:07), so every live-caption and correction
case had nothing to observe. The lab also found one real defect the host cannot reach: **TD21** —
the guest's Terminal reuses a closed tab's tty, and the binding moves to the stranger tab.

**Lab:** BUG 3 · FAIL 13 · PASS 100 · SKIP 17 (133 case runs). **Host:** BUG 2 · PASS 114 · SKIP 17.

| | |
|---|---|
| fixed (host bad → lab PASS) | 0 |
| regressed (host PASS → lab bad, app at fault) | **0** |
| still failing (bad on both) | 2 — TL18, TG40 (the same BUGs) |
| ran in the lab only (host SKIP) | 1 — **TD21 BUG** |
| lab-only differences | 14 — 9 ElevenLabs quota, 4 guest speed/settings (LC9, TL6, TD12, TG16), 1 no Wispr (TG7) |
| flaky in the lab, PASS on a re-run | LC3, TL2; TD13 PASS once tmux was installed |

## How it ran

| step | when (EEST) | took |
|---|---|---|
| `vm-lab.sh up` (the guest had been stopped 25 min earlier — warm host cache) | 21:45 → 21:50 | 4 min 40 s (SSH after 2 min) |
| `pip3 install --user mlx-whisper` ‖ `brew install ffmpeg` | 21:53 → 21:58 | 5 min 10 s / 4 min 40 s, in parallel |
| repo mirror into `~/wt-lab` (9.4 MB tar) | 21:51 → 21:54 | 2.5 min (the disk) |
| app redeployed (host build 20:33 = 2e2d8d5) + launch to `/up` | 21:54 → 21:55 | 40 s; `trusted=true eventTap=true` |
| `POST /engine {"id":"eleven-live"}`, `tapAlive` true, BlackHole 440 Hz `loopback_alive()` true | 21:55 → 21:58 | the tone check 2 min |
| whisper helper once on `.warmup.wav` (weights 1.5 GB) | 21:59 → 22:04 | 4 min 35 s |
| phase A, 50 runs (cap 20 min) | 22:04 → 22:12 | 8 min |
| phase B, 28 gesture runs (cap 30 min) | 22:12 → 22:20 | 7.5 min |
| phase C, 31 audio runs through BlackHole 2ch (cap 40 min) | 22:20 → 22:30 | 10 min |
| phase D, 23 processes / 24 runs, 30 s idle before each (cap 120 min) | 22:30 → 00:06 | 96 min |
| `brew install tmux` + re-run of LC3, LC9, TL2, TG16, TD13 | 00:07 → 00:08 | 1 min |

Environment of every phase: `WT_LOOPBACK="BlackHole 2ch" HANDS_OFF=1 WT_COLD_WHISPER=kill
WT_ALLOW_SPAWN=1 WT_ALLOW_RELAUNCH=1`, launched with `tart exec … nohup` (the Automation grant is
`tart-guest-agent`'s), polled and copied over SSH. Skipped for good as on the host: sleep, cc,
Codex (TD7, TD17, TD18, TD23, TD28, TD30, TL28). One lab-only patch: the guest's copy of
`cases_gestures.py:43` derives `INJECT` from `WT_LOOPBACK` like the other two case files (the repo
still hard-codes `"WT Inject"` there). Scripts: `run-phase.sh`, `run-d.sh`; per-phase logs
`run-*.log`; reports `report-vm-{A,B,C}.md`, `report-vm-DNN-*.md`, `report-vm-X1.md` (the re-run).
This file is built by `.merge_night.py` + `.night_notes.json`.

## Why the first guest run (18:18 UTC) differed from the host, and what changed tonight

| first run | cause | tonight |
|---|---|---|
| TL4 FAIL (90 s, `ok:false`), TL6/TL7 SKIP ("the helper would not come up") | no `mlx_whisper`/`ffmpeg`/weights in the guest | TL4, TL7 PASS; TL6 answers but in 33 s (cold load off the HDD) |
| TR17, TD10 ERROR `./relay-restart.sh` not found | the plan sat at `~/wt-lab/plan`, so `REPO` = `/Users/admin` | `~/wt-lab` mirrors the repo root: both PASS |
| LC13, B2 SKIP "engine is eleven" | the guest app was on the batch engine | `eleven-live`; they now run (and FAIL on the quota) |
| TL12 FAIL | already the quota: its log has `HTTP 401 … quota_exceeded` at 18:40 UTC, not only the injected 401 | still FAIL, same cause |
| LC2 ERROR `KeyError: 'liveCaption'`, TL22 FAIL (mic 1.28 s after the gesture), TR4 FAIL (no hangs/ file) | a 15:01 build (before most of fix batches 1–5) and/or a guest that had just booted — not re-diagnosed | host's 20:33 build, guest up 15 min: all three PASS |
| phases cut to 57 + 5 + 3 cases | `tart exec` fragility, a shorter night | the whole plan, 133 runs |

## Diff against the host's regression run

**Lab:** BUG 3 · FAIL 13 · PASS 100 · SKIP 17 (133 case runs). **Host regression:** BUG 2 · PASS 114 · SKIP 17 (133 case runs).

### Regressed in the lab — host PASS → BUG/FAIL/ERROR (0)

none

### Still failing — bad on the host and in the lab (2)

- **TL18**: host BUG → lab **BUG** — same as the host: the restart gate opens (`busy` false, dry-run exit 0) over audio staged for Recover
- **TG40**: host BUG → lab **BUG** — same as the host: 🔽 in the settle of a relay prompt is refused (the `refused` line before the delivery) and opens no next sentence — the Q12 expectation (batch 6, start the next plain sentence) is not met by the 20:33 build

### Fixed in the lab — host BUG/FAIL/ERROR → PASS (0)

none

### Ran in the lab, SKIP on the host (1)

- **TD21**: host SKIP → lab **BUG** — Terminal in the guest reuses a closed tab's tty (ttys001) within 10 s; on the host it never did (ttys029 → ttys030), so the host SKIPs. Same BUG in the first guest run: the binding silently moves to the stranger tab and the sentence lands there. A real defect only the lab can reach

### Lab-only differences — the verdict moved because of the guest, not the app (14)

- **LC9**: host PASS → lab **FAIL** — timing, twice (main run and re-run): 1–2 of 30 words start at opacity 0.13–0.18 and 5–6 take 0.65–0.78 s to 90 % (limit 0.65 s) — frame pacing on the guest's paravirtual display; the host PASSes
- **TL6**: host PASS → lab **FAIL** — the revived helper answered in 33.0 s (case wants < 20 s; host 3.3 s): a cold `whisper-large-v3-turbo` load off the USB spinning disk. Survival, `it died` and the answer itself were right
- **TG7**: host PASS → lab **SKIP** — Wispr Flow not installed in the guest
- **TG16**: host PASS → lab **FAIL** — twice (at 10 ms and 67 ms after the panel). **Not the app**: the log says `☠️ kamikaze — the prompt on the panel closes its agent when done` and the prompt was delivered 4.3 s after the F9; the case reads the outbox 2.5 s after F9, which only works with autosend on (1 s receipt). The host has autosend on, the guest off (its defaults) — the case should wait for the delivery, not 2.5 s
- **TL12**: host PASS → lab **FAIL** — ElevenLabs quota exhausted (every request `HTTP 401 quota_exceeded`, 2 of 10 000 credits left): the next sentence cannot come back on ElevenLabs, so it went to local-fallback too
- **TL16**: host PASS → lab **FAIL** — quota: the empty-answer fault never ran — the upload got 401 quota_exceeded first, went to the local model and was delivered
- **TL29**: host PASS → lab **FAIL** — quota: the live socket never opened (`quota_exceeded` on connect), so the drop fault never fired
- **LC13**: host PASS → lab **FAIL** — quota: no live words (the realtime socket is refused), band words 0
- **B1**: host PASS → lab **FAIL** — quota: no live band words to place
- **B2**: host PASS → lab **FAIL** — quota: no live correction (scribe_v2 refused)
- **B3**: host PASS → lab **FAIL** — quota: no live correction started
- **B4**: host PASS → lab **FAIL** — quota: no failed correction to observe
- **B5**: host PASS → lab **FAIL** — quota: cost delta $0.000183 vs expected $0.001186 — no corrections were billed
- **TD12**: host PASS → lab **FAIL** — the relaunched app answered `/up` and took the restore `/bind` (200, `re-bound to ttys002` logged 19:32:54) while its main thread was frozen for 12 s at launch (`🧊 main thread silent for 9.7 s`); `state.bound` read 0.5 s later was still None. Lab-only speed, but it shows `/up` answering before launch has settled

### Other changes (0)

none

### PASS on both (100)

LC1, LC2, LC3, LC4, LC5, LC6, LC7, LC7b, LC8, LC10, LC14, LC15, LC16, LC17, TL2, TL3, TL4, TL7, TL27, TR17, TR21 (lifecycle module), TR28, TD1, TD2, TD4, TD5, TD6, TD10, TD13, TD14, TD15, TD16, TD19, TD20, TD29, TD31, TR21 (delivery module), TG19, TL15, TL17, TL21, TL22, TR4, TR18, TR19, TR20, TG1, TG2, TG3, TG4, TG6, TG10, TG11, TG14, TG15, TG17, TG25, TG26, TG28, TG29, TG30, TG36, TG41, TG8, TG9, TG13, TG18, TG20, TL10, TL11, TL13, TL14, TL30, TL32, TR9, TR13, TR23, TR24, TD25, TR22 (delivery module), TL1, TD8, TD11, TL26, TL5, TL31, TR27, TD22-298.5, TD22-299.5, TD22-300.2, TL8, TL9, TR10, TR11, TR12, TR14, TR15, TD9, TL24, TL25

### Re-run once in the lab (5)

- **LC3**: first FAIL → re-run **PASS** — first run FAIL on timing (velocity 0 only from +1.65 s, 11 pt/s residue); PASS on the re-run (0 from +1.47 s) — flaky on the slow guest
- **LC9**: first FAIL → re-run **FAIL** — timing, twice (main run and re-run): 1–2 of 30 words start at opacity 0.13–0.18 and 5–6 take 0.65–0.78 s to 90 % (limit 0.65 s) — frame pacing on the guest's paravirtual display; the host PASSes
- **TL2**: first FAIL → re-run **PASS** — first run FAIL: cancel cleared in 1652 ms (the first guest run 1436 ms, host 44 ms); re-run PASS in 27 ms — a main-thread stall in the guest (the halo's MilkDrop page is never ready there), not the cancel path
- **TD13**: first SKIP → re-run **PASS** — SKIP in the main run (no tmux); `brew install tmux` (3.7c, 15 s) in the guest and the re-run PASSes
- **TG16**: first FAIL → re-run **FAIL** — twice (at 10 ms and 67 ms after the panel). **Not the app**: the log says `☠️ kamikaze — the prompt on the panel closes its agent when done` and the prompt was delivered 4.3 s after the F9; the case reads the outbox 2.5 s after F9, which only works with autosend on (1 s receipt). The host has autosend on, the guest off (its defaults) — the case should wait for the delivery, not 2.5 s

### SKIP on both (16)

LC11, LC12, LC18, TL23, TL33, TG21, TG22, TG23, TG24, TD3, TD24, TD26, TD27, TG12, TR25, TR22 (lifecycle module)

### On the host, not run in the lab (0)

none

## What the lab still lacks

1. **ElevenLabs credits.** The account is at its 10 000-credit quota — top it up, or the 9 live /
   correction cases (TL12, TL16, TL29, LC13, B1–B5) cannot run anywhere. The key file is copied in
   by hand (`~/.walkie-talkie/elevenlabs.env`) and was taken out before `bake`.
2. **Speed — an SSD.** A cold local model loads in 33–77 s (host ~3 s: TL6), a relaunch freezes the
   app's main thread for 12 s (TD12), the live caption's frame pacing misses LC9's 0.65 s by up to
   0.18 s, and the halo's MilkDrop page is never ready within its 2 s (16 fallbacks to the film in
   the log) — which also stalls the main thread (TL2's first 1.6 s cancel).
3. **Autosend.** Off in the guest (its defaults), on on the host. TG16's case only works with the
   1 s receipt; either set the guest's autosend on before a run or make TG16 wait for the delivery.
4. **Wispr Flow** (TG7, the Wispr posters of TG29) — deliberately out of scope for the lab so far.
5. **`claude` and `codex` CLIs** (TD7, TD17, TD18 [CC]; TD28, TD30, TL33 [Codex]).
6. **Sleep** (TD23) — a VZ guest cannot be put to sleep from inside the harness; untested.
7. **Cases the lab could now run but the harness still skips**: TL23 and LC12 need the app relaunched
   under an env var — safe in the guest, where nobody dictates. LC11/LC18 (second display, G7/G8)
   and TR25 (G11) are app gaps, not lab gaps.
8. **Repo fixes the lab needs**: `cases_gestures.py:43` `INJECT` from `LOOPBACK` (patched only in
   the guest); `vm-lab.sh down` over SSH (it uses `tart exec`, which fails silently when the agent is
   down, then waits 600 s and pulls the plug); `vm-lab.sh deploy` dies on
   `codesign --verify --strict` because `.warmup.wav` is written into the bundle after signing.
9. **The nightly job** — a host LaunchAgent that runs `up` + the four phases — is still not
   written. Tonight's timings say a night is long enough: ~2 h of tests after a 5–10 min boot.
10. Tailscale in the guest is still not logged in (no phone access).

## Merged table

| case | phase | host | lab | s | observed in the lab | source |
|---|---|---|---|---|---|---|
| LC1 | A | PASS | **PASS** | 2 | centre off 0.00 pt, max velocity 0.0, opacity 0 → [0.36] at +0.5 s → 0.4, bandWidth 1024 | report-vm-A.md |
| LC2 | A | PASS | **PASS** | 21 | 120 samples, wide from t=4.068, max centre offset 0.0 pt while narrow, dropped 38, max velocity 578 | report-vm-A.md |
| LC3 | A → re-run | PASS | FAIL → **PASS** | 10 | eraser at +5.07 s, max velocity 0.0 pt/s and centre drift 0.00 pt in [+1.5 s, eraser), velocity exactly 0 from +1.47 s | report-vm-X1.md |
| LC4 | A | PASS | **PASS** | 5 | max velocity 700 pt/s, 21 samples, dropped 7 | report-vm-A.md |
| LC5 | A | PASS | **PASS** | 5 | corrections +1, ghosts [['the', 'build']], reflowing 122.4 → [0] at +1.6 s, update seen 0.02 s after the POST | report-vm-A.md |
| LC6 | A | PASS | **PASS** | 3 | corrections +2, ghosts [['500']] | report-vm-A.md |
| LC7 | A | PASS | **PASS** | 2 | dropped before 19; first sample: dropped 0, anchor 380, velocity 0, centre off 0, corrections 0 | report-vm-A.md |
| LC7b | A | PASS | **PASS** | 3 | dropped 19 → 19, corrections +0, anchor -137.3 → -137.3 | report-vm-A.md |
| LC8 | A | PASS | **PASS** | 4 | 6 revisions, corrections +0, 0 sample(s) with ghosts | report-vm-A.md |
| LC9 | A → re-run | PASS | FAIL → **FAIL** | 14 | 1 word(s) started at ≥ 0.1, e.g. [(15, 0.15)]; 6 word(s) slower than 0.65 s to 90 %: [(4, 0.78), (5, 0.72), (12, 0.65)] — corrections 0, start opacity max 0.15, slowest to 90 % 0.83 s over 30/30 words | report-vm-X1.md |
| LC10 | A | PASS | **PASS** | 4 | after close: open False words 0; after reopen at 0.1 s: open True words 2 (the panel's alpha is not in describe(): a fade that ends at 0 over a reopened band is invisible here) | report-vm-A.md |
| LC11 | A | SKIP | **SKIP** | 0 | needs G7 liveCaption.frame/screen | report-vm-A.md |
| LC12 | A | SKIP | **SKIP** | 0 | needs the app relaunched under RELAY_SHOOT (out of scope: no restarts from the runner) | report-vm-A.md |
| LC14 | A | PASS | **PASS** | 1 | words 0, open True | report-vm-A.md |
| LC15 | A | PASS | **PASS** | 3 | +0.6 s [0.94, 0.94, 0.94, 0.75, 0.57, 0.38] (max err 0.06), settled [0.99, 0.99, 0.99, 0.8, 0.6, 0.4]; after commit +0.8 s [1, 1, 1, 1, 0.99, 0.99], corrections 0 | report-vm-A.md |
| LC16 | A | PASS | **PASS** | 17 | eraser at +5.04 s, 261 pt/s; dropped 2, visible-centre offset max 2 pt over 7 samples; fresh line: eraseFront None, centre off 0.0, velocity 0 | report-vm-A.md |
| LC17 | A | PASS | **PASS** | 7 | corrections +1, front -371.56672692708344 → -84.84464192710493 (263 pt/s); the paler tint is not in describe() | report-vm-A.md |
| LC18 | A | SKIP | **SKIP** | 0 | needs G8 (/test/live-caption script + trace) | report-vm-A.md |
| TL2 | A → re-run | PASS | FAIL → **PASS** | 1 | cleared in 27 ms; 'nothing to cancel' line: yes | report-vm-X1.md |
| TL3 | A | PASS | **PASS** | 1 | eleven-live→whisper: mid-sentence answer engine=eleven-live, after cancel engine=whisper; whisper loading=True ready=False | report-vm-A.md |
| TL4 | A | PASS | **PASS** | 80 | first (cold): 77.14 s ok=True via=local-fallback text='If I dictate now, how good is this dictation, I wonder.'; second (warm): 3.04 s ok=True | report-vm-A.md |
| TL6 | A | PASS | **FAIL** | 33 | route 32.99 s → {'warning': '⚠️ a test was unavailable — transcribed on this Mac', 'engine': 'whisper-local', 'via': 'local-fallback', 'seconds': 32.98562300205231, 'text': 'If I dictate now, how good is this dictation, I wonder.', 'ok': True}; app pid 928→928; 'it died' line: yes; ready after=True; restart up in 0.0 s (helper pid 2049→2094) | report-vm-A.md |
| TL7 | A | PASS | **PASS** | 26 | after SIGKILL (alive=False): ready=False; after one request (25.79 s, ok=True): ready=True | report-vm-A.md |
| TL23 | A | SKIP | **SKIP** | 0 | needs an env change + relaunch of the app (RELAY_WHISPER_PYTHON=/nonexistent); out of scope for HTTP | report-vm-A.md |
| TL27 | A | PASS | **PASS** | 11 | released 0.76 s after the bind; words in the witness: yes; lastDelivery.to=terminal:ttys001; invariants ok | report-vm-A.md |
| TL33 | A | SKIP | **SKIP** | 0 | the key hot-add runs when the menu opens (status.elevenReady); needs Codex + moving elevenlabs.env | report-vm-A.md |
| TR17 | A | PASS | **PASS** | 39 | open sentence: exit 3 after 23.3 s (⛔️ still waiting for the sentence in flight: dictating after 20 s — gave up (--max-wait 20); nothing was restarted); after delivery: exit 0, gate opened 10.7 s after lastDelivery.at; invariants ok | report-vm-A.md |
| TR21 (lifecycle module) | A | PASS | **PASS** | 7 | guarded=True; refused=True; typed into zsh=False; outbox rows +0; lastDelivery.to=terminal:ttys001 | report-vm-A.md |
| TR28 | A | PASS | **PASS** | 0 | last launch line: '09-26 18:55:20 [relay] accessibility trusted=true eventTap=true bundle=ro.victorrentea.wispr-relay'; pid 928 started Sat Sep 26 18:54:54 2026; line from this launch=True; Info.plist id=ro.victorrentea.wispr-relay | report-vm-A.md |
| TD1 | A | PASS | **PASS** | 0 | 409 no terminal on ttys999 | report-vm-A.md |
| TD2 | A | PASS | **PASS** | 12 | to1=held to2=held held-after-two=True; hold lines=2; after bind: ALFA in witness=True, BRAVO in witness=True; replacement said in log=False | report-vm-A.md |
| TD4 | A | PASS | **PASS** | 9 | A=ttys001 B=ttys002 bind B → 200 at +1.0s; commit +3.54s vs bind done; to=terminal:ttys001; in A=True, in B=False | report-vm-A.md |
| TD5 | A | PASS | **PASS** | 6 | /bind 200; pasteMode after=True; 'caret dictation redirected' logged=False | report-vm-A.md |
| TD6 | A | PASS | **PASS** | 6 | /bind 200; spawnPending after=True; '✨ spawn dropped' logged=False | report-vm-A.md |
| TD10 | A | PASS | **PASS** | 28 | exit 3 after 22s; output: 🔍 waiting until Walkie Talkie (pid 928) is idle and quiet for 10 s…<br>⏳ waiting for the sentence in flight: held for a bind<br>⛔️ still waiting for the sentence in flight: held for a bind after 20 s — gave up (--max-wait 20); nothing was restarted | report-vm-A.md |
| TD13 | A → re-run | PASS | SKIP → **PASS** | 7 | client ttys003; panes ['%0', '%1']; bind with %0 active → 200 %0; bound-tty='ttys003 %0'; restore with %1 active → 200 %0 | report-vm-X1.md |
| TD14 | A | PASS | **PASS** | 1 | 409 for ttys002 (no terminal on ttys002); ps: Ss+  cat | report-vm-A.md |
| TD15 | A | PASS | **PASS** | 22 | tab ttys002 bind 200; guard saw foreground=['script']; refused=True; to=None; rows=0; touch ran=False | report-vm-A.md |
| TD16 | A | PASS | **PASS** | 21 | tab ttys002 bind 200; guard saw foreground=['less']; to=None; touch ran=False | report-vm-A.md |
| TD19 | A | PASS | **PASS** | 8 | tab ttys002 bind 200; to=terminal:ttys002; third Return logged=False; newlines in file=4 | report-vm-A.md |
| TD20 | A | PASS | **PASS** | 12 | sent 4826 chars via POST /test/prompt send (the panel was held); to=terminal:ttys002; arrived 4842 bytes in 5 reads (1022, 1022, 1022, 1022, 754); CR=2; ^C raw=False; ESC[201~ raw=False; literals intact=True; begin+end=True | report-vm-A.md |
| TD21 | A | SKIP | **BUG** | 17 | binding silently moved to the new tab — tty ttys001 reused by the new tab; bound after 11 s=ttys001; to=terminal:ttys001; landed in the new tab=True | report-vm-A.md |
| TD29 | A | PASS | **PASS** | 7 | unbind at +1.0s; commit +3.78s vs unbind done; to=terminal:ttys001; held=False; in A=True; in B after binding it=False | report-vm-A.md |
| TD31 | A | PASS | **PASS** | 5 | to=held awaitingBind=True rows while held=0; after bind: to=terminal:ttys001 rows=['terminal:ttys001'] outbox agrees with lastDelivery=True awaitingBind=False (real unbound speech is held the same way since 2026-09-26 — TG18) | report-vm-A.md |
| TR21 (delivery module) | A | PASS | **PASS** | 24 | B=ttys002; refused=True; delivered=False; to=None; rows=[]; bound after=ttys002 | report-vm-A.md |
| TG19 | A | PASS | **PASS** | 9 | panel up 6 ms, rebind at +0.006 s; lastDelivery.to='terminal:ttys001' (A=ttys001, B=ttys002); B's witness got 0 chars | report-vm-A.md |
| TG21 | A | SKIP | **SKIP** | 0 | T-G21: adopted hand-started Wispr sentences (`/test/wispr-handsfree {hand: true}`) are out of scope for this suite (Wispr Flow is out of scope of the plan) — not automated here | report-vm-A.md |
| TG22 | A | SKIP | **SKIP** | 0 | T-G22: adopted hand-started Wispr sentences (`/test/wispr-handsfree {hand: true}`) are out of scope for this suite (Wispr Flow is out of scope of the plan) — not automated here | report-vm-A.md |
| TG23 | A | SKIP | **SKIP** | 0 | T-G23: adopted hand-started Wispr sentences (`/test/wispr-handsfree {hand: true}`) are out of scope for this suite (Wispr Flow is out of scope of the plan) — not automated here | report-vm-A.md |
| TG24 | A | SKIP | **SKIP** | 0 | T-G24: adopted hand-started Wispr sentences (`/test/wispr-handsfree {hand: true}`) are out of scope for this suite (Wispr Flow is out of scope of the plan) — not automated here | report-vm-A.md |
| TL15 | B | PASS | **PASS** | 67 | eleven-live: at 33 s after the stop settling=True phase=transcribing/uploading; forward-click refused, forward-right refused; late reply landed, lastDelivery.to=terminal:ttys001 (bound ttys001); invariants ok | report-vm-B.md |
| TL17 | B | PASS | **PASS** | 48 | staged 12.7 s at cancelled-19-13-59.wav; model before Recover ready=False alive=True; after: loading=False ready=True; outcome=recovered; file still present=False; witness 0 chars | report-vm-B.md |
| TL18 | B | BUG | **BUG** | 11 | staged 5.9 s; busy=False busyWhy=[]; dry-run exit 0 after 2.0 s (🧪 dry run: the gate is open — would quit pid 928, relaunch, and re-bind nothing); recoverable still set=True — the gate opened over staged audio | report-vm-B.md |
| TL21 | B | PASS | **PASS** | 10 | mic opened=False; coalesced line=True; 'discarded — under 0.35s'=False; dwell refusal=False; after the stall listening=False isRecording=False; banner rows=['⏸ ignored — the Mac was frozen'] — neither toggle acted on, and the chip said why | report-vm-B.md |
| TL22 | B | PASS | **PASS** | 40 | mic opened 0.16 s after the gesture (model still loading=True, 'recording anyway' line=True, banked line=False); /test/cancel cancelled it, quiet=True; switched to eleven: microphone stayed shut | report-vm-B.md |
| TR4 | B | PASS | **PASS** | 9 | nudge posted=False; silent line=3.1 s; back line=6.0 s; new hangs files=1; sessionFlags=[]; buttons down=None | report-vm-B.md |
| TR18 | B | PASS | **PASS** | 31 | log after the gesture: names the flag (3 line(s)); listening cleared after 27 s | report-vm-B.md |
| TR19 | B | PASS | **PASS** | 17 | eleven-live: ok→ok 0.16s, ok→ok 0.23s, ok→ok 0.19s; whisper: ok→ok 0.12s, ok→ok 0.19s, ok→ok 0.22s | report-vm-B.md |
| TR20 | B | PASS | **PASS** | 13 | B=ttys002 closed while listening; to=caret; rows=[]; gone logged=True; bound after=None; awaitingBind=False; pasted into the sink=True | report-vm-B.md |
| TG1 | B | PASS | **PASS** | 2 | listening=True 268 ms after the POST, pasteMode=True, chip «Prompting → ￼... \| at caret \| ×1 \| Replace Wispr off», trace ↓98×1, ↑98 (ours) passed×1 · sent forward-click@0.678s | report-vm-B.md |
| TG2 | B | PASS | **PASS** | 4 | starts=1, re-triggered at ['372', '292', '240'] ms, refused at sentence ages ['1656'] ms, stopped by +3.2 s=True · sent forward-right@0.000s forward-right@0.373s forward-right@0.660s forward-right@0.905s forward-right@1.661s forward-right@2.372s | report-vm-B.md |
| TG3 | B | PASS | **PASS** | 31 | mic opened 0.24 s after the gesture (model still loading=True); cancel line=True, closed=True (F11 at +1.77 s); model up=True, anything opened after it=False; banked=False · sent forward-right@0.952s forward-left@1.771s · helper SIGKILLed for a cold start (WT_COLD_WHISPER=kill) | report-vm-B.md |
| TG4 | B | PASS | **PASS** | 27 | mic opened 0.22 s after the click (model still loading=True); clean start=True; context shot captured=False skipped=False; second click stop=True shutter=False; words waited 11.3 s for the model, then landed: to=caret via=local-whisper, sink got 55 chars · sent back-click@3.199s back-click@9.530s · helper SIGKILLed for a cold start (WT_COLD_WHISPER=kill) | report-vm-B.md |
| TG6 | B | PASS | **PASS** | 5 | +62 ms: stray Return=False, stop=True, sink Returns=0, open 1 s on=False · +565 ms: stray Return=False, stop=True, sink Returns=0, open 1 s on=False · sent back-click@0.001s back-right@0.062s back-click@2.324s back-right@2.889s | report-vm-B.md |
| TG7 | B | PASS | **SKIP** | 1 | Wispr Flow is not running — its chord would reach macOS instead (T-G42) | report-vm-B.md |
| TG10 | B | PASS | **PASS** | 5 | panel up 10 ms after /test/dictation, F11 at +0.010 s; outbox +0, ✕ cancelled=True, autosend=False · sent forward-left@0.010s | report-vm-B.md |
| TG11 | B | PASS | **PASS** | 7 | panel up 11 ms after /test/dictation; outbox row never; trace: swallowed by the panel=False, passed=True; sink Returns=1; autosend=False · sent back-right@0.011s | report-vm-B.md |
| TG14 | B | PASS | **PASS** | 6 | on×1, taken back×0, chip row=True · sent forward-right@0.000s forward-down@2.570s forward-down@2.874s | report-vm-B.md |
| TG15 | B | PASS | **PASS** | 6 | film started×1, stopped=None, filming=True, chip «Prompting → ￼... \| bind to send \| 0.0s (0￼)» · sent forward-right@0.000s back-up@2.554s back-up@2.872s | report-vm-B.md |
| TG16 | B → re-run | PASS | FAIL → **FAIL** | 8 | panel up 67 ms; ignored line=False; sent prompt carries kamikaze=False · sent forward-down@0.067s | report-vm-X1.md |
| TG17 | B | PASS | **PASS** | 3 | spawnPending=False, pasteMode=True, log ['09-26 19:18:44 [relay] ✨ 🔼 ↑ on a caret sentence — ignored (Q7: it stays at the caret)'], new chip rows [] · sent forward-click@0.636s forward-up@0.955s | report-vm-B.md |
| TG25 | B | PASS | **PASS** | 12 | stall line=True, 🧊 opened=True, trace ↓F10 failing open=False, sink F-keys [], the +4.5 s F10 dropped while frozen=True, the +1.0 s F10 acted after the stall=True · sent forward-right@1.077s forward-right@4.535s | report-vm-B.md |
| TG26 | B | PASS | **PASS** | 11 | POST /test/firewall at +4.5 s → 200 alive=True tap=open canaryMs=8.264374999953361; 🧊 opened=True; `did NOT see` line=False; trace ↑V failing open=False (the sink records keyDowns only, so the keyUp is read off the trace) | report-vm-B.md |
| TG28 | B | PASS | **PASS** | 8 | forward-click F7 ↓1/1sw ↑1, forward-right F10 ↓1/1sw ↑1, forward-left F11 ↓1/1sw ↑1, forward-up F8 ↓1/1sw ↑1, forward-down F9 ↓1/1sw ↑1, back-click F6 ↓1/1sw ↑1, back-down F12 ↓1/1sw ↑1, back-right F5 ↓1/1sw ↑1, back-left F3 ↓1/1sw ↑1, back-up F4 ↓1/1sw ↑1 · sent back-right@0.000s forward-left@0.764s back-down@1.599s forward-down@2.384s forward-click@3.182s forward-right@3.408s forward-up@4.011s back-up@4.982s back-click@5.857s back-left@6.748s | report-vm-B.md |
| TG29 | B | PASS | **PASS** | 8 | 10 steps, every one bare within 300 ms · Wispr posters skipped (Wispr Flow not running — its chord would reach macOS, T-G42) · sent back-right@0.000s forward-left@0.789s back-down@1.629s forward-down@2.398s forward-click@3.211s forward-right@3.373s forward-up@3.911s back-up@4.804s back-click@5.730s back-left@6.877s | report-vm-B.md |
| TG30 | B | PASS | **PASS** | 1 | HTTP 200 ⌃⌥⌘F9; effect line=True; tap saw the keyUp=True; relay binary /Applications/Walkie Talkie.app/Contents/MacOS/Walkie Talkie · sent forward-down@0.797s | report-vm-B.md |
| TG36 | B | PASS | **PASS** | 4 | the panel's row was not activated · bound after 🔽→ = None (witness ttys001); `🔽 → — Return` line=True · sent back-right@2.289s | report-vm-B.md |
| TG41 | B | PASS | **PASS** | 39 | mic opened 0.19 s after the gesture (model still loading=True); switch to eleven-live mid-sentence accepted=False (engine now whisper); words landed in the witness (227 chars), to=terminal:ttys001 via=local-whisper; banked=False · sent forward-right@3.450s forward-right@9.901s · helper SIGKILLed for a cold start (WT_COLD_WHISPER=kill) | report-vm-B.md |
| TD3 | C | SKIP | **SKIP** | 0 | needs real audio: /test/dictation skips latchedAtCaret (see TD31); run with cases_audio | report-vm-C.md |
| TD24 | C | SKIP | **SKIP** | 0 | needs a real spoken sentence (deliver → endSettling → send one turn later) — [AUDIO] | report-vm-C.md |
| TD26 | C | SKIP | **SKIP** | 0 | needs a real sentence in the settle with no key — [AUDIO] | report-vm-C.md |
| TD27 | C | SKIP | **SKIP** | 0 | needs a cancelled real recording to recover — [AUDIO] | report-vm-C.md |
| TG8 | C | PASS | **PASS** | 19 | cancel line=True, lastDelivery={'via': 'local-whisper', 'to': 'terminal:ttys001', 'at': '2026-09-26T19:20:10.312Z', 'kind': 'route'}, witness got 0 chars · sent forward-right@4.616s forward-right@17.236s forward-left@17.441s | report-vm-C.md |
| TG9 | C | PASS | **PASS** | 11 | cancel line=True, delivered after it=False, to='terminal:ttys001' · sent forward-up@2.303s forward-right@8.947s forward-left@9.084s | report-vm-C.md |
| TG12 | C | SKIP | **SKIP** | 0 | needs sentence A's panel held while a clean sentence B settles with its queued Return; two overlapping sentences cannot be staged deterministically from one Loopback — run by hand | report-vm-C.md |
| TG13 | C | PASS | **PASS** | 21 | redirect line=True, lastDelivery.to='terminal:ttys001' (bound ttys001), sink got 0 chars · sent back-click@3.286s forward-right@9.182s back-click@10.340s | report-vm-C.md |
| TG18 | C | PASS | **PASS** | 20 | chip at the start «Prompting → ￼... \| bind to send»; lastDelivery.to='terminal:ttys001' (bound ttys001 during the upload) · sent forward-right@3.134s forward-right@9.748s | report-vm-C.md |
| TG20 | C | PASS | **PASS** | 21 | unbound by F12=True; after it: to='terminal:ttys001', awaitingBind=False, bound=None; witness 227 chars · sent forward-right@3.588s forward-right@9.920s back-down@10.083s | report-vm-C.md |
| TG40 | C | BUG | **BUG** | 21 | refused line=True (before the delivery=True), state just after: listening=False settling=True, a new sentence opened=False · sent forward-right@3.645s forward-right@10.160s back-click@10.333s | report-vm-C.md |
| TL10 | C | PASS | **PASS** | 26 | phase at cancel 'uploading'; after cancel: delivery False, 'audio kept' True, recoverable True; witness 0 chars | report-vm-C.md |
| TL11 | C | PASS | **PASS** | 27 | after cancel + SIGCONT: delivery False, 'audio kept' True, recoverable True | report-vm-C.md |
| TL12 | C | PASS | **FAIL** | 34 | 401 True, ↪️ True, retries 0, via local-fallback in 8.9 s; next sentence via local-fallback; the stale-warning half needs G5 (prompt state) | report-vm-C.md |
| TL13 | C | PASS | **PASS** | 19 | retries 1, failure → fallback 0.92 s after stop, via local-fallback | report-vm-C.md |
| TL14 | C | PASS | **PASS** | 38 | failure 20.4 s after stop, retries 0, 'still uploading — 8 s in' True, via local-fallback (the fake's delay, not URLSession's own timeout — G13 for that) | report-vm-C.md |
| TL16 | C | PASS | **FAIL** | 26 | no-words line False, ↪️ True, audio kept False, recoverable False, delivered True | report-vm-C.md |
| TL29 | C | PASS | **FAIL** | 23 | drop injected False, 0 'send failed' lines (~0.0/s over ~8 s), batch via local-fallback (the socket never opened, so the drop never fired) | report-vm-C.md |
| TL30 | C | PASS | **PASS** | 20 | band open 0/23 samples, max words 0, socket {'connecting'}, pending [1] → [64], batch via local-fallback | report-vm-C.md |
| TL32 | C | PASS | **PASS** | 8 | 'audio kept' 5.8 s, recoverable cancelled-19-26-07.wav exists True, delivered False | report-vm-C.md |
| TR9 | C | PASS | **PASS** | 19 | ↪️ True, abandoned False, via local-fallback, witness 227 chars | report-vm-C.md |
| TR13 | C | PASS | **PASS** | 38 | 'returned no words' True, staged cancelled-19-26-52.wav (22.843466997146606 s), Recover via test | report-vm-C.md |
| TR23 | C | PASS | **PASS** | 28 | new microphones after the stop 0, deliveries 1, recording at the end False | report-vm-C.md |
| TR24 | C | PASS | **PASS** | 25 | A (ttys001) 227 chars, B (ttys002) 0 chars, delivery to terminal:ttys001 | report-vm-C.md |
| TR25 | C | SKIP | **SKIP** | 0 | needs a refused CoreAudio switch (G11 failNextOpen or hardware); /test/eleven cannot inject it | report-vm-C.md |
| LC13 | C | PASS | **FAIL** | 18 | max band words while recording 0; after stop: listening false at 0.172 s, band closed at 0.172 s | report-vm-C.md |
| B1 | C | PASS | **FAIL** | 21 | could not place the speech — first band word None s after the speech in the recording (onset 1.78 s into it); None s by the old clock (play() + 0.5); warm socket (open 12 s); chunks 17 | report-vm-C.md |
| B2 | C | PASS | **FAIL** | 37 | correction started False, applied False (None s), live.corrections 0, cost 0.00742 → 0.00742, band corrections 0 words 0 | report-vm-C.md |
| B3 | C | PASS | **FAIL** | 28 | no correction started within 10 s of the clip | report-vm-C.md |
| B4 | C | PASS | **FAIL** | 33 | no failed correction within 15 s | report-vm-C.md |
| B5 | C | PASS | **FAIL** | 19 | Δ $0.000183 vs expected $0.001186 (recording 7.0 s, corrections 0.0 s, keyterms 0); label $0.01 → $0.01 | report-vm-C.md |
| TD25 | D | PASS | **PASS** | 10 | 110 samples; first busy +0.046s ('prompt on screen',); bound ttys001 at +8.21s; idle-while-unbound samples=0 | report-vm-D01-TD25.md |
| TR22 (lifecycle module) | D | SKIP | **SKIP** | 0 | no route or fault switch fails a spawn (SpawnTerminal has no test hook) — needs a new gap | report-vm-D02-TR22.md |
| TR22 (delivery module) | D | PASS | **PASS** | 10 | spawn rows=['spawn:/Users/admin/workspace']; first outbox row at +8.20s; bound ttys001 at +8.20s; failure/re-offer not injectable | report-vm-D02-TR22.md |
| TD12 | D | PASS | **FAIL** | 21 | A=ttys001 B=ttys002; bound-tty before SIGTERM=['ttys001'], after the exit=['ttys002']; quit deferred=True; restore ttys002 /bind 200; bound after=None | report-vm-D03-TD12.md |
| TL1 | D | PASS | **PASS** | 125 | bound ttys001; area at t=0, flush seen at — s; at 121 s listening=True dictationStartedAt=2026-09-26T19:33:30.453Z released=no witness got 0 chars; invariants ok | report-vm-D04-TL1.md |
| TD8 | D | PASS | **PASS** | 142 | /test/area 200; flush line=none in 135 s; listening=True; dictationStartedAt 2026-09-26T19:36:05.527Z → 2026-09-26T19:36:05.527Z; screenshot rows=0 to=[]; witness bytes=0 | report-vm-D05-TD8.md |
| TD11 | D | PASS | **PASS** | 43 | busyWhy before=['dictating']; exit 0 after 41s; output: g` is still up with no microphone and no recogniser behind it — a stuck flag, not a sentence<br>⏳ waiting for 10 quiet seconds after the last delivery (1 s so far)<br>✅ idle, and quiet for 10 s — safe to restart (waited 40 s)<br>🧪 dry run: the gate is open — would quit pid 5095, relaunch, and re-bind nothing | report-vm-D06-TD11.md |
| TL26 | D | PASS | **PASS** | 304 | held (lastDelivery.to=held); released at 300.0 s; expiry line: yes; invariants ok | report-vm-D07-TL26.md |
| TL5 | D | PASS | **PASS** | 360 | route answered after 180.01 s (False); control surface at +5 s: 0.01 s; 'timed out after' by 305 s: yes; after SIGCONT stale answer consumed: yes; next decode 3.55 s ok=True in sync | report-vm-D08-TL5.md |
| TL31 | D | PASS | **PASS** | 343 | at 35 s: settling=True phase=transcribing/ (the settle waits); 'timed out' at 300.5 s after the stop; then phase=done settling=False busyWhy=[]; failed-with-budget line=True; WAV staged for Recover=True; dry-run exit 0 in 1.7 s; helper 6114→6497 ready=True; invariants ok | report-vm-D09-TL31.md |
| TR27 | D | PASS | **PASS** | 41 | 50/50 opened, 50/50 quiet after cancel, 50 'audio kept', 0 error line(s), 0 leftover mic-*.wav, 9 back-to-back starts in the same second, pid 5095→5095, 41 s | report-vm-D10-TR27.md |
| TD22-298.5 | D | PASS | **PASS** | 315 | bind posted at +298.55s, done +303.60s; released=False expired=True delivered=False rows=0 awaitingBind=False | report-vm-D11-TD22-298.5.md |
| TD22-299.5 | D | PASS | **PASS** | 312 | bind posted at +299.65s, done +300.10s; released=False expired=True delivered=False rows=0 awaitingBind=False | report-vm-D12-TD22-299.5.md |
| TD22-300.2 | D | PASS | **PASS** | 312 | bind posted at +300.31s, done +300.98s; released=False expired=True delivered=False rows=0 awaitingBind=False | report-vm-D13-TD22-300.2.md |
| TL8 | D | PASS | **PASS** | 82 | settle ended 41.8 s after stop (phaseStatus 'error', busy True); abandoned line False; listening:false+isRecording:true at []; S1 lines 1 S2 lines 1, same screen dir False; ring down after S2 stop 1 | report-vm-D14-TL8.md |
| TL9 | D | PASS | **PASS** | 61 | POST /engine whisper → 200, engine now eleven-live; busy while uploading True; late reply logged False; delivery False; outbox +0 (the switch was refused mid-upload) | report-vm-D15-TL9.md |
| TR10 | D | PASS | **PASS** | 45 | delivered 34.5 s after stop via local-fallback, 'did not come up' False, helper now alive True pid 8013 | report-vm-D16-TR10.md |
| TR11 | D | PASS | **PASS** | 67 | settle timed out at None s, ↪️ at 50.1 s, end at 50.2 s, via local-fallback, to terminal:ttys001 | report-vm-D17-TR11.md |
| TR12 | D | PASS | **PASS** | 73 | 401: 0 retries, via local-fallback; 422: 0 retries, via local-fallback; 500x2: 1 retry, via local-fallback; 429x2: 1 retry, via local-fallback | report-vm-D18-TR12.md |
| TR14 | D | PASS | **PASS** | 62 | failed line False, recoverable False, revived and asked again True (the killed sentence via local-fallback), app pid 5095 → 5095, helper pid 8013 → 8590 alive True, next sentence via local-fallback | report-vm-D19-TR14.md |
| TR15 | D | PASS | **PASS** | 412 | 20/20 sentences delivered their own words, 'gave no answer' ×0, misses [] | report-vm-D20-TR15.md |
| TD9 | D | PASS | **PASS** | 600 | listening dropped at +600s; ceiling line=True | report-vm-D21-TD9.md |
| TL24 | D | PASS | **PASS** | 600 | listening fell at 600.24 s; ceiling line: yes | report-vm-D22-TL24.md |
| TL25 | D | PASS | **PASS** | 697 | ceiling at 600.3 s after the chord, delivered 92 s later via local-fallback; ElevenLabs upload failed/absent; fallback True | report-vm-D23-TL25.md |
