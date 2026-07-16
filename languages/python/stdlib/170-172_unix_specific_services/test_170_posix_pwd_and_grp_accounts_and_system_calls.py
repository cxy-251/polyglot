"""170｜posix、pwd 与 grp：Unix 系统调用入口和账户数据库。

posix 是 os 在 Unix 上使用的底层实现，
官方仍建议业务代码导入 os 以获得可移植接口和同步的环境映射。
pwd/grp 返回具名元组形式的系统账户记录；案例只读取
当前进程对应的记录，不打开真实用户目录，也不修改系统账户数据库。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.stdlib.posix python.posix.os-backend
# polyglot-covers: python.posix.system-call-errors python.posix.large-file-offset
# polyglot-covers: python.posix.environ-snapshot python.os.environb-synchronization
# polyglot-covers: python.stdlib.pwd python.pwd.getpwuid python.pwd.getpwnam
# polyglot-covers: python.pwd.getpwall python.pwd.struct-passwd
# polyglot-covers: python.pwd.namedtuple-fields python.pwd.missing-entry
# polyglot-covers: python.pwd.shadow-password-placeholder
# polyglot-covers: python.stdlib.grp python.grp.getgrgid python.grp.getgrnam
# polyglot-covers: python.grp.getgrall python.grp.struct-group
# polyglot-covers: python.grp.primary-vs-member-list python.grp.missing-entry

import os
import sys
import uuid

import pytest


pytestmark = pytest.mark.skipif(
    os.name != "posix",
    reason="posix、pwd 和 grp 仅在 Unix 平台提供",
)

if os.name == "posix":
    import grp
    import posix
    import pwd
else:
    grp = None
    posix = None
    pwd = None


def test_posix_is_the_unix_backend_but_os_is_the_portable_public_entry():
    assert os.name == "posix"
    assert posix.open is os.open
    assert posix.stat is os.stat
    assert posix.getpid is os.getpid
    assert hasattr(os, "path")
    assert not hasattr(posix, "path")
    # os 在 Unix 上重导出 posix，并额外提供 environ 同步、path 等跨平台服务。


def test_posix_file_calls_accept_large_offsets_without_legacy_32_bit_variants(
    tmp_path,
):
    path = tmp_path / "sparse.bin"
    descriptor = posix.open(
        path,
        posix.O_CREAT | posix.O_RDWR | posix.O_TRUNC,
        0o600,
    )
    try:
        offset = 2**31 + 7
        assert posix.lseek(descriptor, offset, os.SEEK_SET) == offset
        assert posix.write(descriptor, b"X") == 1
        stat_result = posix.fstat(descriptor)
    finally:
        posix.close(descriptor)

    assert stat_result.st_size == 2**31 + 8
    if hasattr(stat_result, "st_blocks"):
        assert stat_result.st_blocks * 512 < stat_result.st_size
    # 稀疏文件只占少量真实块；Python 3 不需要 open64/lseek64 这样的平行 API。


def test_posix_reports_oserror_subclasses_for_system_call_failures(tmp_path):
    missing = tmp_path / "missing"
    with pytest.raises(FileNotFoundError):
        posix.stat(missing)

    with pytest.raises(OSError):
        posix.close(-1)


def test_posix_environ_is_the_bytes_storage_shared_by_os_environb(monkeypatch):
    text_key = f"POLYGLOT_POSIX_{uuid.uuid4().hex}"
    byte_key = os.fsencode(text_key)
    monkeypatch.setenv(text_key, "updated")

    assert os.environ[text_key] == "updated"
    assert os.environb[byte_key] == b"updated"
    assert posix.environ[byte_key] == b"updated"
    assert os.environb._data is posix.environ
    assert all(
        isinstance(key, bytes) and isinstance(value, bytes)
        for key, value in list(posix.environ.items())[:5]
    )
    # os.environ/os.environb 是负责编码和 putenv/unsetenv 同步的公开包装；
    # posix.environ 是它们共享的 bytes 存储。直接改底层 dict 不会调用 putenv，
    # 因而仍不应把它当作 os.environb 的替代品。


def test_pwd_current_user_record_supports_indexes_and_named_fields():
    record = pwd.getpwuid(os.getuid())

    assert len(record) == 7
    assert record[0] == record.pw_name
    assert record[1] == record.pw_passwd
    assert record[2] == record.pw_uid == os.getuid()
    assert record[3] == record.pw_gid
    assert record[4] == record.pw_gecos
    assert record[5] == record.pw_dir
    assert record[6] == record.pw_shell
    assert isinstance(record.pw_name, str)
    assert isinstance(record.pw_uid, int)
    assert isinstance(record.pw_gid, int)
    assert all(isinstance(record[index], str) for index in (0, 1, 4, 5, 6))


def test_pwd_name_and_uid_lookups_return_the_same_account():
    by_uid = pwd.getpwuid(os.geteuid())
    by_name = pwd.getpwnam(by_uid.pw_name)

    assert by_name == by_uid
    assert type(by_name).__name__ == "struct_passwd"
    # pw_passwd 在现代系统通常只是 "x"、"*" 等 shadow 占位符，不能据此验密。


def test_pwd_getpwall_contains_current_user_but_order_is_unspecified():
    records = pwd.getpwall()
    current = pwd.getpwuid(os.getuid())

    assert records
    assert all(type(record).__name__ == "struct_passwd" for record in records)
    assert any(record.pw_uid == current.pw_uid for record in records)
    assert {record.pw_name for record in records}
    # 系统可能来自本地文件、LDAP 等 NSS 后端，
    # 因此不要依赖顺序或固定账户集合。


def test_pwd_missing_names_raise_key_error_and_names_must_be_text():
    missing = f"polyglot-user-{uuid.uuid4().hex}"
    with pytest.raises(KeyError):
        pwd.getpwnam(missing)

    with pytest.raises(TypeError):
        pwd.getpwnam(missing.encode())


def test_grp_current_primary_group_record_is_tuple_like():
    record = grp.getgrgid(os.getgid())

    assert len(record) == 4
    assert record[0] == record.gr_name
    assert record[1] == record.gr_passwd
    assert record[2] == record.gr_gid == os.getgid()
    assert record[3] == record.gr_mem
    assert isinstance(record.gr_name, str)
    assert isinstance(record.gr_gid, int)
    assert isinstance(record.gr_mem, list)
    assert all(isinstance(member, str) for member in record.gr_mem)


def test_grp_name_and_gid_lookups_return_the_same_group():
    by_gid = grp.getgrgid(os.getegid())
    by_name = grp.getgrnam(by_gid.gr_name)

    assert by_name == by_gid
    assert type(by_name).__name__ == "struct_group"


def test_grp_getgrall_and_getgrouplist_answer_different_questions():
    if not hasattr(os, "getgrouplist"):
        pytest.skip("当前 Unix 没有 getgrouplist")

    user = pwd.getpwuid(os.getuid())
    all_groups = grp.getgrall()
    process_groups = os.getgrouplist(user.pw_name, user.pw_gid)

    assert any(record.gr_gid == user.pw_gid for record in all_groups)
    assert user.pw_gid in process_groups
    assert all(isinstance(group_id, int) for group_id in process_groups)
    # 主组通常不会把用户名重复写进 gr_mem；
    # 判断用户所属组应使用 getgrouplist。


def test_grp_missing_names_raise_key_error():
    missing = f"polyglot-group-{uuid.uuid4().hex}"
    with pytest.raises(KeyError):
        grp.getgrnam(missing)

    with pytest.raises(TypeError):
        grp.getgrnam(missing.encode())


def test_platform_guards_are_preferable_to_assuming_linux():
    assert sys.platform
    assert os.name == "posix"
    # posix 可代表 Linux、macOS、BSD 等；具体常量仍应以 hasattr/平台文档探测。
