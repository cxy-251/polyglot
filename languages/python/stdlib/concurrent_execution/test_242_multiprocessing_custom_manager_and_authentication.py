"""242｜``BaseManager.register`` custom referent、exposed methods 与 client authentication。

BaseManager 可在本地 IPC server 暴露自定义 object。``register`` 决定 typeid、factory 和
可调用的 public methods；未列入 exposed 的 API 不会穿透 proxy。authkey 用 HMAC 验证
同一 secret 的双方身份，但不加密 payload。案例使用 address=None 的本地最快 IPC family。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.multiprocessing.managers.BaseManager
# polyglot-covers: python.multiprocessing.BaseManager.register
# polyglot-covers: python.multiprocessing.BaseManager-custom-type
# polyglot-covers: python.multiprocessing.BaseManager-exposed-methods
# polyglot-covers: python.multiprocessing.BaseManager.start
# polyglot-covers: python.multiprocessing.BaseManager.address
# polyglot-covers: python.multiprocessing.BaseManager.connect
# polyglot-covers: python.multiprocessing.BaseManager.shutdown
# polyglot-covers: python.multiprocessing.BaseProxy._callmethod
# polyglot-covers: python.multiprocessing.manager-return-by-value
# polyglot-covers: python.multiprocessing.AuthenticationError
# polyglot-covers: python.multiprocessing.manager-authkey
# polyglot-covers: python.multiprocessing.authkey-authenticates-not-encrypts

import multiprocessing
from multiprocessing.managers import BaseManager

import pytest


class _Calculator:
    def __init__(self, offset=0):
        self.offset = offset
        self._history = []

    def add(self, left, right):
        result = left + right + self.offset
        self._history.append(result)
        return result

    def history(self):
        return list(self._history)

    def secret(self):
        return "not exposed"


class _CalculatorManager(BaseManager):
    pass


class _CalculatorClient(BaseManager):
    pass


_CalculatorManager.register(
    "Calculator",
    _Calculator,
    exposed=("add", "history"),
)
_CalculatorClient.register("Calculator")


def test_custom_manager_proxy_exposes_only_registered_methods():
    """history 返回普通 list copy；改 snapshot 不会回写 referent。"""

    manager = _CalculatorManager(address=None, authkey=b"manager-secret")
    with manager as entered:
        assert entered is manager
        calculator = manager.Calculator(10)

        assert calculator.add(2, 3) == 15
        assert calculator._callmethod("add", (4, 5)) == 19
        snapshot = calculator.history()
        assert snapshot == [15, 19]
        snapshot.append(999)
        assert calculator.history() == [15, 19]
        with pytest.raises(AttributeError):
            calculator.secret()

        assert manager.address is not None


def test_separate_client_connects_with_matching_key_and_rejects_wrong_key():
    """所有连接都留在 manager 选择的 Unix socket/Windows pipe，不访问外部网络。"""

    manager = _CalculatorManager(address=None, authkey=b"correct-key")
    manager.start()
    try:
        client = _CalculatorClient(
            address=manager.address,
            authkey=b"correct-key",
        )
        client.connect()
        remote = client.Calculator(1)
        assert remote.add(20, 21) == 42

        wrong = _CalculatorClient(
            address=manager.address,
            authkey=b"wrong-key",
        )
        with pytest.raises(multiprocessing.AuthenticationError):
            wrong.connect()
    finally:
        manager.shutdown()
