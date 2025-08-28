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
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del /q "*.spec"

echo.
echo Building Overlay Mode executable...
echo ===================================
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "PoE_Campaign_Layouts" ^
    --exclude-module numpy ^
    --exclude-module matplotlib ^
    --exclude-module scipy ^
    --exclude-module pandas ^
    --exclude-module tensorflow ^
    --exclude-module torch ^
    poe_campaign_layouts.py

if %ERRORLEVEL% neq 0 (
    echo Failed to build overlay mode executable
    pause
    exit /b 1
)

echo.
echo Building Windowed Mode executable...
echo ===================================
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "PoE_Campaign_Layouts_Windowed" ^
    --exclude-module numpy ^
    --exclude-module matplotlib ^
    --exclude-module scipy ^
    --exclude-module pandas ^
    --exclude-module tensorflow ^
    --exclude-module torch ^
    poe_campaign_layouts_windowed.py

if %ERRORLEVEL% neq 0 (
    echo Failed to build windowed mode executable
    pause
    exit /b 1
)

echo.
echo =====================================
echo  Build Complete!
echo =====================================
echo.

REM Display file sizes
if exist "dist\PoE_Campaign_Layouts.exe" (
    for %%A in ("dist\PoE_Campaign_Layouts.exe") do (
        set size=%%~zA
        call :FormatSize !size! formattedSize
        echo Overlay Mode: PoE_Campaign_Layouts.exe (!formattedSize!)
    )
)

if exist "dist\PoE_Campaign_Layouts_Windowed.exe" (
    for %%A in ("dist\PoE_Campaign_Layouts_Windowed.exe") do (
        set size=%%~zA
        call :FormatSize !size! formattedSize
        echo Windowed Mode: PoE_Campaign_Layouts_Windowed.exe (!formattedSize!)
    )
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
