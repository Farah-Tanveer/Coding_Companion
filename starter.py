
from pathlib import Path
from datetime import datetime
import base64
import hashlib
import subprocess
import sys

from cryptography.fernet import Fernet, InvalidToken
from langchain.tools import tool


# ============================================================
# PATHS AND STATE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
WORK_DIR = (BASE_DIR / "work_dir").resolve()
HISTORY_DIR = WORK_DIR / ".history"

WORK_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

PENDING_ACTION = None


# ============================================================
# SAFE PATH HANDLING
# ============================================================

def safe_path(path: str) -> Path:
    """Resolve a path and ensure it remains inside work_dir."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("A non-empty relative file path is required.")

    candidate = Path(path)

    if candidate.is_absolute():
        raise ValueError("Use a relative path inside work_dir.")

    resolved = (WORK_DIR / candidate).resolve()

    if not resolved.is_relative_to(WORK_DIR):
        raise ValueError("Access outside work_dir is not allowed.")

    if resolved == HISTORY_DIR or HISTORY_DIR in resolved.parents:
        raise ValueError("Direct access to backup files is not allowed.")

    return resolved


def relative_path(file_path: Path) -> str:
    return file_path.relative_to(WORK_DIR).as_posix()


def save_backup(file_path: Path) -> Path:
    """Save a copy of an existing file before changing it."""
    if not file_path.is_file():
        raise FileNotFoundError(f"No existing file to back up: {file_path.name}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup = HISTORY_DIR / timestamp / relative_path(file_path)
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_bytes(file_path.read_bytes())
    return backup


def find_backups(file_path: Path) -> list[Path]:
    """Return backups for this file, newest first."""
    rel = relative_path(file_path)
    matches = [
        p for p in HISTORY_DIR.glob(f"*/{rel}")
        if p.is_file()
    ]
    return sorted(matches, key=lambda p: p.parent.name, reverse=True)


def clear_pending_action() -> None:
    global PENDING_ACTION
    PENDING_ACTION = None


# ============================================================
# FILE TOOLS
# ============================================================

@tool
def list_files(path: str = ".") -> str:
    """List files and folders inside work_dir.

    Args:
        path: Relative folder path inside work_dir. Use "." for the root.
    """
    try:
        folder = safe_path(path)
        if not folder.is_dir():
            return f"Error: Not a directory: {path}"

        items = []
        for item in sorted(folder.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if item == HISTORY_DIR or HISTORY_DIR in item.parents:
                continue
            suffix = "/" if item.is_dir() else ""
            items.append(item.name + suffix)

        return "\n".join(items) if items else "The folder is empty."
    except Exception as exc:
        return f"Error listing files: {exc}"


@tool
def read_file(path: str) -> str:
    """Read a UTF-8 text file inside work_dir.

    Args:
        path: Relative file path inside work_dir.
    """
    try:
        file_path = safe_path(path)
        if not file_path.is_file():
            return f"Error: File not found: {path}"
        return file_path.read_text(encoding="utf-8")
    except Exception as exc:
        return f"Error reading file: {exc}"


@tool
def write_file(path: str, content: str) -> str:
    """Create a file or request approval before overwriting an existing file.

    Args:
        path: Required relative file path inside work_dir, such as primes.py.
        content: Complete intended contents of the file, not a diff.
    """
    global PENDING_ACTION

    try:
        file_path = safe_path(path)

        if PENDING_ACTION is not None:
            return (
                "Another action is awaiting approval. Do not start another "
                "write until the pending action is approved or cancelled."
            )

        if file_path.exists() and not file_path.is_file():
            return f"Error: The target exists and is not a file: {path}"

        if file_path.is_file():
            PENDING_ACTION = {
                "type": "overwrite",
                "path": str(file_path),
                "relative_path": relative_path(file_path),
                "content": content,
            }
            return (
                f"OVERWRITE_PENDING: {path} already exists. "
                "The existing file has NOT been modified. Wait for GUI approval."
            )

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"File created successfully: {path}"

    except Exception as exc:
        return f"Error writing file: {exc}"


def approve_pending_action() -> str:
    """Apply the staged overwrite after explicit GUI approval."""
    global PENDING_ACTION

    action = PENDING_ACTION
    if not action or action.get("type") != "overwrite":
        return "Error: No pending overwrite is awaiting approval."

    file_path = safe_path(action["relative_path"])

    # Recheck immediately before writing.
    if not file_path.is_file():
        clear_pending_action()
        return "Error: The original file no longer exists. Nothing was overwritten."

    try:
        save_backup(file_path)
        file_path.write_text(action["content"], encoding="utf-8")
        clear_pending_action()
        return (
            "Overwrite completed successfully: "
            f"{action['relative_path']}. A backup was saved."
        )
    except Exception as exc:
        return f"Error applying approved overwrite: {exc}"


def cancel_pending_action() -> str:
    """Cancel a staged file operation without changing the target."""
    global PENDING_ACTION

    if PENDING_ACTION is None:
        return "There is no pending action to cancel."

    action_type = PENDING_ACTION.get("type", "unknown")
    path = PENDING_ACTION.get("relative_path", "unknown file")
    clear_pending_action()
    return f"Cancelled {action_type} for {path}. The action was not applied."


@tool
def delete_file(path: str) -> str:
    """Request GUI approval before deleting a file.

    Args:
        path: Relative file path inside work_dir.
    """
    global PENDING_ACTION

    try:
        file_path = safe_path(path)

        if PENDING_ACTION is not None:
            return "Another action is already awaiting approval."

        if not file_path.is_file():
            return f"Error: File not found: {path}"

        PENDING_ACTION = {
            "type": "delete",
            "path": str(file_path),
            "relative_path": relative_path(file_path),
        }
        return f"DELETE_PENDING: {path}. The file has NOT been deleted."
    except Exception as exc:
        return f"Error requesting deletion: {exc}"


def approve_delete_action() -> str:
    """Back up and delete a file after explicit GUI approval."""
    global PENDING_ACTION

    action = PENDING_ACTION
    if not action or action.get("type") != "delete":
        return "Error: No pending deletion is awaiting approval."

    file_path = safe_path(action["relative_path"])

    if not file_path.is_file():
        clear_pending_action()
        return "Error: The target file no longer exists."

    try:
        save_backup(file_path)
        file_path.unlink()
        clear_pending_action()
        return f"File deleted successfully: {action['relative_path']}. A backup was saved."
    except Exception as exc:
        return f"Error applying approved deletion: {exc}"


@tool
def run_python_file(path: str) -> str:
    """Run a Python file inside work_dir and return its actual output.

    Args:
        path: Relative path to a Python file inside work_dir.
    """
    try:
        file_path = safe_path(path)

        if file_path.suffix.lower() != ".py":
            return "Error: Only .py files can be run with this tool."

        if not file_path.is_file():
            return f"Error: Python file not found: {path}"

        result = subprocess.run(
            [sys.executable, str(file_path)],
            cwd=str(WORK_DIR),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        return (
            f"Exit code: {result.returncode}\n"
            f"STDOUT:\n{result.stdout or '(no output)'}\n"
            f"STDERR:\n{result.stderr or '(no errors)'}"
        )
    except subprocess.TimeoutExpired:
        return "Error: Program exceeded the 30-second time limit."
    except Exception as exc:
        return f"Error running Python file: {exc}"


@tool
def undo_file(path: str) -> str:
    """Restore the newest available backup of a file inside work_dir.

    Args:
        path: Relative file path to restore.
    """
    try:
        file_path = safe_path(path)
        backups = find_backups(file_path)

        if not backups:
            return (
                f"No backup exists for {path}. Nothing was changed. "
                "Create a backup by modifying the file through DevMate first."
            )

        backup = backups[0]

        if file_path.exists():
            save_backup(file_path)

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(backup.read_bytes())

        return f"Restored {path} from backup {backup.parent.name}."
    except Exception as exc:
        return f"Error undoing file: {exc}"


# ============================================================
# GIT TOOLS
# ============================================================

def run_git(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return result.stdout or result.stderr or f"Git exited with code {result.returncode}."
    except Exception as exc:
        return f"Git error: {exc}"


@tool
def git_status() -> str:
    """Show the current Git status without changing files or committing."""
    return run_git(["status", "--short", "--branch"])


@tool
def git_snapshot(message: str) -> str:
    """Create a Git commit only when the user explicitly requests a snapshot.

    Args:
        message: Commit message.
    """
    if not message.strip():
        return "Error: A commit message is required."

    status = run_git(["status", "--porcelain"])
    if "Git error:" in status or "not a git repository" in status.lower():
        return status

    if not status.strip():
        return "Nothing to commit; the working tree is clean."

    add_result = run_git(["add", "--", "starter.py", "llm.py", "app.py", "work_dir"])
    if "Git error:" in add_result:
        return add_result

    commit_result = run_git(["commit", "-m", message])
    return commit_result


# ============================================================
# PASSWORD PROTECTION
# ============================================================

def derive_key(password: str) -> bytes:
    """Derive a Fernet-compatible key from a password."""
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


@tool
def protect_file(path: str, password: str) -> str:
    """Encrypt a file inside work_dir with a password.

    Args:
        path: Relative file path inside work_dir.
        password: Password used to encrypt the file.
    """
    try:
        file_path = safe_path(path)
        if not file_path.is_file():
            return f"Error: File not found: {path}"
        if not password:
            return "Error: Password cannot be empty."

        save_backup(file_path)
        encrypted = Fernet(derive_key(password)).encrypt(file_path.read_bytes())
        file_path.write_bytes(encrypted)
        return f"File encrypted successfully: {path}. A backup was saved."
    except Exception as exc:
        return f"Error protecting file: {exc}"


@tool
def unprotect_file(path: str, password: str) -> str:
    """Decrypt a password-protected file inside work_dir.

    Args:
        path: Relative file path inside work_dir.
        password: Password used to encrypt the file.
    """
    try:
        file_path = safe_path(path)
        if not file_path.is_file():
            return f"Error: File not found: {path}"
        if not password:
            return "Error: Password cannot be empty."

        decrypted = Fernet(derive_key(password)).decrypt(file_path.read_bytes())
        save_backup(file_path)
        file_path.write_bytes(decrypted)
        return f"File decrypted successfully: {path}. A backup was saved."
    except InvalidToken:
        return "Error: Wrong password or the file is not a valid encrypted file."
    except Exception as exc:
        return f"Error unprotecting file: {exc}"


# ============================================================
# TOOL REGISTRY
# ============================================================

TOOLS = [
    list_files,
    read_file,
    write_file,
    delete_file,
    run_python_file,
    undo_file,
    git_status,
    git_snapshot,
    protect_file,
    unprotect_file,
]
