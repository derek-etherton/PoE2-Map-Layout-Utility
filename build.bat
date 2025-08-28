@echo off
echo =====================================
echo  PoE Campaign Layouts - Build Script
echo =====================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: PyInstaller is not installed
    echo Installing PyInstaller...
    pip install pyinstaller
    if %ERRORLEVEL% neq 0 (
        echo Failed to install PyInstaller
        pause
        exit /b 1
    )
)

REM Clean previous builds
echo Cleaning previous builds...
if exist "build" rmdir /s /q "build"

REM Backup settings.json if it exists
set "SETTINGS_BACKUP="
if exist "dist\settings.json" (
    echo Backing up existing settings.json...
    copy "dist\settings.json" "settings_backup.json" >nul
    set "SETTINGS_BACKUP=1"
)

if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del /q "*.spec"

echo.
echo Building PoE Campaign Layouts executable...
echo ===================================
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "poe_campaign_layouts" ^
    --add-data "data;data" ^
    --add-data "images;images" ^
    --exclude-module numpy ^
    --exclude-module matplotlib ^
    --exclude-module scipy ^
    --exclude-module pandas ^
    --exclude-module tensorflow ^
    --exclude-module torch ^
    poe_campaign_layouts.py

if %ERRORLEVEL% neq 0 (
    echo Failed to build executable
    pause
    exit /b 1
)

echo.
echo =====================================
echo  Build Complete!
echo =====================================
echo.

REM Display file size
if exist "dist\poe_campaign_layouts.exe" (
    for %%A in ("dist\poe_campaign_layouts.exe") do (
        set size=%%~zA
        call :FormatSize !size! formattedSize
        echo PoE Campaign Layouts: poe_campaign_layouts.exe (!formattedSize!)
    )
)

REM Restore settings.json if we backed it up
if defined SETTINGS_BACKUP (
    echo Restoring settings.json...
    copy "settings_backup.json" "dist\settings.json" >nul
    del "settings_backup.json" >nul
    echo ✓ Previous settings preserved
)

echo.
echo Executables are located in the 'dist' folder
echo Ready for release!
echo.
pause
exit /b 0

:FormatSize
setlocal enabledelayedexpansion
set size=%1
if !size! geq 1073741824 (
    set /a gb=!size!/1073741824
    set /a remainder=!size!%%1073741824*100/1073741824
    set "result=!gb!.!remainder:~0,1! GB"
) else if !size! geq 1048576 (
    set /a mb=!size!/1048576
    set /a remainder=!size!%%1048576*100/1048576
    set "result=!mb!.!remainder:~0,1! MB"
) else if !size! geq 1024 (
    set /a kb=!size!/1024
    set "result=!kb! KB"
) else (
    set "result=!size! bytes"
)
endlocal & set "%2=%result%"
goto :eof
