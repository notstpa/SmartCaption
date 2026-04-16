# SmartCaption v1.0.0

![SmartCaption Screenshot](https://via.placeholder.com/1280x720?text=SmartCaption+Screenshot)

[Download Here](https://github.com/yourusername/SmartCaption/releases)

# Features
- **Subtitle Generation**: Create `.srt` subtitles from audio and video files.
- **Built-In Model Downloads**: Download and delete Whisper models directly in the app.
- **Multiple Model Options**: Choose from `tiny`, `base`, `small`, `medium`, and `large-v3`.
- **Word-Level Timing**: Generate tighter subtitle timing using word timestamps.
- **Flexible Subtitle Splitting**: Control max words and max characters per line.
- **Text Cleanup Tools**: Remove punctuation or force lowercase/uppercase output.
- **Language Selection**: Pick the transcription language from the app UI.
- **Advanced Controls**: Tune beam size, no-speech threshold, and context handling.
- **Drag and Drop**: Drop supported media files straight into the window.
- **Installer Included**: Build a Windows installer for a simpler setup experience.

![SmartCaption Screenshot](https://via.placeholder.com/1280x720?text=SmartCaption+UI)

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
   pip install customtkinter faster-whisper huggingface_hub tkinterdnd2 av ctranslate2 numpy tokenizers tqdm pyinstaller
   ```
2. Install Inno Setup if you want to build the installer.
   - **Note:** The installer build uses `ISCC.exe` from Inno Setup.
   - If you only want the app EXE, you can skip this.
3. Run the build menu batch script.
   ```shell
   build_exe.bat
   ```
4. The output is generated in the `releases/` folder.

## Build Options
The batch menu lets you build:
- App EXE only
- Installer only
- App EXE + Installer
- Clean build folders

Use the batch menu for local builds and keep the repo source files clean.

## Notes
- Supported formats include `mp3`, `wav`, `m4a`, `flac`, `aac`, `ogg`, `wma`, `mp4`, `mkv`, `mov`, `avi`, `webm`, `mpeg`, `mpg`, and `m4v`.
- Models are stored in the app's `models` folder when writable. If not, the app falls back to `%LOCALAPPDATA%\SmartCaption\models`.
- The installer is configured to create a writable `models` folder inside the installed app directory.
