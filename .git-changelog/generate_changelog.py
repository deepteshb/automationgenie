import subprocess
from datetime import datetime
from pathlib import Path

CHANGELOG_FILE = Path("CHANGELOG.md")

def run_git_command(cmd):
    """Run a git command and return its output decoded as UTF-8."""
    return subprocess.check_output(
        cmd,
        shell=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    ).strip()

def get_last_commit_hash():
    return run_git_command("git rev-parse HEAD")

def get_commit_message():
    return run_git_command("git log -1 --pretty=%B")

def get_commit_diff():
    # Show the staged changes against HEAD (pre-commit runs before the commit is created)
    # Using --cached ensures we read what is actually going to be committed
    return run_git_command("git diff --cached --unified=0")

def parse_changes(diff_text):
    changes = []
    current_file = None
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            changes.append((current_file, line[1:].strip()))
    return changes

def extract_reason(line):
    if "# @changelog:" in line:
        return line.split("# @changelog:")[1].strip()
    return None

def update_changelog():
    commit_hash = get_last_commit_hash()
    commit_msg = get_commit_message()
    diff_text = get_commit_diff()
    changes = parse_changes(diff_text)

    # Remove entries for the changelog file itself to avoid recursion
    changes = [(f, l) for (f, l) in changes if f and f != "CHANGELOG.md"]

    if not changes:
        return None

    entry_lines = []
    entry_lines.append(f"## Commit: {commit_msg.strip()}")
    entry_lines.append(
        f"**Hash:** {commit_hash} | **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )

    file_count = set()
    line_count = 0
    wrote_any = False

    for file, line in changes:
        file_count.add(file)
        line_count += 1
        reason = extract_reason(line)

        # Write per-file block
        entry_lines.append(f"### File: `{file}`")
        entry_lines.append(f"- **Changed Code:** `{line}`")
        if reason:
            entry_lines.append(f"- **Reason:** {reason}")
        entry_lines.append("")
        wrote_any = True

    if not wrote_any:
        return None

    entry_lines.append("\n---\n")

    old_content = ""
    if CHANGELOG_FILE.exists():
        old_content = CHANGELOG_FILE.read_text(encoding="utf-8")

    # New entries at the top (newest first)
    new_content = "\n".join(entry_lines) + "\n" + old_content
    CHANGELOG_FILE.write_text(new_content, encoding="utf-8")

    return file_count, line_count

if __name__ == "__main__":
    result = update_changelog()
    if result:
        file_count, line_count = result
        print(f"Changelog updated: {len(file_count)} files changed, {line_count} lines modified")
    else:
        print("No changes to record in changelog")
