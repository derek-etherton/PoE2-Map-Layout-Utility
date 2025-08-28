# PoE Campaign Layouts - Build Script (PowerShell)
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host " PoE Campaign Layouts - Build Script" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host

# Check if PyInstaller is installed
Write-Host "Checking PyInstaller installation..." -ForegroundColor Yellow
try {
    python -c "import PyInstaller" 2>$null
    if ($LASTEXITCODE -ne 0) { throw }
    Write-Host "✓ PyInstaller is installed" -ForegroundColor Green
} catch {
    Write-Host "× PyInstaller not found, installing..." -ForegroundColor Red
    pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install PyInstaller" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "✓ PyInstaller installed successfully" -ForegroundColor Green
}

# Clean previous builds
Write-Host "Cleaning previous builds..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
Get-ChildItem "*.spec" -ErrorAction SilentlyContinue | Remove-Item -Force

Write-Host
Write-Host "Building Overlay Mode executable..." -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan

$overlayArgs = @(
    "-m", "PyInstaller",
    "--onefile",
    "--windowed", 
    "--name", "PoE_Campaign_Layouts",
    "--exclude-module", "numpy",
    "--exclude-module", "matplotlib", 
    "--exclude-module", "scipy",
    "--exclude-module", "pandas",
    "--exclude-module", "tensorflow",
    "--exclude-module", "torch",
    "poe_campaign_layouts.py"
)

& python @overlayArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to build overlay mode executable" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✓ Overlay mode executable built successfully" -ForegroundColor Green

Write-Host
Write-Host "Building Windowed Mode executable..." -ForegroundColor Cyan  
Write-Host "===================================" -ForegroundColor Cyan

$windowedArgs = @(
    "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--name", "PoE_Campaign_Layouts_Windowed", 
    "--exclude-module", "numpy",
    "--exclude-module", "matplotlib",
    "--exclude-module", "scipy", 
    "--exclude-module", "pandas",
    "--exclude-module", "tensorflow",
    "--exclude-module", "torch",
    "poe_campaign_layouts_windowed.py"
)

& python @windowedArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to build windowed mode executable" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✓ Windowed mode executable built successfully" -ForegroundColor Green

Write-Host
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host " Build Complete!" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host

# Display file information
if (Test-Path "dist\PoE_Campaign_Layouts.exe") {
    $overlaySize = (Get-Item "dist\PoE_Campaign_Layouts.exe").Length
    $overlaySizeMB = [math]::Round($overlaySize / 1MB, 1)
    Write-Host "Overlay Mode: PoE_Campaign_Layouts.exe ($overlaySizeMB MB)" -ForegroundColor Green
}

if (Test-Path "dist\PoE_Campaign_Layouts_Windowed.exe") {
    $windowedSize = (Get-Item "dist\PoE_Campaign_Layouts_Windowed.exe").Length  
    $windowedSizeMB = [math]::Round($windowedSize / 1MB, 1)
    Write-Host "Windowed Mode: PoE_Campaign_Layouts_Windowed.exe ($windowedSizeMB MB)" -ForegroundColor Green
}

Write-Host
Write-Host "Executables are located in the 'dist' folder" -ForegroundColor Yellow
Write-Host "Ready for release! 🎉" -ForegroundColor Green
Write-Host
Read-Host "Press Enter to exit"
