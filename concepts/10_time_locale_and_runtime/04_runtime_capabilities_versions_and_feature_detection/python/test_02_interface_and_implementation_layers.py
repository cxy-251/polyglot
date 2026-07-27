"""接口行为和实现层次。

共同问题：版本、实现和运行平台如何分开描述；如何验证真正可用的接口；
为什么字符串版本比较不能替代结构化版本与行为检测。
"""

# polyglot-family: time_locale_and_runtime
# polyglot-concept: runtime_capabilities_versions_and_feature_detection
# polyglot-related: languages/python/stdlib/153-158_python_runtime_services/
# polyglot-related+: test_153_sys_sysconfig_site_and_main_runtime_environment.py

import platform
import sys
import sysconfig


def test_structured_version_avoids_lexicographic_ordering_trap():
    assert "3.10" < "3.9"
    assert (3, 10) > (3, 9)
    assert sys.version_info[:2] == (3, 10)


def test_callable_interface_is_confirmed_by_behavior_not_only_version():
    remove_prefix = getattr(str, "removeprefix", None)

    assert callable(remove_prefix)
    assert remove_prefix("prefix-value", "prefix-") == "value"
    assert remove_prefix("value", "prefix-") == "value"


def test_language_runtime_and_platform_are_separate_dimensions():
    assert sys.version_info.major == 3
    assert sys.implementation.name == "cpython"
    assert platform.python_implementation() == "CPython"
    assert isinstance(sysconfig.get_platform(), str)

    # Python 版本、解释器实现和构建平台分别约束语法、实现扩展与二进制兼容性。
