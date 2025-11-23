import os
import time
from datetime import datetime
from pathlib import Path

import pytest


class _ProgressReporter:
    """Pytest plugin that prints per-test start and end markers with timing."""

    def __init__(self):
        self._terminal = None
        self._starts: dict[str, float] = {}

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionstart(self, session: pytest.Session) -> None:
        if self._terminal is None:
            self._terminal = session.config.pluginmanager.get_plugin("terminalreporter")

    @pytest.hookimpl
    def pytest_runtest_logstart(self, nodeid: str, location) -> None:
        if self._terminal is None:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._starts[nodeid] = time.monotonic()
        self._terminal.write_line(f"[{timestamp}] RUN    {nodeid}")

    @pytest.hookimpl
    def pytest_runtest_logreport(self, report: pytest.TestReport):
        if self._terminal is None or report.when != "call":
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        duration: float | None = None
        if report.nodeid in self._starts:
            duration = time.monotonic() - self._starts.pop(report.nodeid)
        duration_text = f" ({duration:.2f}s)" if duration is not None else ""
        outcome = report.outcome.upper()
        self._terminal.write_line(f"[{timestamp}] {outcome:6} {report.nodeid}{duration_text}")


def _progress_enabled(config: pytest.Config) -> bool:
    if config.getoption("progress", default=False):
        return True
    env_value = os.environ.get("PYTEST_PROGRESS", "")
    return env_value.lower() in {"1", "true", "yes", "on"}


def _manual_enabled(config: pytest.Config) -> bool:
    if config.getoption("manual", default=False):
        return True
    env_value = os.environ.get("PYTEST_INCLUDE_MANUAL", "")
    return env_value.lower() in {"1", "true", "yes", "on"}


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("neumann")
    group.addoption(
        "--progress",
        action="store_true",
        help="Print test start/finish timestamps and durations to aid debugging long runs.",
    )
    group.addoption(
        "--manual",
        action="store_true",
        help="Include tests under tests/manual/. They are skipped by default.",
    )


def pytest_configure(config: pytest.Config) -> None:
    if _progress_enabled(config):
        reporter = _ProgressReporter()
        config.pluginmanager.register(reporter, "neumann-progress-reporter")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if _manual_enabled(config):
        return

    manual_root = Path(config.rootpath, "tests", "manual").resolve()
    skip_manual = pytest.mark.skip(
        reason="Manual test suite is excluded by default; re-run with --manual or PYTEST_INCLUDE_MANUAL=1."
    )

    for item in items:
        try:
            item_path = Path(str(item.fspath)).resolve()
        except OSError:
            continue
        if manual_root in item_path.parents:
            item.add_marker(skip_manual)
