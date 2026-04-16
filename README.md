# SmartCaption

SmartCaption is a Windows desktop app for generating `.srt` subtitles from audio and video files using `faster-whisper`.

It includes a simple GUI for downloading Whisper models, choosing subtitle settings, and exporting subtitle files without using the command line.

## Features

- Generate `.srt` subtitles from audio or video files
- Drag and drop supported files into the app
- Download and delete Whisper models from inside the UI
- Choose from `tiny`, `base`, `small`, `medium`, and `large-v3`
- Word-level subtitle timing support
- Adjustable subtitle splitting with max words and max characters per line
- Text cleanup options like punctuation removal and text case conversion
- Language selection for transcription
- Advanced controls for beam size, no-speech threshold, and context handling
- Built-in Windows installer

## Supported Formats

Audio:

- `mp3`
- `wav`
- `m4a`
- `flac`
- `aac`
- `ogg`
- `wma`

Video:

- `mp4`
- `mkv`
- `mov`
- `avi`
- `webm`
- `mpeg`
- `mpg`
- `m4v`

Actual format support depends on the decoding libraries included in the build.

## How To Use

1. Launch `SmartCaption.exe`.
2. Select or drag in an input audio/video file.
3. Choose an output folder.
4. Pick a model.
5. Click `Download` if that model is not installed yet.
6. Adjust subtitle options if needed.
7. Click `Generate`.

The app writes subtitles as an `.srt` file using the input filename, for example `video.mp4` becomes `video.srt`.

If the output file already exists, SmartCaption lets you overwrite it, create a renamed copy, or cancel.

## Models

Models are downloaded from Hugging Face using the `Systran/faster-whisper-*` repositories.

By default, SmartCaption tries to store models in:

`<app folder>\models`

If that folder is not writable, it falls back to:

`%LOCALAPPDATA%\SmartCaption\models`

The installer in this repo is configured to create a writable `models` folder inside the installed app directory so models can stay with the app.

## Accuracy Tips

- `large-v3` gives the best overall accuracy
- Higher `Beam Size` can help with difficult audio, but it is slower on CPU
- Lower `No Speech Threshold` can help keep quiet speech, but may add noise
- Turning off `Condition On Previous Text` can help if mistakes repeat across segments

Recommended starting point:

- Model: `large-v3`
- Beam Size: `8`
- No Speech Threshold: `0.6`
- Condition On Previous Text: `On`

## Running From Source

Install Python dependencies:

```powershell
python -m pip install customtkinter faster-whisper huggingface_hub tkinterdnd2 av ctranslate2 numpy tokenizers tqdm
```

Run the app:

```powershell
python app.py
```

## Building

This project includes a Windows batch build menu in [build_exe.bat](c:/Users/stopa/Desktop/Repositorys/SmartCaption/build_exe.bat).

It can:

- build the standalone EXE
- build the installer
- build both together
- clean generated build folders

Build dependencies are installed automatically by the script.

To build manually from the menu:

```powershell
.\build_exe.bat
```

Current build outputs go to:

- `releases\SmartCaption.exe`
- `releases\SmartCaption.v1.0.0.exe`
- `releases\SmartCaption.v1.0.0-Installer.exe`
- `releases\THIRD_PARTY_NOTICES.md`

## Installer Notes

- The installer is built with Inno Setup
- It installs SmartCaption under `Program Files`
- It creates a writable `models` subfolder for downloaded models
- The Control Panel uninstall entry is shown as `SmartCaption`

## Tech Stack

- Python
- CustomTkinter
- faster-whisper
- CTranslate2
- huggingface_hub
- tkinterdnd2
- PyAV
- NumPy
- tokenizers
- PyInstaller
- Inno Setup

## License / Notices

This app uses third-party open-source software. Keep `THIRD_PARTY_NOTICES.md` with redistributed builds.
