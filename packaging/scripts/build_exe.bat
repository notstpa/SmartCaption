@echo off
setlocal enabledelayedexpansion
title SmartCaption Build Menu

cd /d "%~dp0\..\.."

set "APP_NAME=SmartCaption"
set "DEFAULT_APP_VERSION=1.0.0"
set "VERSION_FILE=packaging\scripts\last_version.txt"

set "APP_VERSION=%DEFAULT_APP_VERSION%"
if exist "%VERSION_FILE%" (
    set /p APP_VERSION=<"%VERSION_FILE%"
)
if "!APP_VERSION!"=="" set "APP_VERSION=%DEFAULT_APP_VERSION%"

:menu
cls
echo ========================================
echo   %APP_NAME% Build Menu
echo   Current Version: !APP_VERSION!
echo ========================================
echo.
echo   1. Build App EXE
echo   2. Build Installer
echo   3. Build App + Installer
echo   4. Clean Build Folders
echo   5. Exit
echo.
set "choice="
set /p choice="Enter your choice (1-5): "
if "!choice!"=="1" goto build_app_only
if "!choice!"=="2" goto build_installer_only
if "!choice!"=="3" goto build_all
if "!choice!"=="4" goto clean_folders
if "!choice!"=="5" goto end
goto menu

:build_app_only
cls
echo ========================================
echo   Building App EXE
echo ========================================
call :get_version
call :ensure_python_deps
if !errorlevel! neq 0 (
    echo.
    pause
    goto menu
)
call :run_pyinstaller
if !errorlevel! neq 0 (
    echo.
    echo Build failed.
    echo.
    pause
    goto menu
)
echo.
echo App build complete.
echo EXE: releases\SmartCaption.exe
echo.
pause
goto menu

:build_installer_only
cls
echo ========================================
echo   Building Installer
echo ========================================
call :get_version
call :run_inno_setup
if !errorlevel! neq 0 (
    echo.
    pause
    goto menu
)
echo.
echo Installer build complete.
echo Installer: releases\SmartCaption.v!APP_VERSION!-Installer.exe
echo.
pause
goto menu

:build_all
cls
echo ========================================
echo   Building App + Installer
echo ========================================
call :get_version
call :ensure_python_deps
if !errorlevel! neq 0 (
    echo.
    pause
    goto menu
)
call :run_pyinstaller
if !errorlevel! neq 0 (
    echo.
    echo App build failed.
    echo.
    pause
    goto menu
)
call :run_inno_setup
if !errorlevel! neq 0 (
    echo.
    pause
    goto menu
)
echo.
echo App + Installer build complete.
echo.
pause
goto menu

:clean_folders
cls
echo ========================================
echo   Cleaning Build Folders
echo ========================================
echo.
echo This will delete the "build" and "releases" folders.
echo.
set "confirm="
set /p confirm="Are you sure? (Y/N): "
if /i not "!confirm!"=="Y" goto menu
echo.
if exist "build" (
    echo Deleting build\...
    rmdir /s /q "build"
    if exist "build" (
        echo   WARNING: Could not fully delete build folder - some files may be in use.
    ) else (
        echo   Done.
    )
) else (
    echo build\ - not found, skipping.
)
if exist "releases" (
    echo Deleting releases\...
    rmdir /s /q "releases"
    if exist "releases" (
        echo   WARNING: Could not fully delete releases folder - some files may be in use.
    ) else (
        echo   Done.
    )
) else (
    echo releases\ - not found, skipping.
)
echo.
echo Clean complete.
echo.
pause
goto menu

:end
exit /b 0

rem ================================================================
rem  Subroutines - only reachable via CALL, never by fall-through
rem ================================================================

:get_version
echo.
echo Current version: !APP_VERSION!
set "VERSION_INPUT="
set /p VERSION_INPUT="Enter version number [!APP_VERSION!]: "
if not "!VERSION_INPUT!"=="" set "APP_VERSION=!VERSION_INPUT!"
if "!APP_VERSION!"=="" set "APP_VERSION=%DEFAULT_APP_VERSION%"
>"!VERSION_FILE!" echo !APP_VERSION!
echo Version set to !APP_VERSION!.
exit /b 0

:ensure_python_deps
python -m pip install pyinstaller PyQt6 pyqtdarktheme faster-whisper huggingface_hub av ctranslate2
if !errorlevel! neq 0 (
    echo.
    echo Failed to install build dependencies.
    exit /b 1
)
exit /b 0

:run_pyinstaller
if not exist "build" mkdir "build"
if not exist "build\SmartCaption" mkdir "build\SmartCaption"
if not exist "releases" mkdir "releases"
python -m PyInstaller --noconfirm --distpath releases --workpath build\SmartCaption packaging\pyinstaller\SmartCaption.spec
exit /b !errorlevel!

:run_inno_setup
set "ISCC_PATH="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_PATH=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_PATH=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles(x86)%\Inno Setup 5\ISCC.exe" set "ISCC_PATH=%ProgramFiles(x86)%\Inno Setup 5\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 5\ISCC.exe" set "ISCC_PATH=%ProgramFiles%\Inno Setup 5\ISCC.exe"
if "!ISCC_PATH!"=="" (
    echo.
    echo Inno Setup not found. Install from: https://jrsoftware.org/isdl.php
    exit /b 1
)
if not exist "releases\SmartCaption.exe" (
    echo.
    echo releases\SmartCaption.exe not found. Build the app first.
    exit /b 1
)
if not exist "releases" mkdir "releases"
"!ISCC_PATH!" /DMyAppVersion="!APP_VERSION!" "packaging\installer\installer.iss"
exit /b !errorlevel!
