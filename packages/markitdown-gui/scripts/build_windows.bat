@echo off
REM Build MarkItDown GUI for Windows using flet pack.
REM Produces dist\MarkItDown\MarkItDown.exe (and supporting files).

setlocal
cd /d "%~dp0\.."

if not exist "assets\icon.png" (
    echo [ERROR] assets\icon.png not found. Add a 256x256 PNG before building.
    exit /b 1
)

echo [build] Cleaning previous build artifacts...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo [build] Running flet pack...
flet pack ^
  --name "MarkItDown" ^
  --product-name "MarkItDown" ^
  --product-version "0.1.0" ^
  --file-description "Convert files to Markdown" ^
  --copyright "MIT License" ^
  --icon "assets\icon.png" ^
  --add-data "assets;assets" ^
  --hidden-import "magika" ^
  --hidden-import "magika._config" ^
  src\markitdown_gui\__main__.py

if errorlevel 1 (
    echo [ERROR] flet pack failed.
    exit /b 1
)

echo.
echo [build] Done. Run dist\MarkItDown\MarkItDown.exe to test.

endlocal
