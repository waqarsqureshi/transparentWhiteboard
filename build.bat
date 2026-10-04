@echo off
echo ========================================================
echo  Transparent Whiteboard - Automated Windows .exe Builder
echo ========================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in PATH!
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install requirements.
    pause
    exit /b 1
)

echo.
echo [2/3] Building standalone Windows executable via PyInstaller...
python -m PyInstaller --clean -y TransparentWhiteboard.spec
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller failed!
    pause
    exit /b 1
)

echo.
echo [3/3] Verifying generated executable...
if exist "dist\TransparentWhiteboard\TransparentWhiteboard.exe" (
    echo.
    echo ========================================================
    echo  [SUCCESS] TransparentWhiteboard.exe successfully generated!
    echo  Location: dist\TransparentWhiteboard\TransparentWhiteboard.exe
    echo ========================================================
    echo.
    set /p launch="Launch now? (Y/N): "
    if /i "%launch%"=="Y" (
        start "" "dist\TransparentWhiteboard\TransparentWhiteboard.exe"
    )
) else (
    echo [ERROR] Executable not found.
)
pause
