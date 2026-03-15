"""Tests for the retired `src.cortex` entrypoint."""

# pylint: disable=too-few-public-methods
# pylint: disable=import-error,wrong-import-position

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cortex import RETIREMENT_MESSAGE, main


class TestCortexRetirement:
    """The old Cortex entrypoint should fail with a clear migration message."""

    def test_main_exits_with_retirement_message(self, monkeypatch, capsys):
        """The compatibility entrypoint should point callers at the v2 CLI."""
        monkeypatch.setattr(sys, "argv", ["cortex.py", "--ready", "--json"])

        with pytest.raises(SystemExit) as excinfo:
            main()

        captured = capsys.readouterr()
        assert excinfo.value.code == 2
        assert RETIREMENT_MESSAGE in captured.err
        assert "hive task ready" in captured.err
