"""Session management with undo/redo for the Fusion 360 CLI.

Tracks the working session state (last project, last document, command history)
and provides undo/redo over session actions. Persists to a JSON file on disk.
"""

import json
import os
import time
from pathlib import Path

MAX_UNDO_DEPTH = 50
DEFAULT_SESSION_DIR = Path.home() / ".cli-anything-fusion"


def _locked_save_json(path: str, data: dict, **dump_kwargs) -> None:
    """Atomically write JSON with exclusive file locking."""
    try:
        f = open(path, "r+")
    except FileNotFoundError:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        f = open(path, "w")
    with f:
        _locked = False
        try:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            _locked = True
        except (ImportError, OSError):
            pass
        try:
            f.seek(0)
            f.truncate()
            json.dump(data, f, **dump_kwargs)
            f.flush()
        finally:
            if _locked:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class Session:
    """Stateful CLI session with undo/redo and command history."""

    def __init__(self, session_file: str | None = None):
        self.session_file = session_file or str(
            DEFAULT_SESSION_DIR / "session.json"
        )
        self.last_project: str | None = None
        self.last_document: str | None = None
        self.command_history: list[dict] = []
        self.undo_stack: list[dict] = []
        self.redo_stack: list[dict] = []

    def _to_dict(self) -> dict:
        return {
            "last_project": self.last_project,
            "last_document": self.last_document,
            "command_history": self.command_history,
            "undo_stack": self.undo_stack,
            "redo_stack": self.redo_stack,
            "timestamp": time.time(),
        }

    def save(self) -> None:
        """Persist session state to disk."""
        _locked_save_json(self.session_file, self._to_dict(), indent=2)

    def load(self) -> None:
        """Restore session state from disk."""
        if not os.path.isfile(self.session_file):
            return
        try:
            with open(self.session_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return
        self.last_project = data.get("last_project")
        self.last_document = data.get("last_document")
        self.command_history = data.get("command_history", [])
        self.undo_stack = data.get("undo_stack", [])
        self.redo_stack = data.get("redo_stack", [])

    def push_state(self, action: str, data: dict) -> None:
        """Push current action to the undo stack.

        Args:
            action: Description of the action (e.g. 'open_file', 'export_step').
            data: Action data to store for undo.
        """
        entry = {
            "action": action,
            "data": data,
            "timestamp": time.time(),
        }
        self.undo_stack.append(entry)
        if len(self.undo_stack) > MAX_UNDO_DEPTH:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self.command_history.append(entry)

    def undo(self) -> dict | None:
        """Pop from undo stack and push to redo. Returns the undone entry or None."""
        if not self.undo_stack:
            return None
        entry = self.undo_stack.pop()
        self.redo_stack.append(entry)
        return entry

    def redo(self) -> dict | None:
        """Pop from redo stack and push to undo. Returns the redone entry or None."""
        if not self.redo_stack:
            return None
        entry = self.redo_stack.pop()
        self.undo_stack.append(entry)
        return entry

    def get_history(self) -> list[dict]:
        """Return the full command history."""
        return list(self.command_history)
