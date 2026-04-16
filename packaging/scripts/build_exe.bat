@echo off
title SmartCaption Build Menu
setlocal

cd /d "%~dp0\..\.."

set APP_NAME=SmartCaption
set APP_VERSION=1.0.0

:menu
cls
echo ========================================
echo   %APP_NAME% Build Menu
echo   Current Version: %APP_VERSION%
echo ========================================
echo.
echo   1. Build App EXE
echo   2. Build Installer
echo   3. Build App + Installer
echo   4. Clean Build Folders
echo   5. Exit
echo.
set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" goto build_app_only
if "%choice%"=="2" goto build_installer_only
if "%choice%"=="3" goto build_all
if "%choice%"=="4" goto clean_folders
if "%choice%"=="5" goto end
goto menu

:ensure_python_deps
python -m pip install pyinstaller customtkinter faster-whisper huggingface_hub tkinterdnd2 av ctranslate2 numpy tokenizers tqdm
if errorlevel 1 (
    echo.
    echo Failed to install build dependencies.
    pause
    exit /b 1
)
exit /b 0

:prepare_dirs
if not exist "build" mkdir "build"
if not exist "build\SmartCaption" mkdir "build\SmartCaption"
if not exist "releases" mkdir "releases"
exit /b 0

:build_app
call :prepare_dirs
call :ensure_python_deps

python -m PyInstaller --noconfirm --distpath releases --workpath build\SmartCaption packaging\pyinstaller\SmartCaption.spec
if errorlevel 1 (
    echo.
    echo Build failed.
    exit /b 1
)

echo.
echo App build complete.
echo EXE: releases\SmartCaption.exe
exit /b 0

:build_installer
set ISCC_PATH=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC_PATH=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC_PATH=%ProgramFiles%\Inno Setup 6\ISCC.exe
if exist "%ProgramFiles(x86)%\Inno Setup 5\ISCC.exe" set ISCC_PATH=%ProgramFiles(x86)%\Inno Setup 5\ISCC.exe
if exist "%ProgramFiles%\Inno Setup 5\ISCC.exe" set ISCC_PATH=%ProgramFiles%\Inno Setup 5\ISCC.exe

if "%ISCC_PATH%"=="" (
    echo.
    echo Inno Setup was not found.
    echo Install it from: https://jrsoftware.org/isdl.php
    exit /b 1
)

if not exist "releases\SmartCaption.exe" (
    echo.
    echo releases\SmartCaption.exe not found. Build the app first.
    exit /b 1
)

call :prepare_dirs
"%ISCC_PATH%" "packaging\installer\installer.iss"
if errorlevel 1 (
    echo.
    echo Installer build failed.
    exit /b 1
)

echo.
echo Installer build complete.
echo Installer: releases\SmartCaption.v%APP_VERSION%-Installer.exe
exit /b 0

:build_app_only
cls
echo ========================================
echo   Building App EXE
echo ========================================
call :build_app
echo.
pause
goto menu

:build_installer_only
cls
echo ========================================
echo   Building Installer
echo ========================================
call :build_installer
echo.
pause
goto menu

:build_all
cls
echo ========================================
echo   Building App + Installer
echo ========================================
call :build_app
if errorlevel 1 (
    echo.
    pause
    goto menu
)
call :build_installer
echo.
pause
goto menu

:clean_folders
cls
echo ========================================
echo   Cleaning Build Folders
echo ========================================
if exist build rmdir /s /q build 2>nul
if exist releases rmdir /s /q releases 2>nul
echo.
echo Clean complete.
echo.
pause
goto menu

:end
exit
