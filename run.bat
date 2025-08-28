@echo off
echo Building PoE Maps Viewer...
dotnet build --configuration Release

if %errorlevel% neq 0 (
    echo Build failed!
    pause
    exit /b 1
)

echo Build successful! Starting application...
dotnet run --configuration Release

pause
