"""166｜system configuration、platform constants、``urandom`` 与 ``getrandom``。

``cpu_count`` 描述机器 CPU 数而非当前 process affinity；confstr/sysconf 的已知
名称来自 mapping，值仍由 host 决定。OS randomness 可用于加密，但应用层 token
通常应优先使用 ``secrets``；``getrandom`` 还允许 short read，caller 必须累计。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.os.uname python.os.uname-result
# polyglot-covers: python.os.confstr python.os.confstr-names
# polyglot-covers: python.os.sysconf python.os.sysconf-names
# polyglot-covers: python.os.cpu-count python.os.getloadavg
# polyglot-covers: python.os.curdir python.os.pardir python.os.sep python.os.altsep
# polyglot-covers: python.os.extsep python.os.linesep python.os.devnull
# polyglot-covers: python.os.urandom python.os.os-random-bytes
# polyglot-covers: python.os.getrandom python.os.getrandom-short-read
# polyglot-covers: python.os.GRND_NONBLOCK python.os.randomness-layer-choice

import os

import pytest


@pytest.mark.skipif(not hasattr(os, "uname"), reason="平台不提供 uname")
def test_uname_is_named_tuple_without_assuming_specific_host_values():
    """测试结构和非空字段，不把 container/host 的 identity 固化成 fixture。"""

    info = os.uname()

    assert len(info) == 5
    assert tuple(info) == (
        info.sysname,
        info.nodename,
        info.release,
        info.version,
        info.machine,
    )
    assert info.sysname
    assert info.machine


@pytest.mark.skipif(not hasattr(os, "sysconf"), reason="平台不提供 sysconf")
def test_sysconf_uses_discoverable_names_and_rejects_unknown_string():
    """known mapping 只保证名称可传；具体值可为 -1，表示 host 未定义。"""

    name = "SC_OPEN_MAX"
    if name not in os.sysconf_names:
        pytest.skip(f"host 不认识 {name}")

    value = os.sysconf(name)
    assert type(value) is int
    assert os.sysconf_names[name] == os.sysconf_names.get(name)
    with pytest.raises(ValueError):
        os.sysconf("POLYGLOT_UNKNOWN_SYSCONF")


@pytest.mark.skipif(not hasattr(os, "confstr"), reason="平台不提供 confstr")
def test_confstr_returns_string_or_none_for_a_known_name():
    """known name 的配置也可能未定义，此时返回 None 而非空字符串。"""

    name = "CS_PATH"
    if name not in os.confstr_names:
        pytest.skip(f"host 不认识 {name}")

    value = os.confstr(name)
    assert value is None or isinstance(value, str)
    with pytest.raises(ValueError):
        os.confstr("POLYGLOT_UNKNOWN_CONFSTR")


def test_cpu_load_and_path_constants_are_queries_not_path_parsers():
    """separator constants 用于显示/底层互操作；拼接和拆分仍应交给 os.path。"""

    count = os.cpu_count()
    assert count is None or count >= 1
    assert os.curdir
    assert os.pardir
    assert os.sep
    assert os.altsep is None or isinstance(os.altsep, str)
    assert os.extsep
    assert os.linesep

    with open(os.devnull, "wb") as sink:
        assert sink.write(b"discarded") == 9

    if hasattr(os, "getloadavg"):
        load = os.getloadavg()
        assert len(load) == 3
        assert all(value >= 0 for value in load)


def test_urandom_returns_exact_length_bytes_without_text_encoding():
    """随机 bytes 不应断言具体值；零长度请求也合法并精确返回 b''。"""

    first = os.urandom(16)
    second = os.urandom(16)

    assert type(first) is bytes
    assert len(first) == 16
    assert len(second) == 16
    assert os.urandom(0) == b""

    # “通常不同”不是可证明契约，不能作为 correctness assertion。


@pytest.mark.skipif(not hasattr(os, "getrandom"), reason="平台不提供 getrandom")
def test_getrandom_loop_handles_short_reads_without_requesting_random_pool():
    """默认 pool 适合本例；不调用可能消耗稀缺 entropy 的 GRND_RANDOM。"""

    chunks = []
    remaining = 32
    while remaining:
        try:
            chunk = os.getrandom(remaining, os.GRND_NONBLOCK)
        except BlockingIOError:
            pytest.skip("kernel entropy pool 尚未初始化，nonblocking read 暂不可用")
        if not chunk:
            pytest.fail("getrandom 在未满足请求时返回空 bytes")
        chunks.append(chunk)
        remaining -= len(chunk)

    result = b"".join(chunks)
    assert len(result) == 32
    assert type(result) is bytes
