# Talkie Type

Talkie Type is a Windows/macOS/Linux system-tray app that records your microphone via a global hotkey, transcribes with Groq Whisper Large v3, types the result into the currently focused app, and also persists every transcript with an exact Unix-ms timestamp to local JSONL files.

## Features

- Global low-level hotkey (default toggle: Ctrl+Shift+R; optional hold-to-talk: Ctrl+Space)
- Floating draggable toggle widget with recording state + level meter
- Tray icon state changes + notifications
- Groq API transcription using Whisper Large v3
- Automatic text insertion into the focused window
- Append-only daily transcript files (JSON Lines) with atomic `.pending` swap + fsync
- Configurable retention (default 90 days) with background purge
- Temp WAV recording + best-effort secure deletion
- Logging to console and rotating log file + optional desktop notifications

## Requirements

- Windows 10/11
- Python 3.10+
- A working microphone device
- Groq API key

## Installation

1. Create a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Provide your Groq API key:

   - Option A (recommended): run Talkie Type once and enter the key in **Settings** (it is stored encrypted in local app data).
   - Option B: copy `.env.example` to `.env` and put your key in it:

   ```env
   GROQ_API_KEY="gsk_..."
   ```

## Run

- Double-click `run.bat`, or run:

  ```powershell
  .\.venv\Scripts\python.exe -m talkietype      
  ```

On manual launch, Talkie Type opens a window showing today’s transcripts with live updates. Use the tray menu to control startup launch and hotkey mode.

## Usage

- Press **Ctrl+Shift+R** to toggle recording ON/OFF
- (Optional) Hold **Ctrl+Space** to record (if you disable “Hands-free mode” in the tray)
- When transcription completes, Talkie Type types the text into the currently focused window
- Every successful recording stop appends `{"ts":..., "text":...}` to today’s JSONL file

### Hotkey alternatives

If Ctrl+Space conflicts with other software, change the hotkey in the config file to one of these common options:

- `ctrl+shift+r`
- `f6`
- `ctrl+alt+space`

Open the config from the tray menu: **Open config** → edit `toggle_hotkey` or `hold_hotkey`.

### Hands-free mode

Right-click the tray icon and toggle **Hands-free mode**:

- ON: toggle behavior via `toggle_hotkey`
- OFF: hold-to-talk behavior via `hold_hotkey`

## Configuration

Talkie Type creates a config file on first run:

- `%APPDATA%\TalkieType\config.json` (legacy: `%APPDATA%\TalkieType\config.json`)

Useful options:

- `toggle_hotkey`: e.g. `"ctrl+shift+r"`, `"f6"`
- `hold_hotkey`: e.g. `"ctrl+space"`
- `hands_free_enabled`: `true/false` (toggle vs hold-to-talk)
- `autostart_enabled`: `true/false` (Windows startup launch)
- `sample_rate_hz`: default `16000`
- `max_record_seconds`: default `30`
- `vad_rms_threshold`, `vad_silence_ms`: end-of-utterance auto-stop tuning
- `toggle_widget_enabled`, `toggle_widget_always_on_top`: floating widget controls
- `notifications_enabled`: enable/disable desktop notifications
- `typing_interval_s`: per-character typing delay (helps in some apps)
- `pyautogui_failsafe`: keep the mouse-corner failsafe on/off
- `retention_days`: default `90`

## API key storage

- The Groq API key is stored encrypted in `%APPDATA%\TalkieType\secrets.json` (legacy: `%APPDATA%\VoiceType\secrets.json`).
- The encryption master key is stored in the OS keyring for your user profile.
- You can set/update the key from the app’s **Settings** button.

## Transcript storage

Transcripts are stored under:

- `%APPDATA%\TalkieType\transcripts\<YYYY-MM-DD>.jsonl` (legacy: `%APPDATA%\VoiceType\transcripts\...`)

Each line uses:

- `{"ts":1680001234567,"text":"transcribed sentence..."}`

## Logs

Logs are written to:

- `%APPDATA%\TalkieType\logs\voicetype.log` (legacy: `%APPDATA%\VoiceType\logs\...`)

Use the tray menu: **Open logs**

## Troubleshooting

### “Missing GROQ_API_KEY”

- Open **Settings** in the app and set your key, or
- Ensure `.env` exists in the project folder (same folder as `run.bat`), or
- Ensure `%APPDATA%\\TalkieType\\.env` exists (legacy: `%APPDATA%\\VoiceType\\.env`)
- Ensure it contains `GROQ_API_KEY="..."` (quotes are allowed)

## Releases (GitHub)

- CI runs on pull requests and `main` pushes.
- Tag pushes like `v0.1.0` trigger a multi-OS build and publish assets to GitHub Releases.

### Ship command

On a clean git working tree:

```bash
make ship
```

This runs tests, creates a `v<version>` tag from `voicetype.__version__`, and pushes the tag to `origin`, which triggers the GitHub Release workflow.

### Release troubleshooting

- **Build fails with PyInstaller argument errors**: ensure the build scripts pass a script path like `voicetype/__main__.py` to PyInstaller (not `-m voicetype`, which is a different flag in PyInstaller).
- **Windows zip packaging fails with “file is being used by another process”**: this can happen immediately after PyInstaller finishes; the Windows packaging script retries `Compress-Archive` a few times.
- **Missing release assets**: the Release workflow validates that `dist_release/` contains the expected platform artifact before uploading.

### Hotkey doesn’t trigger

- Some apps (games, remote desktop tools) can intercept low-level keyboard hooks.
- If you run into permissions issues, try running your terminal “as Administrator” and re-testing.
- Try switching to another hotkey such as `f6` or `ctrl+shift+r`.

### Microphone errors / “No audio captured”

- Verify Windows microphone permissions (Settings → Privacy & security → Microphone)
- Ensure a default input device exists
- Try unplugging/replugging your mic or selecting a different input device in Windows Sound settings

### Transcription fails

- Check the log file for details
- If the API call fails, Talkie Type keeps the WAV file for debugging in:
  - `%APPDATA%\TalkieType\failed_recordings`

### Typing looks wrong in some apps

- Set `typing_interval_s` to a small value like `0.005`
- Some applications handle simulated keystrokes differently; Talkie Type falls back to clipboard paste if direct typing fails

## Security notes

- Do not commit your `.env` file.
- Talkie Type attempts best-effort secure deletion of temp WAV files, but Windows filesystems may still retain recoverable traces.
