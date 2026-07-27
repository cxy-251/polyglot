"""断言配置与运行时契约边界。

共同问题：开发断言能否被配置移除；类型约束是否检查运行时值；
公共 API 应采用什么稳定失败通道。
"""

# polyglot-family: errors_and_resources
# polyglot-concept: contracts_assertions_and_failure_signaling
# polyglot-related: languages/python/language/test_009_exception_handling_and_chaining.py

import subprocess
import sys

import pytest


def test_optimized_interpreter_removes_assert_statements():
    completed = subprocess.run(
        [sys.executable, "-O", "-c", "assert False; print('continued')"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == "continued"

    # 这是锁定 CPython 的真实优化模式边界：assert 适合内部不变量，不能承担输入校验。


def test_annotations_do_not_check_runtime_value_contracts():
    def positive(value: int) -> int:
        if value <= 0:
            raise ValueError("must be positive")
        return value

    assert positive(2) == 2
    with pytest.raises(TypeError):
        positive("2")
    with pytest.raises(ValueError, match="positive"):
        positive(-2)

    # 字符串失败来自函数体的比较，不是注解检查；正值约束同样必须由运行时代码实现。
