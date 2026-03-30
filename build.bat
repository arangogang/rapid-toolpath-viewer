@echo off
setlocal

echo === ABB RAPID Toolpath Viewer - Windows Build ===
echo.

REM 기존 빌드 산출물 정리
echo [1/3] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

REM PyInstaller 빌드
echo [2/3] Running PyInstaller...
python -m PyInstaller rapid_viewer.spec
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    exit /b 1
)

REM 결과 확인
echo [3/3] Verifying output...
if exist dist\rapid_viewer.exe (
    echo.
    echo Build successful!
    echo Output: dist\rapid_viewer.exe
    for %%F in (dist\rapid_viewer.exe) do echo Size:   %%~zF bytes
) else (
    echo ERROR: dist\rapid_viewer.exe not found.
    exit /b 1
)

endlocal
