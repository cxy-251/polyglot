"""146｜unittest.mock：调用记录、spec、patch、魔法方法与异步协议。

mock 的价值不只是“返回假值”，而是记录交互并在正确的名字绑定位置
替换依赖。本套覆盖 Mock/MagicMock/AsyncMock 的共同模型、签名约束、
patch 生命周期以及最常见的“patch 定义处而不是使用处”陷阱。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.unittest.mock python.mock.mock-child-and-return-value
# polyglot-covers: python.mock.call-args python.mock.call-args-list
# polyglot-covers: python.mock.method-calls python.mock.mock-calls
# polyglot-covers: python.mock.call python.mock.call-list
# polyglot-covers: python.mock.assert-called python.mock.assert-any-call
# polyglot-covers: python.mock.assert-has-calls python.mock.reset-mock
# polyglot-covers: python.mock.return-value python.mock.side-effect-function
# polyglot-covers: python.mock.side-effect-iterable python.mock.side-effect-exception
# polyglot-covers: python.mock.default-sentinel python.mock.any
# polyglot-covers: python.mock.sentinel-identity-and-pickling
# polyglot-covers: python.mock.spec python.mock.spec-set
# polyglot-covers: python.mock.mock-class-masquerading
# polyglot-covers: python.mock.create-autospec-function-and-class
# polyglot-covers: python.mock.autospec-signature-enforcement
# polyglot-covers: python.mock.wraps python.mock.configure-mock
# polyglot-covers: python.mock.attach-mock python.mock.seal
# polyglot-covers: python.mock.magic-mock-default-protocols
# polyglot-covers: python.mock.magic-mock-iteration
# polyglot-covers: python.mock.context-manager-magic-methods
# polyglot-covers: python.mock.property-mock
# polyglot-covers: python.mock.patch python.mock.patch-object
# polyglot-covers: python.mock.patch-where-looked-up
# polyglot-covers: python.mock.patch-decorator-order
# polyglot-covers: python.mock.patch-dict python.mock.patch-multiple
# polyglot-covers: python.mock.mock-open python.mock.file-context-workflow
# polyglot-covers: python.mock.patcher-start-stop python.mock.stopall
# polyglot-covers: python.mock.async-mock-call-versus-await
# polyglot-covers: python.mock.async-mock-side-effect
# polyglot-covers: python.mock.async-iterator-and-context-manager
# polyglot-covers: python.mock.autospec-async-function
# polyglot-covers: python.mock.patch-auto-async-mock
# polyglot-covers: python.mock.unsafe-assert-attribute-guard

import asyncio
import copy
import pickle
import sys
import types
from unittest.mock import ANY
from unittest.mock import AsyncMock
from unittest.mock import DEFAULT
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import PropertyMock
from unittest.mock import call
from unittest.mock import create_autospec
from unittest.mock import mock_open
from unittest.mock import patch
from unittest.mock import seal
from unittest.mock import sentinel

import pytest


class ServiceAPI:
    category = "service"

    def __init__(self, endpoint, *, timeout=10):
        self.endpoint = endpoint
        self.timeout = timeout

    def fetch(self, key, *, limit=1):
        return [key] * limit

    def close(self):
        return None


class Calculator:
    def add(self, left, right):
        return left + right


async def async_fetch(key, *, fresh=False):
    return {"key": key, "fresh": fresh}


def test_mock_lazily_creates_and_caches_child_mocks():
    service = Mock(name="service")

    assert service.client is service.client
    assert service.return_value is service.return_value
    assert service.client._mock_name == "client"
    assert service.client._mock_parent is service

    returned = service("payload")
    assert returned is service.return_value
    assert service.called is True
    assert service.call_count == 1
    assert service.call_args == call("payload")

    # 构造参数 name 只影响 repr 和子 mock 的可读路径，
    # 不会创建普通字符串属性。
    assert isinstance(service.name, Mock)
    assert "service.client" in repr(service.client)


def test_call_recording_distinguishes_root_methods_and_complete_tree():
    service = Mock()
    service(1, mode="fast")
    service.worker.run("job-1", retry=True)
    service.worker.stop()

    assert service.call_args == call(1, mode="fast")
    assert service.call_args_list == [call(1, mode="fast")]
    assert service.worker.run.call_args == call("job-1", retry=True)
    assert service.method_calls == [
        call.worker.run("job-1", retry=True),
        call.worker.stop(),
    ]
    assert service.mock_calls == [
        call(1, mode="fast"),
        call.worker.run("job-1", retry=True),
        call.worker.stop(),
    ]


def test_call_list_builds_expected_chained_interactions():
    backend = Mock()
    backend.session("primary").query("SELECT 1").close()

    expected_chain = call.session("primary").query("SELECT 1").close()
    assert backend.mock_calls == expected_chain.call_list()

    # 中间调用的参数不会被复制进最后一个 call 对象；比较完整 chained
    # calls 时应使用 call_list，而不是只比较 backend.mock_calls[-1]。
    assert backend.mock_calls[-1] == call.session().query().close()


def test_assertion_helpers_and_reset_mock_control_interaction_history():
    callback = Mock(return_value="fallback")
    callback(1, state="new")
    callback(2, state="ready")

    callback.assert_called()
    callback.assert_called_with(2, state="ready")
    callback.assert_any_call(1, state="new")
    callback.assert_has_calls(
        [call(1, state="new"), call(2, state="ready")],
        any_order=False,
    )
    assert callback.call_count == 2

    callback.side_effect = ValueError("temporary")
    callback.reset_mock(return_value=True, side_effect=True)
    assert callback.called is False
    assert callback.call_args_list == []
    assert isinstance(callback.return_value, Mock)
    assert callback.side_effect is None


def test_side_effect_function_can_delegate_to_return_value_with_default():
    events = []

    def choose(value):
        events.append(value)
        if value < 0:
            raise ValueError("negative")
        if value == 0:
            return DEFAULT
        return value * 10

    operation = Mock(return_value="zero", side_effect=choose)

    assert operation(2) == 20
    assert operation(0) == "zero"
    with pytest.raises(ValueError, match="negative"):
        operation(-1)

    assert events == [2, 0, -1]
    # 即使 side_effect 抛异常，本次调用也已经记录。
    assert operation.call_args_list == [call(2), call(0), call(-1)]


def test_iterable_and_exception_side_effects_model_sequential_outcomes():
    sequence = Mock(side_effect=["first", RuntimeError("broken"), "third"])

    assert sequence() == "first"
    with pytest.raises(RuntimeError, match="broken"):
        sequence()
    assert sequence() == "third"
    with pytest.raises(StopIteration):
        sequence()

    always_fails = Mock(side_effect=LookupError)
    with pytest.raises(LookupError):
        always_fails("record")


def test_any_default_and_sentinel_support_readable_expectations():
    sender = Mock()
    sender.send({"id": 1}, timestamp=123456)

    sender.send.assert_called_once_with({"id": 1}, timestamp=ANY)
    assert DEFAULT is sentinel.DEFAULT
    assert sentinel.missing is sentinel.missing
    assert sentinel.missing is copy.copy(sentinel.missing)
    assert sentinel.missing is copy.deepcopy(sentinel.missing)
    assert sentinel.missing is pickle.loads(pickle.dumps(sentinel.missing))
    assert repr(sentinel.missing) == "sentinel.missing"


def test_spec_limits_lookup_while_spec_set_also_limits_assignment():
    loose = Mock(spec=ServiceAPI)
    strict = Mock(spec_set=ServiceAPI)

    loose.fetch("key", limit=2)
    loose.dynamic_state = "allowed"
    assert loose.dynamic_state == "allowed"
    with pytest.raises(AttributeError):
        loose.unknown_method()

    strict.close.return_value = None
    with pytest.raises(AttributeError):
        strict.dynamic_state = "blocked"

    # spec 让 mock 的 __class__ 报告目标类，因此部分 isinstance 分支可以通过；
    # 对象本身仍然是 Mock，不应据此把它交给依赖真实实现细节的代码。
    assert isinstance(loose, ServiceAPI)
    assert type(loose) is Mock


def test_spec_does_not_enforce_signatures_but_autospec_does():
    spec_only = Mock(spec=ServiceAPI)
    spec_only.fetch("key", "limit may incorrectly be positional")

    instance = create_autospec(ServiceAPI, instance=True)
    instance.fetch("key", limit=2)
    instance.fetch.assert_called_once_with("key", limit=2)

    with pytest.raises(TypeError):
        instance.fetch()
    with pytest.raises(TypeError):
        instance.fetch("key", 2)
    with pytest.raises(TypeError):
        instance.fetch("key", unknown=True)


def test_create_autospec_class_models_constructor_and_instance_methods():
    ServiceFactory = create_autospec(ServiceAPI)
    fake_instance = ServiceFactory("https://example.invalid", timeout=3)

    ServiceFactory.assert_called_once_with("https://example.invalid", timeout=3)
    assert isinstance(fake_instance, ServiceAPI)
    fake_instance.fetch("item", limit=4)
    fake_instance.fetch.assert_called_once_with("item", limit=4)

    with pytest.raises(TypeError):
        ServiceFactory()
    with pytest.raises(TypeError):
        ServiceFactory("endpoint", 3)


def test_wraps_creates_a_spy_that_delegates_and_records():
    real = Calculator()
    spy = Mock(wraps=real)

    assert spy.add(2, 5) == 7
    spy.add.assert_called_once_with(2, 5)

    spy.add.return_value = 100
    assert spy.add(1, 1) == 100
    # 显式 return_value 优先于 wraps；配置后它不再调用真实 add。
    assert spy.add.call_args_list == [call(2, 5), call(1, 1)]


def test_configure_attach_and_seal_build_a_deliberate_mock_tree():
    client = Mock()
    client.configure_mock(
        **{
            "fetch.return_value": {"status": "ok"},
            "close.side_effect": None,
        }
    )
    assert client.fetch("key") == {"status": "ok"}

    parent = Mock()
    database = Mock()
    parent.attach_mock(database, "database")
    database.commit(transaction="tx-1")
    assert parent.mock_calls == [call.database.commit(transaction="tx-1")]

    # seal 前先触发需要的 children；seal 后，拼错路径会立即失败，而不是静默
    # 生成一个新 child 并让错误断言看似成立。
    client.fetch
    client.close
    seal(client)
    with pytest.raises(AttributeError):
        client.ftech("typo")


def test_magicmock_has_protocol_defaults_and_configurable_magic_methods():
    value = MagicMock()

    assert len(value) == 0
    assert bool(value) is True
    assert int(value) == 1
    assert list(value) == []

    value.__len__.return_value = 3
    value.__bool__.return_value = False
    value.__getitem__.side_effect = {"name": "Ada"}.__getitem__
    assert len(value) == 3
    assert bool(value) is False
    assert value["name"] == "Ada"
    value.__getitem__.assert_called_once_with("name")


def test_magicmock_iteration_can_be_reusable_or_one_shot():
    reusable = MagicMock()
    reusable.__iter__.return_value = [1, 2]
    assert list(reusable) == [1, 2]
    assert list(reusable) == [1, 2]

    one_shot = MagicMock()
    one_shot.__iter__.return_value = iter([1, 2])
    assert list(one_shot) == [1, 2]
    assert list(one_shot) == []


def test_magicmock_context_manager_records_enter_and_exit():
    manager = MagicMock()
    resource = object()
    manager.__enter__.return_value = resource

    with manager as entered:
        assert entered is resource

    manager.__enter__.assert_called_once_with()
    manager.__exit__.assert_called_once_with(None, None, None)
    assert manager.mock_calls == [call.__enter__(), call.__exit__(None, None, None)]


def test_property_mock_must_be_installed_on_the_owner_type():
    service = ServiceAPI("local")

    with patch.object(ServiceAPI, "category", new_callable=PropertyMock) as category:
        category.return_value = "patched-category"
        assert service.category == "patched-category"
        category.assert_called_once_with()

    assert service.category == "service"

    mock_instance = MagicMock()
    state = PropertyMock(return_value="ready")
    type(mock_instance).state = state
    try:
        assert mock_instance.state == "ready"
        state.assert_called_once_with()
    finally:
        del type(mock_instance).state


def test_patch_must_target_the_name_looked_up_by_the_consumer(monkeypatch):
    source = types.ModuleType("polyglot_mock_source")
    consumer = types.ModuleType("polyglot_mock_consumer")
    source.get_value = lambda: "original"
    monkeypatch.setitem(sys.modules, source.__name__, source)
    exec(
        "from polyglot_mock_source import get_value\n"
        "def read():\n"
        "    return get_value()\n",
        consumer.__dict__,
    )

    with patch.object(source, "get_value", return_value="wrong target"):
        assert consumer.read() == "original"

    with patch.object(consumer, "get_value", return_value="patched") as replacement:
        assert consumer.read() == "patched"
        replacement.assert_called_once_with()


def test_patch_decorators_inject_mocks_from_inside_out():
    target = types.SimpleNamespace(first=lambda: 1, second=lambda: 2)

    @patch.object(target, "first")
    @patch.object(target, "second")
    def exercise(mock_second, mock_first):
        assert target.first is mock_first
        assert target.second is mock_second
        return mock_first, mock_second

    first, second = exercise()
    assert isinstance(first, MagicMock)
    assert isinstance(second, MagicMock)


def test_patch_dict_and_patch_multiple_restore_original_state():
    configuration = {"mode": "prod", "retries": 3}
    with patch.dict(configuration, {"mode": "test", "extra": True}, clear=False):
        assert configuration == {"mode": "test", "retries": 3, "extra": True}
    assert configuration == {"mode": "prod", "retries": 3}

    with patch.dict(configuration, {"only": 1}, clear=True):
        assert configuration == {"only": 1}
    assert configuration == {"mode": "prod", "retries": 3}

    target = types.SimpleNamespace(fetch=lambda: None, close=lambda: None)
    with patch.multiple(target, fetch=DEFAULT, close=DEFAULT) as replacements:
        assert set(replacements) == {"fetch", "close"}
        target.fetch("key")
        replacements["fetch"].assert_called_once_with("key")

    assert callable(target.fetch)
    assert callable(target.close)


def test_mock_open_models_context_manager_reads_and_records_open_arguments():
    opener = mock_open(read_data="first line\nremaining")

    with patch("builtins.open", opener):
        with open("settings.txt", encoding="utf-8") as stream:
            first = stream.readline()
            remaining = stream.read()

    assert first == "first line\n"
    assert remaining == "remaining"
    opener.assert_called_once_with("settings.txt", encoding="utf-8")
    handle = opener()
    handle.__enter__.assert_called_once_with()
    handle.readline.assert_called_once_with()
    handle.read.assert_called_once_with()
    handle.__exit__.assert_called_once_with(None, None, None)

    # mock_open 适合纯交互测试，不实现完整文件系统语义；
    # seek、并发句柄或复杂编解码流程应使用 tmp_path 中的真实临时文件。


def test_started_patchers_require_explicit_stop_or_registered_cleanup():
    target = types.SimpleNamespace(value="original", status="idle")
    value_patcher = patch.object(target, "value", "patched")
    status_patcher = patch.object(target, "status", "busy")

    assert value_patcher.start() == "patched"
    assert status_patcher.start() == "busy"
    assert (target.value, target.status) == ("patched", "busy")

    patch.stopall()
    assert (target.value, target.status) == ("original", "idle")

    # TestCase 中通常写 self.addCleanup(patcher.stop)，这样 setUp 中途失败也能恢复。


def test_default_mock_rejects_likely_misspelled_assertion_names():
    safe = Mock()
    with pytest.raises(AttributeError, match="not a valid assertion"):
        safe.assert_caleld_once()

    unsafe = Mock(unsafe=True)
    assert isinstance(unsafe.assert_caleld_once, Mock)


def test_async_mock_separates_call_history_from_await_history():
    async def scenario():
        operation = AsyncMock(return_value="done")
        pending = operation("item", fresh=True)

        operation.assert_called_once_with("item", fresh=True)
        operation.assert_not_awaited()
        assert operation.call_count == 1
        assert operation.await_count == 0

        assert await pending == "done"
        operation.assert_awaited_once_with("item", fresh=True)
        assert operation.await_args == call("item", fresh=True)
        assert operation.await_args_list == [call("item", fresh=True)]

    asyncio.run(scenario())


def test_async_mock_side_effect_iterable_ends_with_stop_async_iteration():
    async def scenario():
        operation = AsyncMock(side_effect=[1, RuntimeError("broken"), 3])

        assert await operation() == 1
        with pytest.raises(RuntimeError, match="broken"):
            await operation()
        assert await operation() == 3
        with pytest.raises(StopAsyncIteration):
            await operation()

    asyncio.run(scenario())


def test_magicmock_supports_async_iteration_and_async_context_management():
    async def scenario():
        stream = MagicMock()
        stream.__aiter__.return_value = [1, 2, 3]
        values = [value async for value in stream]
        assert values == [1, 2, 3]
        stream.__aiter__.assert_called_once_with()

        manager = MagicMock()
        manager.__aenter__.return_value = sentinel.connection
        async with manager as connection:
            assert connection is sentinel.connection
        manager.__aenter__.assert_awaited_once_with()
        manager.__aexit__.assert_awaited_once_with(None, None, None)

    asyncio.run(scenario())


def test_autospec_and_patch_choose_async_aware_mocks(monkeypatch):
    async def scenario():
        operation = create_autospec(async_fetch)
        operation.return_value = {"key": "a", "fresh": True}
        assert await operation("a", fresh=True) == {"key": "a", "fresh": True}
        operation.assert_awaited_once_with("a", fresh=True)
        with pytest.raises(TypeError):
            await operation()

        module = types.ModuleType("polyglot_async_dependency")
        module.fetch = async_fetch
        monkeypatch.setitem(sys.modules, module.__name__, module)
        with patch("polyglot_async_dependency.fetch") as replacement:
            assert isinstance(replacement, AsyncMock)
            replacement.return_value = "patched"
            assert await module.fetch("id") == "patched"
            replacement.assert_awaited_once_with("id")

    asyncio.run(scenario())
