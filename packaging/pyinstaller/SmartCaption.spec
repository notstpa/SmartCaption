# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

BASE_DIR = os.path.abspath(os.getcwd())

datas = [
    (os.path.join(BASE_DIR, "THIRD_PARTY_NOTICES.md"), "."),
    (os.path.join(BASE_DIR, "icon.ico"), "."),
    (os.path.join(BASE_DIR, "dropdown_arrow.svg"), "."),
    (os.path.join(BASE_DIR, "checkbox_check.svg"), "."),
]
binaries = []
hiddenimports = []
icon_path = os.path.join(BASE_DIR, "icon.ico")
if not os.path.exists(icon_path):
    icon_path = None

for package_name in ("PyQt6", "faster_whisper"):
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
    excludes=[],
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
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
