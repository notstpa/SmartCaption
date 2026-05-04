Third-Party Notices
===================

SmartCaption includes and/or is built with open-source software from the
projects listed below. Keep this file with redistributed builds of the app.

This notice was reviewed on 2026-05-04 against `requirements.txt` and the
package metadata installed in the local build environment. Because
`requirements.txt` uses minimum versions, future builds may resolve newer
versions; refresh this file when dependencies are upgraded.

Direct Runtime Dependencies
---------------------------

- PyQt6 6.11.0
  Project: https://www.riverbankcomputing.com/software/pyqt/
  License: GPL-3.0-only
  Notes: Depends on PyQt6-Qt6 and PyQt6-sip. Confirm the licensing model is
  appropriate for any redistributed build.

- pyqtdarktheme 2.1.0
  Project: https://github.com/5yutan5/PyQtDarkTheme
  Documentation: https://pyqtdarktheme.readthedocs.io
  License: MIT

- faster-whisper 1.2.1
  Project: https://github.com/SYSTRAN/faster-whisper
  License: MIT

- huggingface_hub 1.10.2
  Project: https://github.com/huggingface/huggingface_hub
  License: Apache-2.0

- av 17.0.0
  Project: https://github.com/PyAV-Org/PyAV
  Website: https://pyav.basswood-io.com
  License: BSD-3-Clause
  Notes: PyAV provides Python bindings for FFmpeg libraries. Confirm the exact
  FFmpeg library licensing terms for the binaries included in a release.

- CTranslate2 4.7.1
  Project: https://github.com/OpenNMT/CTranslate2
  Documentation: https://opennmt.net/CTranslate2
  License: MIT

- NumPy 2.4.4
  Project: https://github.com/numpy/numpy
  Website: https://numpy.org
  License: BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0

- tokenizers 0.22.2
  Project: https://github.com/huggingface/tokenizers
  License: Apache-2.0

- tqdm 4.67.3
  Project: https://github.com/tqdm/tqdm
  Website: https://tqdm.github.io
  License: MPL-2.0 AND MIT

Runtime Transitive Dependencies
-------------------------------

The following packages are transitive runtime dependencies reported by the
installed package metadata for the direct dependencies above. Depending on the
exact build and packaging output, some or all may be bundled with the app.

- annotated-doc 0.0.4 - MIT
- anyio 4.13.0 - MIT
- certifi 2026.2.25 - MPL-2.0
- click 8.3.2 - BSD-3-Clause
- colorama 0.4.6 - BSD
- darkdetect 0.7.1 - BSD
- filelock 3.28.0 - MIT
- flatbuffers 25.12.19 - Apache-2.0
- fsspec 2026.3.0 - BSD-3-Clause
- h11 0.16.0 - MIT
- hf-xet 1.4.3 - Apache-2.0
- httpcore 1.0.9 - BSD-3-Clause
- httpx 0.28.1 - BSD-3-Clause
- idna 3.11 - BSD-3-Clause
- markdown-it-py 4.0.0 - MIT
- mdurl 0.1.2 - MIT
- mpmath 1.3.0 - BSD
- onnxruntime 1.24.4 - MIT
- packaging 26.1 - Apache-2.0 OR BSD-2-Clause
- protobuf 6.33.6 - BSD-3-Clause
- Pygments 2.20.0 - BSD-2-Clause
- PyQt6-Qt6 6.11.0 - LGPL-3.0
- PyQt6-sip 13.11.1 - BSD-2-Clause
- PyYAML 6.0.3 - MIT
- rich 15.0.0 - MIT
- setuptools 65.5.0 - MIT
- shellingham 1.5.4 - ISC
- sympy 1.14.0 - BSD
- typer 0.24.1 - MIT
- typing_extensions 4.15.0 - PSF-2.0

Build Tools
-----------

- PyInstaller 6.19.0
  Project: https://pyinstaller.org
  Source: https://github.com/pyinstaller/pyinstaller
  License: GPL-2.0-or-later with a special exception allowing generated
  executables to be distributed under different terms.

Redistribution Notes
--------------------

- Preserve copyright and license notices required by bundled dependencies.
- If a release includes downloaded Whisper model files, review the model
  license for additional attribution or redistribution requirements.
- If a release includes FFmpeg-linked binaries through PyAV or another package,
  confirm the exact FFmpeg configuration and licensing terms for those binaries.
- This file is informational only and is not legal advice.
