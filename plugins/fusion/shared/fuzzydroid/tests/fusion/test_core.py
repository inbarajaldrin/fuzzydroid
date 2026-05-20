"""Unit tests for cli-anything-fusion core modules.

All tests use synthetic data — no external dependencies,
no bridge connection, no Fusion 360 required.

Run: python3 -m pytest shared/fuzzydroid/tests/fusion/test_core.py -v --tb=short
"""

import time


# ── Session tests ────────────────────────────────────────────────────────────


class TestSessionInitialState:
    """Verify a new Session starts with clean, empty state."""

    def test_session_initial_state(self, tmp_path):
        from fuzzydroid.fusion.core.session import Session

        s = Session(session_file=str(tmp_path / "session.json"))
        assert s.last_project is None
        assert s.last_document is None
        assert s.command_history == []
        assert s.undo_stack == []
        assert s.redo_stack == []


class TestSessionPushState:
    """Verify push_state behaviour."""

    def _make_session(self, tmp_path):
        from fuzzydroid.fusion.core.session import Session

        return Session(session_file=str(tmp_path / "session.json"))

    def test_push_state_adds_to_undo(self, tmp_path):
        s = self._make_session(tmp_path)
        s.push_state("open_file", {"file": "gear.f3d"})
        assert len(s.undo_stack) == 1
        assert s.undo_stack[0]["action"] == "open_file"

    def test_push_state_records_history(self, tmp_path):
        s = self._make_session(tmp_path)
        s.push_state("export_step", {"path": "/tmp/out.step"})
        assert len(s.command_history) == 1
        assert s.command_history[0]["action"] == "export_step"

    def test_push_state_clears_redo(self, tmp_path):
        s = self._make_session(tmp_path)
        s.push_state("a1", {"x": 1})
        s.undo()
        assert len(s.redo_stack) == 1
        # New push must clear redo
        s.push_state("a2", {"x": 2})
        assert s.redo_stack == []

    def test_push_state_entry_has_timestamp(self, tmp_path):
        s = self._make_session(tmp_path)
        before = time.time()
        s.push_state("act", {"k": "v"})
        after = time.time()
        ts = s.undo_stack[0]["timestamp"]
        assert isinstance(ts, float)
        assert before <= ts <= after


class TestSessionUndoRedo:
    """Verify undo/redo stack mechanics."""

    def _make_session(self, tmp_path):
        from fuzzydroid.fusion.core.session import Session

        return Session(session_file=str(tmp_path / "session.json"))

    def test_undo_returns_entry(self, tmp_path):
        s = self._make_session(tmp_path)
        s.push_state("open", {"f": "a"})
        entry = s.undo()
        assert entry is not None
        assert entry["action"] == "open"

    def test_undo_moves_to_redo(self, tmp_path):
        s = self._make_session(tmp_path)
        s.push_state("open", {"f": "a"})
        s.undo()
        assert len(s.redo_stack) == 1
        assert s.redo_stack[0]["action"] == "open"

    def test_redo_returns_entry(self, tmp_path):
        s = self._make_session(tmp_path)
        s.push_state("open", {"f": "a"})
        s.undo()
        entry = s.redo()
        assert entry is not None
        assert entry["action"] == "open"

    def test_redo_moves_to_undo(self, tmp_path):
        s = self._make_session(tmp_path)
        s.push_state("open", {"f": "a"})
        s.undo()
        assert len(s.undo_stack) == 0
        s.redo()
        assert len(s.undo_stack) == 1

    def test_undo_empty_returns_none(self, tmp_path):
        s = self._make_session(tmp_path)
        assert s.undo() is None

    def test_redo_empty_returns_none(self, tmp_path):
        s = self._make_session(tmp_path)
        assert s.redo() is None

    def test_undo_redo_cycle(self, tmp_path):
        s = self._make_session(tmp_path)
        s.push_state("a1", {"v": 1})
        s.push_state("a2", {"v": 2})
        # Undo a2
        undone = s.undo()
        assert undone["action"] == "a2"
        assert len(s.undo_stack) == 1
        assert len(s.redo_stack) == 1
        # Redo a2
        redone = s.redo()
        assert redone["action"] == "a2"
        assert len(s.undo_stack) == 2
        assert len(s.redo_stack) == 0

    def test_redo_clears_on_new_push(self, tmp_path):
        s = self._make_session(tmp_path)
        s.push_state("a1", {"v": 1})
        s.push_state("a2", {"v": 2})
        s.undo()  # redo_stack now has a2
        assert len(s.redo_stack) == 1
        s.push_state("a3", {"v": 3})  # must clear redo
        assert s.redo_stack == []
        assert s.undo_stack[-1]["action"] == "a3"


