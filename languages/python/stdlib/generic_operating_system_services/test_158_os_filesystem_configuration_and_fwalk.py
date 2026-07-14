"""158｜``statvfs``、path configuration、device numbers 与 descriptor traversal。

这些查询描述当前 host/filesystem 能力，不应把某台机器的具体数值写死。
``pathconf_names``/``sysconf_names`` mapping 用于发现已知名称，而不是保证 kernel
支持每一个值；未知名称与已知但不可用的名称会以不同异常表达。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.os.statvfs python.os.statvfs-result
# polyglot-covers: python.os.ST_RDONLY python.os.ST_NOSUID
# polyglot-covers: python.os.pathconf python.os.pathconf-names
# polyglot-covers: python.os.fpathconf python.os.pathconf-unknown-name
# polyglot-covers: python.os.major python.os.minor python.os.makedev
# polyglot-covers: python.os.device-number-roundtrip python.os.filesystem-capability-query

import os

import pytest


@pytest.mark.skipif(not hasattr(os, "statvfs"), reason="平台不提供 statvfs")
def test_statvfs_reports_capacity_units_and_mount_flags(tmp_path):
    """block counts 必须乘 fragment size 才是 bytes；free 与 available 含义不同。"""

    info = os.statvfs(tmp_path)

    assert info.f_bsize > 0
    assert info.f_frsize > 0
    assert info.f_blocks >= info.f_bfree >= 0
    assert info.f_blocks >= info.f_bavail >= 0
    assert info.f_namemax > 0
    assert isinstance(info.f_flag & os.ST_RDONLY, int)
    assert isinstance(info.f_flag & os.ST_NOSUID, int)


@pytest.mark.skipif(not hasattr(os, "pathconf"), reason="平台不提供 pathconf")
def test_pathconf_accepts_symbolic_name_and_fd_and_rejects_unknown_name(tmp_path):
    """symbolic key 来自 pathconf_names；fd variant 避免再次解析路径。"""

    name = "PC_NAME_MAX"
    if name not in os.pathconf_names:
        pytest.skip(f"host 不认识 {name}")

    path_value = os.pathconf(tmp_path, name)
    fd = os.open(tmp_path, os.O_RDONLY)
    try:
        fd_value = os.fpathconf(fd, name)
    finally:
        os.close(fd)

    assert path_value == fd_value
    assert path_value > 0
    assert os.pathconf_names[name] == os.pathconf_names.get(name)
    with pytest.raises(ValueError):
        os.pathconf(tmp_path, "POLYGLOT_UNKNOWN_PATHCONF")


@pytest.mark.skipif(
    not all(hasattr(os, name) for name in ("major", "minor", "makedev")),
    reason="平台不暴露 Unix device number helpers",
)
def test_major_minor_and_makedev_round_trip_stat_device_number(tmp_path):
    """raw st_dev 不应自行按位拆分；布局由平台和三个 helper 定义。"""

    device = os.stat(tmp_path).st_dev
    major = os.major(device)
    minor = os.minor(device)

    assert major >= 0
    assert minor >= 0
    assert os.makedev(major, minor) == device
