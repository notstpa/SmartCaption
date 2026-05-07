# SmartCaption v2.1.0

![SmartCaption](https://i.imgur.com/ZlAXIdx.png)

[Download Here](https://github.com/notstpa/SmartCaption/releases)

# New This Update
- **Output Tab**: Preview subtitles after transcription, edit inline, and export when ready.
- **Profanity Filter**: Automatically censors profanity in generated subtitles.
- **Gap Fill**: Fills silent gaps for smoother subtitle output.
- **CUDA Support**: GPU acceleration on supported NVIDIA hardware for faster transcription.
- **Native File Dialogs**: Input and output pickers now use the Windows file browser.

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
