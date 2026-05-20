"""Tests for fuzzydroid.common.logbook."""
import io

from fuzzydroid.common import logbook as fd_log


class TestLogger:
    def test_info_prints_plugin_prefix(self):
        buf = io.StringIO()
        log = fd_log.Logger("fusion", stream=buf)
        log.info("hello")
        output = buf.getvalue()
        assert "[fusion]" in output
        assert "hello" in output

    def test_error_includes_severity(self):
        buf = io.StringIO()
        log = fd_log.Logger("fusion", stream=buf)
        log.error("something broke")
        output = buf.getvalue()
        assert "ERROR" in output
        assert "something broke" in output

    def test_success_includes_check_mark(self):
        buf = io.StringIO()
        log = fd_log.Logger("fusion", stream=buf)
        log.success("done")
        assert "✅" in buf.getvalue()

    def test_warning_includes_warn_marker(self):
        buf = io.StringIO()
        log = fd_log.Logger("fusion", stream=buf)
        log.warning("watch out")
        assert "⚠" in buf.getvalue()

    def test_multiple_calls_each_emit_newline(self):
        buf = io.StringIO()
        log = fd_log.Logger("fusion", stream=buf)
        log.info("one")
        log.info("two")
        lines = buf.getvalue().splitlines()
        assert len(lines) == 2

    def test_plugin_prefix_uses_given_name(self):
        buf = io.StringIO()
        log = fd_log.Logger("rviz", stream=buf)
        log.info("hi")
        assert "[rviz]" in buf.getvalue()

    def test_default_stream_is_stdout(self):
        log = fd_log.Logger("fusion")
        import sys
        assert log.stream is sys.stdout
