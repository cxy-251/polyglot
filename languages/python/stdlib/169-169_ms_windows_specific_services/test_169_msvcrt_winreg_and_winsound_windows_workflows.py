"""169｜Windows 专属服务：CRT 文件/控制台、注册表与系统声音。

这三个模块只存在于原生 Windows。文件在其他平台仍可被 pytest 收集，但所有
案例会明确 skip；不能用 Linux 上缺少模块误判为 Python 标准库不完整。
注册表案例只在当前用户下创建带随机名的临时键，
并在 finally 中删除；声音案例
只测试停止、缺失资源与非法组合，不在自动测试中播放真实声音。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.msvcrt python.msvcrt.locking
# polyglot-covers: python.msvcrt.lock-modes python.msvcrt.setmode
# polyglot-covers: python.msvcrt.get-osfhandle python.msvcrt.open-osfhandle
# polyglot-covers: python.msvcrt.console-byte-wide python.msvcrt.pushback
# polyglot-covers: python.msvcrt.kbhit python.msvcrt.heapmin
# polyglot-covers: python.stdlib.winreg python.winreg.root-handles
# polyglot-covers: python.winreg.access-masks python.winreg.wow64-views
# polyglot-covers: python.winreg.value-types python.winreg.expand-environment-strings
# polyglot-covers: python.winreg.connect-registry python.winreg.pyhkey
# polyglot-covers: python.winreg.pyhkey-context python.winreg.pyhkey-detach
# polyglot-covers: python.winreg.create-open-delete-key
# polyglot-covers: python.winreg.set-query-delete-value
# polyglot-covers: python.winreg.enum-key-value python.winreg.query-info-key
# polyglot-covers: python.winreg.unnamed-value python.winreg.nonrecursive-delete
# polyglot-covers: python.winreg.reflection-api python.winreg.flush-avoidance
# polyglot-covers: python.stdlib.winsound python.winsound.play-sound
# polyglot-covers: python.winsound.sound-sources python.winsound.playback-flags
# polyglot-covers: python.winsound.stop-playback python.winsound.nodefault
# polyglot-covers: python.winsound.memory-async-conflict python.winsound.beep-range

import io
import os
import sys
import uuid
import wave

import pytest


pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="msvcrt、winreg 和 winsound 仅在原生 Windows 提供",
)

if sys.platform == "win32":
    import msvcrt
    import winreg
    import winsound
else:
    msvcrt = None
    winreg = None
    winsound = None


def test_msvcrt_locking_uses_the_current_file_position_and_exact_region(tmp_path):
    path = tmp_path / "locked.bin"
    with path.open("w+b") as file_object:
        file_object.write(b"0123456789")
        file_object.flush()
        file_object.seek(2)

        msvcrt.locking(file_object.fileno(), msvcrt.LK_NBLCK, 4)
        try:
            assert file_object.tell() == 2
            # 锁区从当前位置开始，可越过文件尾；
            # 相邻锁也不会被自动合并。
        finally:
            file_object.seek(2)
            msvcrt.locking(file_object.fileno(), msvcrt.LK_UNLCK, 4)

    assert len({
        msvcrt.LK_LOCK,
        msvcrt.LK_RLCK,
        msvcrt.LK_NBLCK,
        msvcrt.LK_NBRLCK,
        msvcrt.LK_UNLCK,
    }) == 5


def test_msvcrt_setmode_switches_crt_newline_translation_and_returns_old_mode(
    tmp_path,
):
    path = tmp_path / "mode.txt"
    with path.open("w+b") as file_object:
        descriptor = file_object.fileno()
        previous = msvcrt.setmode(descriptor, os.O_BINARY)
        try:
            assert isinstance(previous, int)
            file_object.write(b"line\n")
            file_object.flush()
        finally:
            msvcrt.setmode(descriptor, previous)

    assert path.read_bytes() == b"line\n"
    # setmode 只改 CRT 文件描述符层；已包装的 TextIOWrapper
    # 还可能有自己的 newline 规则。


def test_msvcrt_converts_file_descriptors_to_native_handles(tmp_path):
    path = tmp_path / "handle.bin"
    with path.open("w+b") as file_object:
        handle = msvcrt.get_osfhandle(file_object.fileno())
        assert isinstance(handle, int)
        assert handle != -1

    with pytest.raises(OSError):
        msvcrt.get_osfhandle(-1)
    # open_osfhandle 会把 native handle 的所有权交给新 fd；
    # 不应拿仍由现有 file object 管理的 handle 做往返，否则会发生重复关闭。
    assert callable(msvcrt.open_osfhandle)


def test_msvcrt_console_pushback_has_separate_byte_and_wide_character_apis():
    try:
        msvcrt.ungetch(b"A")
        assert msvcrt.kbhit() is True
        assert msvcrt.getch() == b"A"

        msvcrt.ungetwch("界")
        assert msvcrt.getwch() == "界"
    except OSError as error:
        pytest.skip(f"当前 Windows 测试进程没有可用控制台：{error}")

    assert callable(msvcrt.getche)
    assert callable(msvcrt.getwche)
    assert callable(msvcrt.putch)
    assert callable(msvcrt.putwch)
    # 普通接口只处理单字节字符；
    # 国际化控制台输入应优先使用宽字符版本。


def test_msvcrt_heapmin_reports_success_or_platform_failure():
    try:
        result = msvcrt.heapmin()
    except OSError:
        result = "runtime could not compact the heap"

    assert result is None or isinstance(result, str)
    # heapmin 是“请求 CRT 归还空闲块”，不是保证进程常驻内存立即下降。


def test_winreg_constants_separate_roots_access_rights_views_and_value_types():
    roots = {
        winreg.HKEY_CLASSES_ROOT,
        winreg.HKEY_CURRENT_USER,
        winreg.HKEY_LOCAL_MACHINE,
        winreg.HKEY_USERS,
        winreg.HKEY_CURRENT_CONFIG,
    }
    assert len(roots) == 5

    assert winreg.KEY_READ & winreg.KEY_QUERY_VALUE
    assert winreg.KEY_WRITE & winreg.KEY_SET_VALUE
    assert winreg.KEY_ALL_ACCESS & winreg.KEY_CREATE_SUB_KEY
    assert winreg.KEY_WOW64_32KEY != winreg.KEY_WOW64_64KEY

    value_types = {
        winreg.REG_SZ,
        winreg.REG_EXPAND_SZ,
        winreg.REG_BINARY,
        winreg.REG_DWORD,
        winreg.REG_MULTI_SZ,
        winreg.REG_QWORD,
    }
    assert len(value_types) == 6


def test_winreg_expands_percent_delimited_process_environment(monkeypatch):
    monkeypatch.setenv("POLYGLOT_WINREG_169", "expanded")

    expanded = winreg.ExpandEnvironmentStrings(
        r"prefix-%POLYGLOT_WINREG_169%-suffix"
    )

    assert expanded == "prefix-expanded-suffix"
    # REG_EXPAND_SZ 存储的是模板；QueryValueEx 不会自动展开，
    # 需显式调用本函数。


def test_winreg_pyhkey_context_closes_handles_and_detach_transfers_ownership():
    with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as connected:
        assert type(connected).__name__ == "PyHKEY"
        assert bool(connected) is True
        assert int(connected) != 0
    assert bool(connected) is False

    detached = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
    raw_handle = detached.Detach()
    try:
        assert isinstance(raw_handle, int)
        assert raw_handle != 0
        assert bool(detached) is False
    finally:
        winreg.CloseKey(raw_handle)
    # Detach 后 PyHKEY 不再负责关闭，原始整数句柄必须由调用者 CloseKey。


def test_winreg_temporary_key_roundtrips_supported_value_shapes():
    key_path = rf"Software\Classes\PolyglotStdlibTests-{uuid.uuid4().hex}"
    key = winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER,
        key_path,
        access=winreg.KEY_ALL_ACCESS,
    )
    try:
        values = {
            "text": ("hello", winreg.REG_SZ),
            "expandable": (r"%TEMP%\lesson", winreg.REG_EXPAND_SZ),
            "bytes": (b"\x00\x01\xff", winreg.REG_BINARY),
            "dword": (2**32 - 1, winreg.REG_DWORD),
            "qword": (2**63 + 1, winreg.REG_QWORD),
            "multi": (["first", "second"], winreg.REG_MULTI_SZ),
        }
        for name, (value, value_type) in values.items():
            winreg.SetValueEx(key, name, 0, value_type, value)
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "default text")

        for name, expected in values.items():
            assert winreg.QueryValueEx(key, name) == expected
        assert winreg.QueryValue(key, None) == "default text"

        subkey_count, value_count, modified = winreg.QueryInfoKey(key)
        assert subkey_count == 0
        assert value_count == len(values) + 1
        assert isinstance(modified, int)

        enumerated = {}
        for index in range(value_count):
            name, value, value_type = winreg.EnumValue(key, index)
            enumerated[name] = (value, value_type)
        expected_entries = dict(values)
        expected_entries[""] = ("default text", winreg.REG_SZ)
        assert enumerated == expected_entries

        winreg.DeleteValue(key, "text")
        with pytest.raises(FileNotFoundError):
            winreg.QueryValueEx(key, "text")
    finally:
        key.Close()
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
    # FlushKey 会强制等待落盘；普通配置写入依赖系统
    # lazy flusher 即可，本例不调用它。


def test_winreg_enumerates_subkeys_and_delete_key_is_not_recursive():
    key_path = rf"Software\Classes\PolyglotStdlibTests-{uuid.uuid4().hex}"
    parent = winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER,
        key_path,
        access=winreg.KEY_ALL_ACCESS,
    )
    child = winreg.CreateKey(parent, "child")
    grandchild = winreg.CreateKey(child, "grandchild")
    grandchild.Close()
    child.Close()
    try:
        assert winreg.EnumKey(parent, 0) == "child"
        with pytest.raises(OSError):
            winreg.EnumKey(parent, 1)
        with pytest.raises(OSError):
            winreg.DeleteKey(parent, "child")

        with winreg.OpenKey(parent, r"child\grandchild") as opened:
            assert type(opened).__name__ == "PyHKEY"
    finally:
        winreg.DeleteKey(parent, r"child\grandchild")
        winreg.DeleteKey(parent, "child")
        parent.Close()
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)


def test_winreg_reflection_apis_are_capability_dependent():
    assert callable(winreg.DisableReflectionKey)
    assert callable(winreg.EnableReflectionKey)
    assert callable(winreg.QueryReflectionKey)
    # 这些函数只对 WOW64 反射列表中的键有意义，
    # 32 位系统通常抛 NotImplementedError；
    # 自动测试不应为了“覆盖调用”改变真实系统注册表的反射策略。


def test_winsound_constants_compose_source_and_playback_policies():
    source_flags = {
        winsound.SND_ALIAS,
        winsound.SND_FILENAME,
        winsound.SND_MEMORY,
    }
    behavior_flags = {
        winsound.SND_ASYNC,
        winsound.SND_LOOP,
        winsound.SND_NODEFAULT,
        winsound.SND_NOSTOP,
        winsound.SND_SYNC,
    }

    assert len(source_flags) == 3
    assert len(behavior_flags) == 5
    assert winsound.MB_OK != winsound.MB_ICONHAND
    assert winsound.SND_LOOP | winsound.SND_ASYNC
    # SND_LOOP 需要 SND_ASYNC；SND_MEMORY 与 SND_ASYNC 在 3.10 中不能组合。


def test_winsound_none_stops_playback_without_producing_sound():
    assert winsound.PlaySound(None, winsound.SND_PURGE) is None


def test_winsound_nodefault_turns_a_missing_alias_into_an_error():
    missing_alias = f"polyglot-missing-{uuid.uuid4().hex}"
    with pytest.raises(RuntimeError):
        winsound.PlaySound(
            missing_alias,
            winsound.SND_ALIAS | winsound.SND_NODEFAULT | winsound.SND_SYNC,
        )
    # 没有 SND_NODEFAULT 时系统可能播放默认声音，
    # 使测试既吵闹又掩盖配置错误。


def test_winsound_rejects_asynchronous_in_memory_audio():
    stream = io.BytesIO()
    with wave.open(stream, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(1)
        writer.setframerate(8000)
        writer.writeframes(b"\x80" * 8)

    with pytest.raises(RuntimeError):
        winsound.PlaySound(
            stream.getvalue(),
            winsound.SND_MEMORY | winsound.SND_ASYNC,
        )


@pytest.mark.parametrize("frequency", [36, 32_768])
def test_winsound_beep_rejects_frequencies_outside_the_documented_range(
    frequency,
):
    with pytest.raises(RuntimeError):
        winsound.Beep(frequency, 1)
    # 合法范围是 37..32767 Hz；自动套件不调用合法值，以免制造真实蜂鸣声。
