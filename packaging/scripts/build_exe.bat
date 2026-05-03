@echo off
title SmartCaption Build Menu
setlocal

cd /d "%~dp0\..\.."

set "APP_NAME=SmartCaption"
set "DEFAULT_APP_VERSION=1.0.0"
set "VERSION_FILE=packaging\scripts\last_version.txt"
call :load_saved_version

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

:load_saved_version
set "APP_VERSION=%DEFAULT_APP_VERSION%"
if exist "%VERSION_FILE%" (
    set /p APP_VERSION=<"%VERSION_FILE%"
)
if "%APP_VERSION%"=="" set "APP_VERSION=%DEFAULT_APP_VERSION%"
exit /b 0

:prompt_app_version
call :load_saved_version
echo.
echo Current saved version: %APP_VERSION%
set "VERSION_INPUT="
set /p VERSION_INPUT="Enter version number [%APP_VERSION%]: "
if not "%VERSION_INPUT%"=="" set "APP_VERSION=%VERSION_INPUT%"
if "%APP_VERSION%"=="" set "APP_VERSION=%DEFAULT_APP_VERSION%"
> "%VERSION_FILE%" echo %APP_VERSION%
echo Version set to %APP_VERSION%.
exit /b 0

:ensure_python_deps
python -m pip install pyinstaller PyQt6 faster-whisper huggingface_hub av ctranslate2 numpy tokenizers tqdm
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
"%ISCC_PATH%" /DMyAppVersion="%APP_VERSION%" "packaging\installer\installer.iss"
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
call :prompt_app_version
call :build_app
echo.
pause
goto menu

:build_installer_only
cls
echo ========================================
echo   Building Installer
echo ========================================
call :prompt_app_version
call :build_installer
echo.
pause
goto menu

:build_all
cls
echo ========================================
echo   Building App + Installer
echo ========================================
call :prompt_app_version
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
