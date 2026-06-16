#!/usr/bin/env bash
# Publish the local repo to a GitHub remote and push a v0.1.0 tag.
#
# Prerequisites (one-time setup):
#   1. Create an empty GitHub repository (no README / .gitignore / license).
#   2. Generate a Personal Access Token (classic) at:
#        https://github.com/settings/tokens/new
#      with `repo` scope. Copy the token once — you can't see it again.
#
# This script will:
#   - Add the remote
#   - Push main
#   - Create and push tag v0.1.0 (triggers the release workflow)
#
# When Git asks for credentials, type your GitHub username and paste
# the PAT as the password. macOS Keychain will remember it for the next push.

set -euo pipefail

read -r -p "GitHub username or org (e.g. yourname): " OWNER
read -r -p "Repository name (e.g. markitdown-gui): " REPO
VERSION="0.1.0"

if [ -z "$OWNER" ] || [ -z "$REPO" ]; then
    echo "[ERROR] Owner and repo name are required."
    exit 1
fi

REMOTE_URL="https://github.com/${OWNER}/${REPO}.git"

echo
echo "[publish] Remote URL: ${REMOTE_URL}"
echo "[publish] Tag:        v${VERSION}"
echo

# Make sure we're on main (create if needed)
if ! git show-ref --verify --quiet refs/heads/main; then
    git checkout -b main
else
    git checkout main
fi

echo "[publish] Adding remote..."
git remote remove origin 2>/dev/null || true
git remote add origin "${REMOTE_URL}"

echo "[publish] Pushing main to ${REMOTE_URL} ..."
if ! git push -u origin main; then
    echo
    echo "[ERROR] Push failed. Common causes:"
    echo "  - Wrong owner/repo name"
    echo "  - Repo already exists with commits (delete and re-create empty, or 'git push -f')"
    echo "  - Authentication failed: when prompted, use your GitHub username + the PAT as password"
    exit 1
fi

echo "[publish] Creating tag v${VERSION}..."
git tag -a "v${VERSION}" -m "v${VERSION} — first public release with markitdown-gui"

echo "[publish] Pushing tag (this triggers GitHub Actions release workflow)..."
git push origin "v${VERSION}"

echo
echo "[publish] Done! Next steps:"
echo "  1. Open https://github.com/${OWNER}/${REPO}/actions to watch the build"
echo "  2. Wait ~5-10 minutes for both Windows and macOS builds"
echo "  3. Open https://github.com/${OWNER}/${REPO}/releases/tag/v${VERSION} for the Release"
echo
