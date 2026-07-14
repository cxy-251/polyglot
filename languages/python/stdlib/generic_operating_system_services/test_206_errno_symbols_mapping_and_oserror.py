"""206｜``errno`` 平台符号、``errorcode`` 反向映射与 ``OSError`` 分类。

errno 名称是 C 系统错误码的可读常量，具体可用集合由平台决定；业务分支应比较
``exc.errno`` 与符号常量，不解析可能本地化的错误文本。构造 OSError 时，CPython 会按
常见 errno 自动选择 FileNotFoundError、PermissionError 等更具体的内建异常子类。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.errno.integer-symbols python.errno.platform-dependent-symbols
# polyglot-covers: python.errno.errorcode python.errno.numeric-to-symbol-name
# polyglot-covers: python.errno.ENOENT python.errno.EACCES
# polyglot-covers: python.errno.EEXIST python.errno.EAGAIN
# polyglot-covers: python.errno.OSError.errno python.errno.OSError.filename
# polyglot-covers: python.errno.OSError-subclass-dispatch
# polyglot-covers: python.errno.os.strerror python.errno.localized-message-caveat

import errno
import os

import pytest


def test_errorcode_entries_point_back_to_available_integer_constants():
    """同值 alias 可能只保留一个规范名称，因此不要反向假设每个 alias 都出现。"""

    assert errno.errorcode[errno.ENOENT] == "ENOENT"
    assert errno.errorcode[errno.EACCES] in {"EACCES", "EPERM"}

    for number, name in errno.errorcode.items():
        assert isinstance(number, int)
        assert name.startswith("E")
        assert getattr(errno, name) == number


def test_real_missing_path_exposes_symbolic_errno_and_filename(tmp_path):
    """高级异常类型便于捕获，errno 仍保留底层可移植错误原因。"""

    missing = tmp_path / "does-not-exist"

    with pytest.raises(FileNotFoundError) as raised:
        os.open(missing, os.O_RDONLY)

    assert raised.value.errno == errno.ENOENT
    assert raised.value.filename == str(missing)
    assert errno.errorcode[raised.value.errno] == "ENOENT"


@pytest.mark.parametrize(
    ("number", "expected_type"),
    [
        (errno.ENOENT, FileNotFoundError),
        (errno.EACCES, PermissionError),
        (errno.EEXIST, FileExistsError),
        (errno.EAGAIN, BlockingIOError),
    ],
)
def test_oserror_constructor_dispatches_common_errno_to_specific_subclass(
    number,
    expected_type,
):
    """该自动分派发生在直接构造 OSError；构造任意自定义子类时不会再次改类。"""

    error = OSError(number, os.strerror(number), "resource")

    assert type(error) is expected_type
    assert error.errno == number
    assert error.filename == "resource"


def test_strerror_is_for_people_and_may_be_localized():
    """只依赖它返回非空文本；机器逻辑继续使用 errno 整数。"""

    message = os.strerror(errno.ENOENT)

    assert isinstance(message, str)
    assert message