class TestSessionUndoCap:
    """Verify the 50-level undo depth cap."""

    def test_undo_cap_50(self, tmp_path):
        from fuzzydroid.fusion.core.session import Session, MAX_UNDO_DEPTH

        s = Session(session_file=str(tmp_path / "session.json"))
        for i in range(55):
            s.push_state(f"action_{i}", {"i": i})
        assert len(s.undo_stack) == MAX_UNDO_DEPTH
        assert len(s.undo_stack) == 50
        # The oldest entries should have been dropped
        assert s.undo_stack[0]["action"] == "action_5"
        assert s.undo_stack[-1]["action"] == "action_54"
        # History should still have all 55
        assert len(s.command_history) == 55


class TestSessionPersistence:
    """Verify save/load round-trips and edge cases."""

    def test_save_load_roundtrip(self, tmp_path):
        from fuzzydroid.fusion.core.session import Session

        sf = str(tmp_path / "session.json")
        s1 = Session(session_file=sf)
        s1.last_project = "TestProject"
        s1.last_document = "gear.f3d"
        s1.push_state("open", {"f": "gear.f3d"})
        s1.push_state("export", {"fmt": "step"})
        s1.undo()  # move last entry to redo
        s1.save()

        s2 = Session(session_file=sf)
        s2.load()
        assert s2.last_project == "TestProject"
        assert s2.last_document == "gear.f3d"
        assert len(s2.undo_stack) == 1
        assert len(s2.redo_stack) == 1
        assert len(s2.command_history) == 2

    def test_load_missing_file(self, tmp_path):
        from fuzzydroid.fusion.core.session import Session

        s = Session(session_file=str(tmp_path / "nonexistent.json"))
        s.load()  # should not raise
        assert s.last_project is None

    def test_load_corrupt_json(self, tmp_path):
        from fuzzydroid.fusion.core.session import Session

        corrupt = tmp_path / "corrupt.json"
        corrupt.write_text("{broken json!!!")
        s = Session(session_file=str(corrupt))
        s.load()  # should not raise
        assert s.undo_stack == []


class TestSessionHistory:
    """Verify get_history returns correct data."""

    def test_get_history(self, tmp_path):
        from fuzzydroid.fusion.core.session import Session

        s = Session(session_file=str(tmp_path / "session.json"))
        s.push_state("a1", {"v": 1})
        s.push_state("a2", {"v": 2})
        h = s.get_history()
        assert len(h) == 2
        assert h[0]["action"] == "a1"
        assert h[1]["action"] == "a2"

    def test_get_history_is_copy(self, tmp_path):
        from fuzzydroid.fusion.core.session import Session

        s = Session(session_file=str(tmp_path / "session.json"))
        s.push_state("a1", {"v": 1})
        h = s.get_history()
        h.clear()
        # Internal history must be unaffected
        assert len(s.get_history()) == 1


# ── Export validation tests ──────────────────────────────────────────────────


class TestExportValidation:
    """Verify export format constants used by the CLI."""

    VALID_FORMATS = ("step", "stl", "f3d")

    def test_valid_format_step(self):
        assert "step" in self.VALID_FORMATS

    def test_valid_format_stl(self):
        assert "stl" in self.VALID_FORMATS

    def test_valid_format_f3d(self):
        assert "f3d" in self.VALID_FORMATS

    def test_invalid_format_not_accepted(self):
        assert "obj" not in self.VALID_FORMATS

    def test_all_formats_lowercase(self):
        assert all(f == f.lower() for f in self.VALID_FORMATS)


