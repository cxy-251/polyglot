"""102｜pickle protocol 5 out-of-band buffer 与 unpickle 安全边界。

``PickleBuffer`` 只表示大块 buffer 可被外部 transport；producer 的 callback 与 consumer 的
``buffers`` iterable 必须按相同顺序配对。unpickle 会调用 stream 指定的 global callable，
``find_class`` allowlist 可缩小攻击面但不是通用 sandbox；根本规则仍是只加载可信数据。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.pickle.protocol-five python.pickle.PickleBuffer
# polyglot-covers: python.pickle.PickleBuffer.raw python.pickle.buffer-protocol
# polyglot-covers: python.pickle.PickleBuffer.release python.pickle.noncontiguous-buffer
# polyglot-covers: python.pickle.buffer-callback python.pickle.out-of-band
# polyglot-covers: python.pickle.buffer-callback-false python.pickle.buffer-callback-true
# polyglot-covers: python.pickle.loads-buffers python.pickle.missing-buffers
# polyglot-covers: python.pickle.buffer-order python.pickle.buffer-iterator-consumption
# polyglot-covers: python.pickle.protocol-four-buffer-fallback
# polyglot-covers: python.pickle.Unpickler.find-class python.pickle.function-resolution
# polyglot-covers: python.pickle.restricted-unpickler python.pickle.global-allowlist
# polyglot-covers: python.pickle.no-globals python.pickle.builtin-opcodes
# polyglot-covers: python.pickle.unpickle-calls-code python.pickle.arbitrary-code-risk
# polyglot-covers: python.pickle.restricted-not-sandbox python.pickle.trusted-data-only

import builtins
import io
import pickle

import pytest


class ZeroCopyByteArray(bytearray):
    """protocol 5 提供 PickleBuffer，旧 protocol 退回普通 bytearray copy。"""

    def __reduce_ex__(self, protocol):
        if protocol >= 5:
            return type(self)._reconstruct, (pickle.PickleBuffer(self),), None
        return type(self)._reconstruct, (bytearray(self),)

    @classmethod
    def _reconstruct(cls, obj):
        with memoryview(obj) as view:
            underlying = view.obj
        if type(underlying) is cls:
            return underlying
        return cls(underlying)


SAFE_BUILTINS = {"complex", "frozenset", "range", "set", "slice"}


class RestrictedUnpickler(pickle.Unpickler):
    """示例 allowlist 只允许少量 inert builtins globals。"""

    def find_class(self, module, name):
        if module == "builtins" and name in SAFE_BUILTINS:
            return getattr(builtins, name)
        raise pickle.UnpicklingError(f"forbidden global: {module}.{name}")


class NoGlobalsUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        raise pickle.UnpicklingError(f"globals disabled: {module}.{name}")


class TrackingUnpickler(pickle.Unpickler):
    def __init__(self, file):
        super().__init__(file)
        self.requested_globals = []

    def find_class(self, module, name):
        self.requested_globals.append((module, name))
        return super().find_class(module, name)


LOAD_EVENTS = []


def record_load_event(value):
    """只产生 process-local list event，用安全副作用证明 reduce callable 会在 load 阶段运行。"""

    LOAD_EVENTS.append(value)
    return {"loaded": value}


class CallsCodeWhenLoaded:
    def __init__(self, value):
        self.value = value

    def __reduce__(self):
        return record_load_event, (self.value,)


def restricted_loads(payload):
    return RestrictedUnpickler(io.BytesIO(payload)).load()


def test_picklebuffer_raw_exposes_a_one_dimensional_unsigned_byte_view():
    """raw() 统一返回 C-contiguous format B memoryview，适合直接交给 transport。"""

    source = bytearray(b"abc")
    buffer = pickle.PickleBuffer(source)
    view = buffer.raw()
    try:
        assert isinstance(view, memoryview)
        assert view.ndim == 1
        assert view.format == "B"
        assert view.c_contiguous is True
        assert view.tobytes() == b"abc"

        view[0] = ord("A")
        assert source == bytearray(b"Abc")
    finally:
        view.release()
        buffer.release()


def test_picklebuffer_raw_rejects_a_noncontiguous_view():
    """strided view 既非 C- 也非 Fortran-contiguous，不能降成 raw byte span。"""

    source = memoryview(bytearray(b"abcdef"))[::2]
    buffer = pickle.PickleBuffer(source)
    try:
        with pytest.raises(BufferError):
            buffer.raw()
    finally:
        buffer.release()
        source.release()


def test_picklebuffer_release_forbids_new_raw_views():
    """transport 完成后显式 release；已释放 wrapper 不能再次暴露 underlying buffer。"""

    buffer = pickle.PickleBuffer(bytearray(b"data"))
    buffer.release()

    with pytest.raises(ValueError):
        buffer.raw()


def test_picklebuffer_itself_requires_protocol_five_or_newer():
    """PickleBuffer opcode 不存在于 protocol 4；provider 必须像示例 class 一样提供旧版 fallback。"""

    buffer = pickle.PickleBuffer(bytearray(b"data"))
    try:
        with pytest.raises(pickle.PicklingError):
            pickle.dumps(buffer, protocol=4)
    finally:
        buffer.release()


def test_protocol_four_provider_fallback_round_trips_as_an_independent_copy():
    """旧 reader 得到相同 value，但没有 out-of-band identity/zero-copy 优化。"""

    original = ZeroCopyByteArray(b"payload")

    restored = pickle.loads(pickle.dumps(original, protocol=4))

    assert restored == original
    assert isinstance(restored, ZeroCopyByteArray)
    assert restored is not original


def test_protocol_five_without_callback_keeps_buffer_in_band():
    """仅选择 protocol 5 不会自动拆分 transport；buffer_callback=None 仍把数据写入主 stream。"""

    original = ZeroCopyByteArray(b"payload")

    payload = pickle.dumps(original, protocol=5)
    restored = pickle.loads(payload)

    assert restored == original
    assert restored is not original


def test_false_buffer_callback_moves_data_out_of_band_and_consumer_supplies_it():
    """list.append 返回 None，因此 captured buffer 不进入 pickle bytes，只留下 next-buffer marker。"""

    original = ZeroCopyByteArray(b"payload")
    buffers = []

    payload = pickle.dumps(original, protocol=5, buffer_callback=buffers.append)

    assert len(buffers) == 1
    assert isinstance(buffers[0], pickle.PickleBuffer)
    with pytest.raises(pickle.UnpicklingError):
        pickle.loads(payload)

    restored = pickle.loads(payload, buffers=buffers)
    assert restored is original


def test_truthy_buffer_callback_keeps_data_in_band():
    """callback 返回 truthy 表示仅观察而不外移；consumer 无需 buffers 也能独立 load。"""

    observed = []

    def keep_in_band(buffer):
        observed.append(buffer.raw().tobytes())
        return True

    original = ZeroCopyByteArray(b"payload")
    payload = pickle.dumps(original, protocol=5, buffer_callback=keep_in_band)
    restored = pickle.loads(payload)

    assert observed == [b"payload"]
    assert restored == original
    assert restored is not original


def test_buffer_callback_requires_protocol_five_explicitly():
    """protocol=None 在 3.10 会选默认 4，也因此不能与 callback 组合。"""

    original = ZeroCopyByteArray(b"payload")

    with pytest.raises(ValueError):
        pickle.dumps(original, buffer_callback=lambda buffer: None)
    with pytest.raises(ValueError):
        pickle.dumps(original, protocol=4, buffer_callback=lambda buffer: None)


def test_out_of_band_buffers_are_positional_and_must_keep_provider_order():
    """stream marker 没有自描述 key；reversed iterable 会合法地把 buffer 接到错误对象位置。"""

    first = ZeroCopyByteArray(b"first")
    second = ZeroCopyByteArray(b"second")
    buffers = []
    payload = pickle.dumps(
        [first, second], protocol=5, buffer_callback=buffers.append
    )

    restored_in_order = pickle.loads(payload, buffers=buffers)
    restored_reversed = pickle.loads(payload, buffers=reversed(buffers))

    assert restored_in_order[0] is first
    assert restored_in_order[1] is second
    assert restored_reversed[0] is second
    assert restored_reversed[1] is first


def test_too_few_out_of_band_buffers_raise_unpickling_error():
    """buffers iterable 是按需消费；少一个就无法完成后续 reconstruct。"""

    buffers = []
    payload = pickle.dumps(
        [ZeroCopyByteArray(b"first"), ZeroCopyByteArray(b"second")],
        protocol=5,
        buffer_callback=buffers.append,
    )

    with pytest.raises(pickle.UnpicklingError):
        pickle.loads(payload, buffers=buffers[:1])


def test_find_class_is_used_for_functions_despite_its_name():
    """GLOBAL resolution 不只找 class；reduce callable/function 同样经过 find_class。"""

    payload = pickle.dumps(record_load_event)
    unpickler = TrackingUnpickler(io.BytesIO(payload))

    assert unpickler.load() is record_load_event
    assert unpickler.requested_globals == [(record_load_event.__module__, "record_load_event")]


def test_restricted_unpickler_allows_selected_builtins_and_ordinary_data():
    """list/dict/int 等常有专用 opcode，不经过 find_class；range/complex 等 global 必须 allowlist。"""

    original = {
        "plain": [1, 2, 3],
        "range": range(1, 6, 2),
        "complex": 2 + 3j,
        "slice": slice(1, 5, 2),
    }

    restored = restricted_loads(pickle.dumps(original))

    assert restored == original


def test_restricted_unpickler_rejects_non_allowlisted_functions():
    """拒绝在 callable 被调用前发生；此例不把 payload 交给 unrestricted loads。"""

    payload = pickle.dumps(len)

    with pytest.raises(pickle.UnpicklingError, match="builtins.len"):
        restricted_loads(payload)


def test_no_globals_policy_can_still_load_opcode_only_builtin_containers():
    """完全禁止 GLOBAL/STACK_GLOBAL 不等于禁止所有值；plain container opcodes 可正常恢复。"""

    payload = pickle.dumps({"items": [1, 2, None, True]})

    assert NoGlobalsUnpickler(io.BytesIO(payload)).load() == {
        "items": [1, 2, None, True]
    }


def test_unrestricted_load_invokes_reduce_callable_during_deserialization():
    """用无害的 in-memory event 证明风险机制：load 不只是解析 bytes，它会执行 global callable。"""

    LOAD_EVENTS.clear()
    try:
        payload = pickle.dumps(CallsCodeWhenLoaded("event"))
        assert LOAD_EVENTS == []

        restored = pickle.loads(payload)

        assert restored == {"loaded": "event"}
        assert LOAD_EVENTS == ["event"]
    finally:
        LOAD_EVENTS.clear()


def test_restricted_load_blocks_reduce_callable_before_its_side_effect():
    """allowlist 可拦截此类 global，但允许的任何 callable 仍需安全审计；它不是 general sandbox。"""

    LOAD_EVENTS.clear()
    try:
        payload = pickle.dumps(CallsCodeWhenLoaded("blocked"))

        with pytest.raises(pickle.UnpicklingError, match="record_load_event"):
            restricted_loads(payload)

        assert LOAD_EVENTS == []
    finally:
        LOAD_EVENTS.clear()
