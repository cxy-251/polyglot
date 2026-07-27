"""重新抛出、诊断信息与完成方式竞争。

共同问题：重新抛出是否保留原对象和诊断起点；清理块产生 return 或 throw 时，
原有完成方式是否继续传播。
"""

# polyglot-family: errors_and_resources
# polyglot-concept: exception_propagation_and_matching
# polyglot-related: languages/python/language/test_009_exception_handling_and_chaining.py

import traceback

import pytest


def test_bare_raise_preserves_original_object_and_traceback_origin():
    original = RuntimeError("failed")

    def origin():
        raise original

    def propagate():
        try:
            origin()
        except RuntimeError:
            raise

    with pytest.raises(RuntimeError) as caught:
        propagate()

    frames = traceback.extract_tb(caught.value.__traceback__)
    assert caught.value is original
    assert frames[-1].name == "origin"


def test_finally_return_replaces_a_pending_exception():
    def replace():
        try:
            raise RuntimeError("hidden")
        finally:
            return "replacement"

    assert replace() == "replacement"


def test_finally_exception_replaces_a_pending_return():
    def replace():
        try:
            return "hidden"
        finally:
            raise LookupError("replacement")

    with pytest.raises(LookupError, match="replacement"):
        replace()
