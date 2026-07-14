"""185｜``logging`` logger 层级、有效级别与 record 传播。

logger 名称按点号形成层级；非 root logger 的 ``NOTSET`` 会继承首个祖先有效级别。
record 一旦由源 logger 接受，传播阶段会直接交给祖先的 handler，不再检查祖先 logger
自身的 level/filter；handler 的 level/filter 仍然生效。这一区别常导致误判和重复日志。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.logging.getLogger python.logging.logger-singleton-by-name
# polyglot-covers: python.logging.logger-name-hierarchy python.logging.Logger.parent
# polyglot-covers: python.logging.Logger.setLevel python.logging.NOTSET-inheritance
# polyglot-covers: python.logging.Logger.getEffectiveLevel
# polyglot-covers: python.logging.Logger.isEnabledFor python.logging.Logger.disabled
# polyglot-covers: python.logging.Logger.propagate
# polyglot-covers: python.logging.propagation-skips-ancestor-logger-gates
# polyglot-covers: python.logging.handler-level-during-propagation
# polyglot-covers: python.logging.duplicate-handler-emission python.logging.disable

import logging


class CollectingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class RejectEverything(logging.Filter):
    def filter(self, record):
        return False


def test_get_logger_is_identity_based_and_late_parent_creation_rewires_children():
    """先创建 child 也没关系；创建中间祖先后 Manager 会修正 parent 链。"""

    child = logging.getLogger("polyglot.case185.late.child")
    same_child = logging.getLogger("polyglot.case185.late.child")
    parent = logging.getLogger("polyglot.case185.late")

    assert child is same_child
    assert child.name == "polyglot.case185.late.child"
    assert child.parent is parent


def test_notset_delegates_to_the_first_ancestor_with_a_real_level():
    """有效级别是继承计算结果；child.level 本身仍保持 NOTSET。"""

    parent = logging.getLogger("polyglot.case185.level")
    child = logging.getLogger("polyglot.case185.level.child")
    parent.setLevel(logging.WARNING)
    child.setLevel(logging.NOTSET)
    child.disabled = False

    assert child.level == logging.NOTSET
    assert child.getEffectiveLevel() == logging.WARNING
    assert child.isEnabledFor(logging.INFO) is False
    assert child.isEnabledFor(logging.WARNING) is True

    child.disabled = True
    try:
        assert child.isEnabledFor(logging.CRITICAL) is False
    finally:
        child.disabled = False


def test_propagation_skips_ancestor_logger_gates_but_checks_handler_level():
    """祖先 logger 的 CRITICAL/filter 不挡 record；其 handler 的 level 会挡。"""

    parent = logging.getLogger("polyglot.case185.propagation")
    child = logging.getLogger("polyglot.case185.propagation.child")
    handler = CollectingHandler()
    rejecting_filter = RejectEverything()

    parent.handlers.clear()
    child.handlers.clear()
    parent.setLevel(logging.CRITICAL)
    parent.addFilter(rejecting_filter)
    parent.propagate = False
    child.setLevel(logging.DEBUG)
    child.propagate = True
    handler.setLevel(logging.INFO)
    parent.addHandler(handler)
    try:
        child.warning("accepted by ancestor handler")
        assert [record.getMessage() for record in handler.records] == [
            "accepted by ancestor handler"
        ]

        handler.setLevel(logging.ERROR)
        child.warning("blocked by handler")
        assert len(handler.records) == 1
    finally:
        parent.removeHandler(handler)
        parent.removeFilter(rejecting_filter)
        handler.close()


def test_attaching_the_same_handler_twice_in_the_chain_duplicates_a_record():
    """传播链不对 handler 去重；通常只把 handler 挂在合适的最高祖先。"""

    parent = logging.getLogger("polyglot.case185.duplicate")
    child = logging.getLogger("polyglot.case185.duplicate.child")
    handler = CollectingHandler()
    parent.handlers.clear()
    child.handlers.clear()
    parent.setLevel(logging.DEBUG)
    child.setLevel(logging.DEBUG)
    parent.propagate = False
    child.propagate = True
    parent.addHandler(handler)
    child.addHandler(handler)
    try:
        child.error("duplicated")
        assert len(handler.records) == 2
        assert handler.records[0] is handler.records[1]

        child.propagate = False
        child.error("local only")
        assert [record.getMessage() for record in handler.records] == [
            "duplicated",
            "duplicated",
            "local only",
        ]
    finally:
        child.removeHandler(handler)
        parent.removeHandler(handler)
        handler.close()


def test_module_disable_is_a_process_wide_gate_above_logger_levels():
    """disable(level) 屏蔽小于等于该值的事件；最后必须恢复 Manager 全局阈值。"""

    logger = logging.getLogger("polyglot.case185.global-disable")
    logger.setLevel(logging.DEBUG)
    logger.disabled = False
    previous = logging.root.manager.disable
    try:
        logging.disable(logging.ERROR)
        assert logger.isEnabledFor(logging.ERROR) is False
        assert logger.isEnabledFor(logging.CRITICAL) is True
    finally:
        logging.disable(previous)
