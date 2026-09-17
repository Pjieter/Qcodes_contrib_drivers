"""
Shared fixtures and safety guards for the Kiutra L-Type Rapid tests.

Some of these tests drive a real cryostat: they start temperature and field
ramps and then wait for them to settle. Running them by accident against a
cold system dumps the ADR and costs hours of recovery time, so they are
skipped unless hardware testing is explicitly requested.

To run the hardware tests, point them at a system and opt in::

    KIUTRA_HARDWARE_TESTS=1 KIUTRA_ADDRESS=192.168.11.20 pytest tests/Kiutra

Without ``KIUTRA_HARDWARE_TESTS`` every test that needs a live connection is
skipped, and constructing a ``KiutraClient`` raises, so a missing skip marker
cannot quietly turn into a connection attempt.
"""

import os
from pathlib import Path

import pytest

#: Environment variable that opts in to tests which talk to real hardware.
HARDWARE_ENV_VAR = "KIUTRA_HARDWARE_TESTS"

#: Environment variable holding the address of the system under test.
ADDRESS_ENV_VAR = "KIUTRA_ADDRESS"

#: Address used when the tests are opted in but no address is given.
DEFAULT_ADDRESS = "192.168.11.20"

#: Default JSON-RPC port of a kiutra system.
DEFAULT_PORT = 1006

#: Fixtures that can only be built with a live connection.
_HARDWARE_FIXTURES = frozenset({"driver"})


def hardware_tests_enabled() -> bool:
    """Whether the user opted in to tests that talk to real hardware."""
    return os.environ.get(HARDWARE_ENV_VAR, "").strip().lower() not in (
        "",
        "0",
        "false",
        "no",
    )


@pytest.fixture(scope="session", name="kiutra_address")
def _kiutra_address() -> str:
    """Address of the system under test, overridable from the environment."""
    return os.environ.get(ADDRESS_ENV_VAR, DEFAULT_ADDRESS)


@pytest.fixture(scope="session", name="kiutra_port")
def _kiutra_port() -> int:
    """Port of the system under test."""
    return int(os.environ.get("KIUTRA_PORT", DEFAULT_PORT))


def pytest_collection_modifyitems(config, items) -> None:
    """
    Skips tests needing a live connection unless hardware testing is on.

    pytest hands this hook every item collected in the session, not just the
    ones under this directory, and "driver" is a common fixture name. Items
    outside this directory are therefore filtered out explicitly; without that
    check this silently skips unrelated drivers' tests.
    """
    if hardware_tests_enabled():
        return

    here = Path(__file__).parent.resolve()
    skip_hardware = pytest.mark.skip(
        reason=(
            f"needs a live kiutra system; set {HARDWARE_ENV_VAR}=1 to run "
            f"(and {ADDRESS_ENV_VAR} to pick the address)"
        )
    )
    for item in items:
        item_path = getattr(item, "path", None)
        if item_path is None:  # pytest < 7 compatibility
            item_path = Path(str(item.fspath))
        if here not in Path(item_path).resolve().parents:
            continue
        fixtures = set(getattr(item, "fixturenames", ()))
        if fixtures & _HARDWARE_FIXTURES:
            item.add_marker(skip_hardware)


def _forbid_hardware_connections() -> None:
    """
    Makes any connection attempt fail loudly when not opted in.

    This is a backstop for the skip marker above: if a test grows a new way of
    reaching the instrument, it fails with a clear message instead of silently
    starting a ramp on a cold system.

    This runs at conftest import time, before pytest imports any test module.
    That ordering matters, because some of the test modules replace
    ``sys.modules["kiutra_api"]`` with a ``MagicMock`` while being imported; a
    guard installed later would patch that mock instead of the real client, and
    which happened first would depend on collection order.
    """
    if hardware_tests_enabled():
        return

    try:
        from kiutra_api import api_client
    except ImportError:
        # kiutra_api is not installed, so nothing can connect anyway.
        return

    def _refuse(self, *args, **kwargs):
        raise RuntimeError(
            f"Refusing to connect to a kiutra system: {HARDWARE_ENV_VAR} is not "
            f"set. Set it to 1 to allow tests to drive real hardware."
        )

    api_client.KiutraClient.__init__ = _refuse


_forbid_hardware_connections()
