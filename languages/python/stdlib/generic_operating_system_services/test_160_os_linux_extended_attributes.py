"""160｜Linux extended attributes 的 create/get/list/replace/remove lifecycle。

extended attribute 是附在 inode 上的 named bytes value。``user.*`` namespace
通常可由普通用户使用，但仍取决于 filesystem policy；本文件只对明确的能力型
错误 skip，并严格检查 create-only 与 replace-only flags 的原子语义。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.os.setxattr python.os.getxattr
# polyglot-covers: python.os.listxattr python.os.removexattr
# polyglot-covers: python.os.XATTR_CREATE python.os.XATTR_REPLACE
# polyglot-covers: python.os.XATTR_SIZE_MAX python.os.extended-attribute-bytes
# polyglot-covers: python.os.xattr-create-existing-error
# polyglot-covers: python.os.xattr-replace-missing-error python.os.xattr-capability-guard

import errno
import os

import pytest


_UNSUPPORTED_ERRNOS = {
    errno.EACCES,
    errno.EPERM,
    errno.EOPNOTSUPP,
}


@pytest.mark.skipif(not hasattr(os, "setxattr"), reason="平台不提供 extended attributes")
def test_xattr_create_replace_list_and_remove_lifecycle(tmp_path):
    """flags 让 kernel 原子检查“必须不存在/已存在”，避免先查后改竞态。"""

    path = tmp_path / "item.bin"
    path.write_bytes(b"content")
    attribute = "user.polyglot-example"
    created = False
    try:
        try:
            os.setxattr(path, attribute, b"v1", os.XATTR_CREATE)
            created = True
        except OSError as error:
            if error.errno in _UNSUPPORTED_ERRNOS:
                pytest.skip(f"filesystem policy 不支持 user xattr: {error}")
            raise

        assert os.getxattr(path, attribute) == b"v1"
        assert attribute in os.listxattr(path)
        assert os.XATTR_SIZE_MAX >= len(b"v1")

        with pytest.raises(OSError) as duplicate:
            os.setxattr(path, attribute, b"again", os.XATTR_CREATE)
        assert duplicate.value.errno == errno.EEXIST

        os.setxattr(path, attribute, b"v2", os.XATTR_REPLACE)
        assert os.getxattr(path, attribute) == b"v2"

        os.removexattr(path, attribute)
        created = False
        with pytest.raises(OSError) as missing:
            os.setxattr(path, attribute, b"v3", os.XATTR_REPLACE)
        assert missing.value.errno in {errno.ENODATA, getattr(errno, "ENOATTR", -1)}
    finally:
        if created:
            os.removexattr(path, attribute)
