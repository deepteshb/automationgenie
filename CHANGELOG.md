## Commit: new changes added
**Hash:** 23b31ef84340d2bd851b9a98df3b27c0657fee3b | **Date:** 2025-08-19 15:46:00

### File: `.git-changelog/test.txtgit`
- **Changed Code:** `# @changelog: Testing Change Log`
- **Reason:** Testing Change Log

### File: `.git-changelog/test.txtgit`
- **Changed Code:** `adding another line of code.`

### File: `.git-changelog/test.txtgit`
- **Changed Code:** ``


---

## Commit: new changes added
**Hash:** 7a50fa65561ffb31c7ec7c7badf30a2359ed8231 | **Date:** 2025-08-19 15:43:01

### File: `.git-changelog/test.txtgit`
- **Changed Code:** `# @changelog: Testing Change Log`
- **Reason:** Testing Change Log

### File: `.git-changelog/test.txtgit`
- **Changed Code:** `adding another line of code.`

### File: `.git-changelog/test.txtgit`
- **Changed Code:** ``


---

#!/bin/sh
echo "Running changelog generator..."

# Get repo root
REPO_ROOT="$(git rev-parse --show-toplevel)"
CHANGELOG_SCRIPT="$REPO_ROOT/.git-changelog/generate_changelog.py"
CHANGELOG_FILE="$REPO_ROOT/CHANGELOG.md"

# Detect Python (Windows venv, Linux/Mac venv, or fallback)
if [ -f "$REPO_ROOT/venv/Scripts/python.exe" ]; then
    PYTHON_CMD="$REPO_ROOT/venv/Scripts/python.exe"
elif [ -f "$REPO_ROOT/venv/bin/python" ]; then
    PYTHON_CMD="$REPO_ROOT/venv/bin/python"
else
    PYTHON_CMD="python3"
fi

# Run generator
"$PYTHON_CMD" "$CHANGELOG_SCRIPT"

# Stage changelog
git add "$CHANGELOG_FILE"

# Amend last commit if changelog changed
if ! git diff --cached --quiet "$CHANGELOG_FILE"; then
    git commit --amend --no-edit --no-verify
    echo "CHANGELOG.md updated and commit amended."
else
    echo "No changes in CHANGELOG.md."
fi
