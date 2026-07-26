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


def test_version_info_is_structured_and_orderable():
    assert sys.version_info >= (3, 10)
    assert sys.version_info.major == 3
    assert isinstance(sys.version, str)


def test_module_capability_can_be_detected_without_import_side_effects():
    assert importlib.util.find_spec("json") is not None
    assert importlib.util.find_spec("module_that_polyglot_does_not_ship") is None


def test_attribute_detection_checks_the_interface_directly():
    assert callable(getattr(str, "removeprefix", None))
    assert getattr(sys, "gettotalrefcount", None) is None

    # gettotalrefcount 属于 CPython debug build；实现名称或版本号都不能保证该能力存在。


def test_implementation_metadata_is_separate_from_language_version():
    assert platform.python_implementation() == "CPython"
    assert sys.implementation.name == "cpython"
    assert sys.implementation.version.major == sys.version_info.major
