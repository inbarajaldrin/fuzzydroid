"""Shared log formatting for fuzzydroid plugins.

Keeps output consistent across every plugin's /setup and /doctor commands.
Minimal for v0 — just prefixed prints with severity markers.
"""
from __future__ import annotations

import sys
from typing import TextIO

__all__ = ["Logger"]


class Logger:
    """A small prefixed logger that writes to a stream.

    Usage:
        log = Logger("fusion")
        log.info("Starting setup")
        log.success("Venv ready")
        log.warning("New deps detected")
        log.error("mklink failed")
    """

    def __init__(
        self,
        plugin: str,
        stream: TextIO | None = None,
    ) -> None:
        self.plugin = plugin
        self.stream = stream if stream is not None else sys.stdout

    def _write(self, marker: str, message: str) -> None:
        self.stream.write(f"[{self.plugin}] {marker} {message}\n")

    def info(self, message: str) -> None:
        self._write("·", message)

    def success(self, message: str) -> None:
        self._write("✅", message)

    def warning(self, message: str) -> None:
        self._write("⚠  WARNING", message)

    def error(self, message: str) -> None:
        self._write("❌ ERROR", message)
