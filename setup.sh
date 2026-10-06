#!/bin/bash
# One-time setup for a new Mac: checks the toolchain, installs the local
# Whisper model's Python packages, exports $WALKIE_SHOTS, then builds and
# installs the app. Safe to run again. See SETUP.md.
set -e
cd "$(dirname "$0")"

say()  { echo "▸ $1"; }
fail() { echo "✗ $1" >&2; exit 1; }

[ "$(uname -m)" = "arm64" ] || echo "⚠️  Not an Apple Silicon Mac: the local Whisper model will not run. Use ElevenLabs instead."

say "Checking the Swift toolchain"
swift build --version >/dev/null 2>&1 \
    || fail "swift does not work. Install the Command Line Tools (xcode-select --install) and run this again."

say "Checking ffmpeg"
command -v ffmpeg >/dev/null || { command -v brew >/dev/null && brew install ffmpeg; } \
    || fail "ffmpeg is missing and Homebrew is not installed. Install ffmpeg and run this again."

# The app finds Python by probing these paths, not $PATH (an app opened from
# Finder gets launchd's bare PATH). Homebrew's Python refuses pip installs
# (PEP 668), so the python.org installer is the one that works.
say "Looking for a Python with mlx-whisper"
PY=""
for p in /usr/local/bin/python3 /Library/Frameworks/Python.framework/Versions/*/bin/python3 /opt/homebrew/bin/python3; do
    [ -x "$p" ] || continue
    if "$p" -c "import mlx_whisper" 2>/dev/null; then PY="$p"; break; fi
done
if [ -z "$PY" ]; then
    for p in /Library/Frameworks/Python.framework/Versions/*/bin/python3; do
        [ -x "$p" ] && PY="$p"
    done
    [ -n "$PY" ] || fail "No python.org Python found. Install Python 3.12 from https://www.python.org/downloads/macos/ and run this again."
    say "Installing mlx-whisper into $PY"
    "$PY" -m pip install mlx-whisper
fi
"$PY" -c "import mlx_whisper" || fail "mlx-whisper did not install into $PY"
echo "  using $PY"

LINE='export WALKIE_SHOTS=~/Library/Caches/ro.victorrentea.wispr-relay/shots'
if ! grep -qF "WALKIE_SHOTS=" ~/.zshrc 2>/dev/null; then
    say "Adding WALKIE_SHOTS to ~/.zshrc"
    echo "$LINE" >> ~/.zshrc
fi

if pgrep -x "Walkie Talkie" >/dev/null; then
    say "The app is running: building with ./relay-restart.sh --build"
    ./relay-restart.sh --build
else
    say "Building and installing /Applications/Walkie Talkie.app"
    ./build-app.sh
    open "/Applications/Walkie Talkie.app"
fi

echo
echo "✓ Done. Now grant Accessibility, Screen Recording and Microphone (see SETUP.md, step 4)."
