"""横向概念 004｜同步资源清理、异常安全与清理冲突。

共同问题：正常退出是否清理；异常退出是否清理；多个资源是否逆序清理；
清理由什么机制触发；清理失败与原始异常如何交互。
"""

# polyglot-concept: resource_cleanup
# polyglot-related: languages/python/language/test_010_context_manager_protocols.py

import pytest


class RecordingResource:
    """只实现同步 ``with`` 协议，并记录取得与释放时点。"""

    def __init__(self, name, events, *, suppress=False, cleanup_error=None):
        self.name = name
        self.events = events
        self.suppress = suppress
        self.cleanup_error = cleanup_error
        self.exit_arguments = None

    def __enter__(self):
        self.events.append(f"acquire:{self.name}")
        return self

    def __exit__(self, exception_type, exception, traceback):
        self.events.append(f"release:{self.name}")
        self.exit_arguments = (exception_type, exception, traceback)
        if self.cleanup_error is not None:
            raise self.cleanup_error
        return self.suppress


def test_with_protocol_cleans_on_normal_exit():
    events = []
    resource = RecordingResource("normal", events)

    with resource as acquired:
        assert acquired is resource
        events.append("body")

    assert events == ["acquire:normal", "body", "release:normal"]
    assert resource.exit_arguments == (None, None, None)


def test_with_protocol_cleans_during_exception_exit():
    events = []
    resource = RecordingResource("exception", events)
    original = ValueError("body failed")

    with pytest.raises(ValueError) as caught:
        with resource:
            events.append("body")
            raise original

    assert caught.value is original
    assert events == ["acquire:exception", "body", "release:exception"]
    assert resource.exit_arguments[1] is original


def test_multiple_context_managers_clean_in_lifo_order():
    events = []

    with RecordingResource("first", events), RecordingResource("second", events):
        events.append("body")

    assert events == [
        "acquire:first",
        "acquire:second",
        "body",
        "release:second",
        "release:first",
    ]


def test_exit_true_can_suppress_the_body_exception():
    events = []

    with RecordingResource("suppressor", events, suppress=True):
        events.append("body")
        raise LookupError("handled")

    events.append("continued")
    assert events == ["acquire:suppressor", "body", "release:suppressor", "continued"]


def test_cleanup_error_replaces_body_error_and_preserves_context():
    events = []
    body_error = ValueError("body failed")
    cleanup_error = RuntimeError("cleanup failed")

    with pytest.raises(RuntimeError) as caught:
        with RecordingResource("failing", events, cleanup_error=cleanup_error):
            raise body_error

    assert caught.value is cleanup_error
    assert caught.value.__context__ is body_error
    assert events == ["acquire:failing", "release:failing"]
