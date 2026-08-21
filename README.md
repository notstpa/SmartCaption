# SmartCaption v2.2.3
![SmartCaption](https://i.imgur.com/yQDtMjF.png)

[Download Here](https://github.com/notstpa/SmartCaption/releases)

# New This Update
- **Much Better Accuracy**: `large-v3-turbo` is now the default and the
  recommended model. Benchmarked against hand-made captions on noisy gameplay
  audio, the old default (`small`) missed 55 of 126 words -- a 50.8% word error
  rate, against 14.3% for turbo.
- **Voice Activity Filter Control**: The filter that strips non-speech audio can
  now be turned off. It is the reason smaller models drop whole lines on noisy
  recordings, and no other setting can recover what it removes.
- **Vocabulary Hints**: Give the transcriber names, jargon, or game terms from
  your video so it stops guessing at words it has never seen.
- **Accuracy Benchmark**: `benchmark/` scores output against reference captions,
  so a settings change can be measured instead of guessed at.
- **Preset Fixes**: A saved preset now actually applies on restart instead of
  restoring its name over the previous preset's behaviour.
- **Subtitle Editing**: Long inline edits keep every word instead of silently
  dropping the overflow.
- **Responsive Deletes**: Removing a model no longer freezes the window, asks
  for confirmation first, and reclaims the download cache.

# Features
- **Subtitle Generation**: Create `.srt` subtitles from audio and video files.
- **Fully Offline**: Audio never leaves your machine.
- **Built-In Model Downloads**: Download and delete Whisper models directly in the app.
- **Multiple Model Options**: Choose from `tiny`, `base`, `small`, `medium`,
  `large-v3-turbo`, and `large-v3`.
- **Word-Level Timing**: Generate tighter subtitle timing using word timestamps.
- **Flexible Subtitle Splitting**: Control max words per subtitle and max characters per line.
- **Text Cleanup Tools**: Remove punctuation or force lowercase/uppercase output.
- **Profanity Filter**: Optionally censor profanity, keeping punctuation intact.
- **Gap Fill**: Bridge short pauses for smoother subtitle output.
- **Output Tab**: Preview subtitles, edit them inline, and export when ready.
- **Language Selection**: Auto-detect, or pick from 100 languages.
- **Advanced Controls**: Tune beam size, no-speech threshold, voice activity filtering, and context handling.
- **Vocabulary Hints**: Prime the transcriber with names and jargon it would not otherwise know.
- **CUDA Support**: Optional GPU acceleration on supported NVIDIA hardware.
- **Drag and Drop**: Drop supported media files straight into the window.
- **Installer Included**: Build a Windows installer for a simpler setup experience.

# Versions

SmartCaption
- **Included:** Standalone app build
- **Best For:** Users who want to run the app directly
- **File Size:** Smaller than the installer package

SmartCaption-Installer
- **Included:** Windows installer for SmartCaption
- **Best For:** Users who want an easier installation flow
- **File Size:** Larger than the standalone app

# Build from Source
1. Clone the repo and install dependencies.
   ```shell
   pip install -r requirements.txt
   ```
   For optional NVIDIA GPU acceleration, also install:
   ```shell
   pip install -r requirements-gpu.txt
   ```
2. Run the app.
   ```shell
   python main.py
   ```
3. Run the tests.
   ```shell
   pip install pytest
   python -m pytest tests/ -q
   ```
   To measure transcription accuracy against reference captions:
   ```shell
   python benchmark/run_benchmark.py video.mp4 captions.csv --fps 60
   ```
   The reference can be an `.srt`, or an Adobe-style CSV of `HH:MM:SS:FF`
   timecodes (pass the video's frame rate with `--fps`).
4. Build the Windows exe and installer.
   ```shell
   packaging\scripts\build_exe.bat
   ```
   The version comes from `APP_VERSION` in `main.py`; keep
   `packaging/pyinstaller/version_info.txt` in sync when you bump it.
