@echo off
REM Publish the local repo to a GitHub remote and push a v0.1.0 tag.
REM
REM Prerequisites (one-time setup):
REM   1. Create an empty GitHub repository (no README / .gitignore / license).
REM   2. Generate a Personal Access Token (classic) at:
REM        https://github.com/settings/tokens/new
REM      with `repo` scope. Copy the token once — you can't see it again.
REM
REM This script will:
REM   - Add the remote
REM   - Push main
REM   - Create and push tag v0.1.0 (triggers the release workflow)
REM
REM When Git asks for credentials, type your GitHub username and paste
REM the PAT as the password. Windows' credential manager will remember
REM it for the next push.

setlocal

set /p OWNER=GitHub username or org (e.g. yourname):
set /p REPO=Repository name (e.g. markitdown-gui):
set VERSION=0.1.0

if "%OWNER%"=="" (
    echo [ERROR] Owner is required.
    exit /b 1
)
if "%REPO%"=="" (
    echo [ERROR] Repo name is required.
    exit /b 1
)

set REMOTE_URL=https://github.com/%OWNER%/%REPO%.git

echo.
echo [publish] Remote URL: %REMOTE_URL%
echo [publish] Tag:        v%VERSION%
echo.

REM Make sure we're on main and clean
git checkout main 2>nul
if errorlevel 1 (
    git checkout -b main
)

echo [publish] Adding remote...
git remote remove origin 2>nul
git remote add origin %REMOTE_URL%

echo [publish] Pushing main to %REMOTE_URL% ...
git push -u origin main
if errorlevel 1 (
    echo.
    echo [ERROR] Push failed. Common causes:
    echo   - Wrong owner/repo name
    echo   - Repo already exists with commits (delete and re-create empty, or `git push -f`)
    echo   - Authentication failed: when prompted, use your GitHub username + the PAT as password
    exit /b 1
)

echo [publish] Creating tag v%VERSION%...
git tag -a v%VERSION% -m "v%VERSION% — first public release with markitdown-gui"

echo [publish] Pushing tag (this triggers GitHub Actions release workflow)...
git push origin v%VERSION%
if errorlevel 1 (
    echo [ERROR] Tag push failed.
    exit /b 1
)

echo.
echo [publish] Done! Next steps:
echo   1. Open https://github.com/%OWNER%/%REPO%/actions to watch the build
echo   2. Wait ~5-10 minutes for both Windows and macOS builds
echo   3. Open https://github.com/%OWNER%/%REPO%/releases/tag/v%VERSION% for the Release
echo.

endlocal
