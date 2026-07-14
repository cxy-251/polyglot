"""203｜``platform`` 的 portable uname、展示字符串与 Python build 信息。

platform 返回的是“尽力识别”结果，无法确定的字段可能为空；测试只校验结构和同一进程
内部一致性，不硬编码容器 kernel、hostname 或 CPU。``platform()`` 明确面向人类展示，
不能作为稳定机器协议；自动判断应选择 system/machine 或 os-release 的结构化字段。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.platform.uname python.platform.uname-namedtuple
# polyglot-covers: python.platform.system python.platform.node
# polyglot-covers: python.platform.release python.platform.version
# polyglot-covers: python.platform.machine python.platform.processor
# polyglot-covers: python.platform.platform python.platform.platform-aliased
# polyglot-covers: python.platform.platform-terse python.platform.human-readable-warning
# polyglot-covers: python.platform.python_version python.platform.python_version_tuple
# polyglot-covers: python.platform.python_implementation
# polyglot-covers: python.platform.python_build python.platform.python_compiler
# polyglot-covers: python.platform.python_branch python.platform.python_revision

import platform
import sys


def test_uname_is_a_six_field_named_tuple_consistent_with_accessors():
    """platform.uname 比 os.uname 多 processor，且前两字段命名为 system/node。"""

    info = platform.uname()

    assert info._fields == (
        "system",
        "node",
        "release",
        "version",
        "machine",
        "processor",
    )
    assert tuple(info) == (
        platform.system(),
        platform.node(),
        platform.release(),
        platform.version(),
        platform.machine(),
        platform.processor(),
    )
    assert all(isinstance(value, str) for value in info)


def test_platform_string_options_remain_human_readable_not_machine_schema():
    """aliased/terse 改变信息选择；只可依赖返回 str，不应按连字符位置反解析。"""

    verbose = platform.platform(aliased=False, terse=False)
    aliased = platform.platform(aliased=True, terse=False)
    terse = platform.platform(aliased=False, terse=True)

    assert isinstance(verbose, str)
    assert isinstance(aliased, str)
    assert isinstance(terse, str)
    assert verbose
    assert terse


def test_python_version_helpers_match_structured_interpreter_version():
    """version tuple 元素是字符串；patchlevel 即使为零也不会省略。"""

    version_tuple = platform.python_version_tuple()

    assert len(version_tuple) == 3
    assert all(isinstance(part, str) for part in version_tuple)
    assert platform.python_version() == ".".join(version_tuple)
    assert tuple(map(int, version_tuple)) == tuple(sys.version_info[:3])
    assert platform.python_implementation().lower() == sys.implementation.name.lower()


def test_python_build_metadata_has_stable_shapes_but_platform_defined_values():
    """branch/revision 在 release build 中可能为空，不能据此判断解释器是否合法。"""

    build_number, build_date = platform.python_build()

    assert isinstance(build_number, str)
    assert isinstance(build_date, str)
    assert isinstance(platform.python_compiler(), str)
    assert isinstance(platform.python_branch(), str)
    assert isinstance(platform.python_revision(), str)
