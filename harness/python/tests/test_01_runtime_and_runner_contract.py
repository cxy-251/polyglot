# polyglot-harness: python.runtime-pytest-and-isolated-runner-contract

from importlib.metadata import version
from pathlib import Path
import os
import sys


def test_locked_runtime_and_pytest_versions() -> None:
    assert sys.version_info[:3] == (3, 10, 12)
    assert version("pytest") == "9.1.1"


def test_runner_isolates_user_site_bytecode_and_persistent_cache(pytestconfig) -> None:
    assert os.environ["PYTHONNOUSERSITE"] == "1"
    assert sys.dont_write_bytecode is False
    assert Path.home().is_relative_to(Path("/tmp"))
    assert Path(sys.pycache_prefix).is_relative_to(Path("/tmp"))
    assert not pytestconfig.pluginmanager.hasplugin("cacheprovider")
