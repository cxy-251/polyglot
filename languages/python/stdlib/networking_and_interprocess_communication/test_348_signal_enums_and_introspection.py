"""348｜信号、处理动作与 mask 常量的枚举接口。

Python 3.5 起，常见 SIG*、SIG_DFL/SIG_IGN 和 SIG_BLOCK 等常量分别属于 IntEnum；它们仍可作为
整数传给系统 API，同时具备可读名称。可用信号是平台能力，valid_signals 比假定 ``1..NSIG``
更可靠，实时信号或系统保留号尤其不能靠硬编码清单判断。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.signal.Signals
# polyglot-covers: python.signal.Handlers
# polyglot-covers: python.signal.Sigmasks
# polyglot-covers: python.signal.SIG_DFL
# polyglot-covers: python.signal.SIG_IGN
# polyglot-covers: python.signal.SIG_BLOCK
# polyglot-covers: python.signal.SIG_UNBLOCK
# polyglot-covers: python.signal.SIG_SETMASK
# polyglot-covers: python.signal.NSIG
# polyglot-covers: python.signal.valid_signals
# polyglot-covers: python.signal.strsignal
# polyglot-covers: python.signal.platform-dependent-signal-set

import signal


def test_signal_related_constants_are_integer_compatible_enums():
    assert isinstance(signal.SIGINT, signal.Signals)
    assert signal.Signals(int(signal.SIGINT)) is signal.Signals.SIGINT
    assert isinstance(signal.SIG_DFL, signal.Handlers)
    assert isinstance(signal.SIG_IGN, signal.Handlers)
    assert {
        signal.SIG_BLOCK,
        signal.SIG_UNBLOCK,
        signal.SIG_SETMASK,
    } == set(signal.Sigmasks)

    # IntEnum 与 int 相等且可直接索引，但日志与 repr 会保留语义名称。
    handlers = {int(signal.SIGINT): "interrupt"}
    assert handlers[signal.SIGINT] == "interrupt"
    assert signal.SIGINT.name == "SIGINT"


def test_valid_signals_and_system_descriptions_are_discovered_at_runtime():
    available = signal.valid_signals()
    assert signal.SIGINT in available
    assert signal.SIGTERM in available
    assert all(isinstance(signum, int) for signum in available)
    assert all(0 < int(signum) < signal.NSIG for signum in available)

    description = signal.strsignal(signal.SIGINT)
    # 描述由操作系统提供且可能本地化，所以只断言类型与非空，不比较英文文本。
    assert isinstance(description, str)
    assert description


def test_optional_signal_names_must_be_feature_detected():
    # Windows 有 SIGBREAK；Unix 常有 SIGUSR1。跨平台库应探测名称而非无条件导入。
    optional = {
        name: getattr(signal, name)
        for name in ("SIGBREAK", "SIGUSR1", "SIGWINCH")
        if hasattr(signal, name)
    }
    assert optional
    assert set(optional.values()) <= signal.valid_signals()
