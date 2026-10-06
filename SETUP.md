# Walkie Talkie — setup for our team

Talk to Claude Code instead of typing, and point at your screen while you talk.
You speak, the app transcribes, and the prompt goes into the Claude Code
terminal you bound. A screenshot, your mouse position and any text you
highlight go with it.

This is our fork of [victorrentea/walkie-talkie](https://github.com/victorrentea/walkie-talkie)
(public domain, by Victor Rentea). Our changes:

- **No private dependency.** Victor's `victor-mac-kit` is private. A stand-in
  is in `vendor/victor-mac-kit`, so a plain clone builds. Because of this, the
  wheel-drag region capture does nothing. Everything else works.
- **Dutch and English** instead of Romanian and English.

## Requirements

- macOS 13 or later. An Apple Silicon Mac for the local speech model.
- Command Line Tools with a working `swift` (`xcode-select --install`).
  Full Xcode is not necessary.
- Homebrew, for `ffmpeg`.
- Python 3.12 from [python.org](https://www.python.org/downloads/macos/),
  for the local speech model. Homebrew's Python does not work, because it
  refuses `pip install`.

## Install

1. Clone the repository:
   ```
   git clone https://github.com/lab900/walkie-talkie.git
   cd walkie-talkie
   ```
2. Run the setup script. It checks the tools, installs `mlx-whisper`, adds
   `WALKIE_SHOTS` to `~/.zshrc`, and builds and installs the app:
   ```
   ./setup.sh
   ```
   The first build takes a long time (more than 30 minutes on some Macs).
   Later builds take about one minute.
3. Open a new terminal, so that `$WALKIE_SHOTS` is set.
4. Give the permissions in **System Settings → Privacy & Security**:
   **Accessibility**, **Screen Recording** and **Microphone** for
   **Walkie Talkie**. Then restart the app with
   `open "/Applications/Walkie Talkie.app"`.
5. The first start downloads the speech model (about 1.6 GB) to
   `~/.cache/huggingface`. The log says `local model ready` when it is done.

## Use

| Key | Action |
|---|---|
| ⌘⌃B | Bind the Claude Code terminal in front (again: unbind) |
| ⌘⌃D | Start dictation, and press again to stop |
| ⌘⌃X | Transcribe the current take with the local model now |

After you stop, the prompt shows for 4–7 seconds with **Send** and
**Cancel**, then goes into the terminal. Press ⏎ to send at once.

To point at things while you talk:

- **Mouse position:** the app takes a screenshot when you start and records
  where the pointer is.
- **Highlighted text:** select text while you talk. It goes into the prompt.
- **More screenshots:** press ⌃⌥⌘ + fn + F6 while you talk.
- **Web page elements:** with the Chrome extension, hold ⌘⇧ for 400 ms over
  a page and click an element. Install it once: open `chrome://extensions`
  (or `brave://extensions`), turn on **Developer mode**, click
  **Load unpacked** and select the `chrome-extension/` folder.

## Speech engines

Select the engine in the menu bar icon, under **Engine**.

- **Local Whisper**: runs on your Mac, free, about 2.5 GB of RAM. The
  "Live captions (local)" option uses about 2 GB more; turn it off on a Mac
  with 16 GB or less.
- **ElevenLabs**: in the cloud, more accurate. Put your key in
  `~/.walkie-talkie/elevenlabs.env`:
  ```
  ELEVENLABS_API_KEY=your-key
  ```
  "ElevenLabs + Live" costs about 3 times more credits.

To change the engine without the menu:
```
curl -s -X POST http://127.0.0.1:8917/engine -d '{"id":"whisper"}'   # or "eleven"
```

## Rebuild after a change

With the app running, always use:
```
./relay-restart.sh --build
```
It waits until you stop talking, then quits, installs and restarts the app.
If the app is not running, use `./build-app.sh` instead.

After each rebuild macOS asks for Accessibility again, because the app has
only an ad-hoc signature. If it stops working, remove **Walkie Talkie** from
the Accessibility list with **−** and add it again.

To stop this, sign with a stable certificate:

1. Open **Keychain Access → Certificate Assistant → Create a Certificate…**
2. Name: `Walkie Local Signing`, Identity Type: **Self Signed Root**,
   Certificate Type: **Code Signing**.
3. Build with `CODESIGN_IDENTITY="Walkie Local Signing" ./build-app.sh`, or
   add `export CODESIGN_IDENTITY="Walkie Local Signing"` to `~/.zshrc`.

## Known limits

- The wheel-drag region capture does nothing (see the stand-in above).
- Some menu items are for Victor's own setup: his microphones, Logitech
  gestures and his other apps (Victor Addons). They do no harm.
- The app adds itself as a login item. Remove it in **System Settings →
  General → Login Items** if you do not want that.

## Troubleshooting

All events go to `~/.walkie-talkie/relay.log`:
```
tail -n 30 ~/.walkie-talkie/relay.log
```

| Problem | Fix |
|---|---|
| `swift build` fails with `dyld: Symbol not found` | The Command Line Tools install is broken. Remove `/Library/Developer/CommandLineTools` and install them again, or install a different version from [developer.apple.com/download/all](https://developer.apple.com/download/all/). |
| ⌘⌃B and ⌘⌃D do nothing | The log says `accessibility trusted=false`. Give Accessibility again (see "Rebuild after a change"). |
| `no python3 here has mlx_whisper` | Install Python 3.12 from python.org and run `./setup.sh` again. |
| No menu bar icon | The notch hides icons when the menu bar is full. Remove other icons, or check **System Settings → Menu Bar**. |
| `relay-restart.sh --build` stops after "Staged" | The app was not running. Run `./build-app.sh --swap-staged` and open the app. |
