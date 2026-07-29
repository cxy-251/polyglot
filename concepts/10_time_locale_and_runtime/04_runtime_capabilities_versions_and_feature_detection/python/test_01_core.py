"""运行时能力、版本与特性检测。

共同问题：代码如何识别当前实现和版本；如何检测某项能力是否真正存在；
何时应检测行为或接口而不是脆弱地比较版本字符串。
"""

# polyglot-family: time_locale_and_runtime
# polyglot-concept: runtime_capabilities_versions_and_feature_detection
# polyglot-related: languages/python/stdlib/153-158_python_runtime_services/
# polyglot-related+: test_153_sys_sysconfig_site_and_main_runtime_environment.py

import importlib.util
import platform
import sys
import sysconfig


def test_version_info_is_structured_and_orderable():
    assert "3.10" < "3.9"
    assert (3, 10) > (3, 9)
    assert sys.version_info[:2] == (
        sys.version_info.major,
        sys.version_info.minor,
    )
    assert isinstance(sys.version, str)


def test_module_capability_can_be_detected_without_import_side_effects():
    assert importlib.util.find_spec("json") is not None
    assert importlib.util.find_spec("module_that_polyglot_does_not_ship") is None


def test_attribute_detection_checks_the_interface_directly():
    remove_prefix = getattr(str, "removeprefix", None)
    assert callable(remove_prefix)
    assert remove_prefix("prefix-value", "prefix-") == "value"
    assert remove_prefix("value", "prefix-") == "value"

    get_total_refcount = getattr(sys, "gettotalrefcount", None)
    if get_total_refcount is not None:
        assert callable(get_total_refcount)
        assert isinstance(get_total_refcount(), int)

    # gettotalrefcount 属于 CPython debug build；实现名称或版本号都不能保证该能力存在。


def test_implementation_metadata_is_separate_from_language_version():
    assert platform.python_implementation().casefold() == sys.implementation.name
    assert sys.implementation.version.major == sys.version_info.major
    assert isinstance(sysconfig.get_platform(), str)

    # Python 版本、解释器实现和构建平台分别约束语法、实现扩展与二进制兼容性。
