# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

BASE_DIR = os.path.abspath(os.getcwd())

datas = [
    (os.path.join(BASE_DIR, "THIRD_PARTY_NOTICES.md"), "."),
    (os.path.join(BASE_DIR, "icon.ico"), "."),
]
binaries = []
hiddenimports = []
excludes = [
    "PyQt5",
    "PyQt5_sip",
    "PySide2",
    "PySide6",
    "PySide6_Addons",
    "PySide6_Essentials",
    "shiboken2",
    "shiboken6",
    "llvmlite",
    "numba",
    "scipy",
    "tensorflow",
    "torch",
    "torchaudio",
    "torchvision",
]
icon_path = os.path.join(BASE_DIR, "icon.ico")
if not os.path.exists(icon_path):
    icon_path = None

# Embed a Windows version resource so the exe reports a publisher and version
# instead of showing blank properties, which SmartScreen treats as a signal.
version_path = os.path.join(BASE_DIR, "packaging", "pyinstaller", "version_info.txt")
if not os.path.exists(version_path):
    version_path = None

# Packages PyInstaller cannot work out on its own. onnxruntime, av and PyQt6
# are deliberately absent: they ship their own hooks, and collecting them here
# as well only risks pulling in optional submodules that fail to import.
#
# Note the import name, not the distribution name -- pip installs
# "pyqtdarktheme" but the package is "qdarktheme", and collect_all() given the
# wrong one silently returns nothing at all rather than failing the build.
for package_name in (
    "faster_whisper",
    "qdarktheme",
    "ctranslate2",
    "tokenizers",
    "huggingface_hub",
):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package_name)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports


a = Analysis(
    [os.path.join(BASE_DIR, "main.py")],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SmartCaption",
    icon=icon_path,
    version=version_path,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX is a well-known antivirus heuristic trigger on unsigned Qt binaries
    # and can corrupt some native DLLs. The size saving is not worth it.
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
