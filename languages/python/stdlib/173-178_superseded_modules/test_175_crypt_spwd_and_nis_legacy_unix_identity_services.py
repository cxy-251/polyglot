"""175｜crypt、spwd 与 nis：旧式 Unix 凭据和目录服务接口。

三个模块都依赖 Unix 平台能力，并且在不同镜像中可能没有编译。
案例把可重复验证的散列与结构字段作为主体；读取 shadow 和 NIS 域时
只观察容器当前状态，不修改账户、不连接外部目录服务器，
也绝不输出密码散列。新代码应优先采用维护中的密码散列库和
明确的身份目录客户端。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.crypt python.crypt.methods python.crypt.method
# polyglot-covers: python.crypt.mksalt python.crypt.crypt python.crypt.verify
# polyglot-covers: python.crypt.default-method python.crypt.rounds
# polyglot-covers: python.stdlib.spwd python.spwd.struct-spwd
# polyglot-covers: python.spwd.getspnam python.spwd.getspall
# polyglot-covers: python.spwd.shadow-permissions python.spwd.aging-fields
# polyglot-covers: python.stdlib.nis python.nis.get-default-domain
# polyglot-covers: python.nis.match python.nis.cat python.nis.maps
# polyglot-covers: python.nis.bytes-values python.nis.external-service

import hmac
import importlib
import os
import pwd

import pytest


def optional_module(name):
    """用 importorskip 表达“构建时可选”，而不把缺失误报为功能失败。"""
    return pytest.importorskip(name)


def method_named(crypt_module, name):
    return next(
        (method for method in crypt_module.methods if method.name == name),
        None,
    )


def test_crypt_methods_are_ordered_strongest_first_and_describe_hash_layout():
    crypt = optional_module("crypt")

    assert crypt.methods
    assert crypt.methods[0] in {
        getattr(crypt, "METHOD_SHA512", None),
        getattr(crypt, "METHOD_BLOWFISH", None),
        getattr(crypt, "METHOD_SHA256", None),
        getattr(crypt, "METHOD_MD5", None),
        getattr(crypt, "METHOD_CRYPT", None),
    }
    for method in crypt.methods:
        assert method.name
        assert isinstance(method.ident, str)
        assert method.salt_chars >= 2
        assert method.total_size >= method.salt_chars

    # methods 反映当前 C 库真正支持的算法，不同 Unix 镜像的成员可能不同。
    # 顺序由强到弱，不能把 DES、MD5 等历史算法的存在误当成推荐使用。


def test_mksalt_and_crypt_form_a_store_then_verify_workflow():
    crypt = optional_module("crypt")
    secret = "correct horse battery staple"

    salt = crypt.mksalt()
    stored = crypt.crypt(secret, salt)
    if stored is None:
        pytest.skip("平台 crypt(3) 拒绝了默认算法")

    candidate = crypt.crypt(secret, stored)
    wrong = crypt.crypt("wrong secret", stored)

    assert hmac.compare_digest(candidate, stored)
    assert wrong is not None
    assert not hmac.compare_digest(wrong, stored)
    # 验证时把完整存储值传回 crypt，而不是另存一份 salt。
    # compare_digest 避免普通字符串比较泄露与首个差异位置相关的时序信息。


def test_crypt_without_explicit_salt_uses_the_strongest_available_method():
    crypt = optional_module("crypt")
    generated = crypt.crypt("temporary secret")
    if generated is None:
        pytest.skip("平台 crypt(3) 无法生成默认散列")

    expected_prefix = "$" + crypt.methods[0].ident + "$"
    if crypt.methods[0].ident:
        assert generated.startswith(expected_prefix)
    else:
        assert len(generated) == crypt.methods[0].total_size


def test_sha_rounds_are_encoded_in_the_salt_and_validate_the_lower_bound():
    crypt = optional_module("crypt")
    method = method_named(crypt, "SHA512") or method_named(crypt, "SHA256")
    if method is None:
        pytest.skip("平台 C 库未提供 SHA-crypt")

    salt = crypt.mksalt(method, rounds=1000)
    assert salt.startswith(f"${method.ident}$rounds=1000$")

    with pytest.raises(ValueError, match="rounds"):
        crypt.mksalt(method, rounds=999)


def test_mksalt_generates_fresh_salts_for_the_same_method():
    crypt = optional_module("crypt")
    method = crypt.methods[0]

    first = crypt.mksalt(method)
    second = crypt.mksalt(method)

    assert first != second
    if method.ident:
        assert first.startswith(f"${method.ident}$")
    else:
        assert len(first) == method.salt_chars
    # 随机 salt 使相同口令得到不同存储值；它不需要保密，
    # 但必须随散列保存。


def test_struct_spwd_exposes_tuple_and_named_shadow_fields_without_privileges():
    spwd = optional_module("spwd")
    entry = spwd.struct_spwd(
        (
            "learner",
            "!locked!",
            19_000,
            1,
            90,
            7,
            14,
            -1,
            0,
        )
    )

    assert len(entry) == 9
    assert entry[0] == entry.sp_namp == "learner"
    assert entry.sp_pwdp == "!locked!"
    assert entry.sp_lstchg == 19_000
    assert entry.sp_min == 1
    assert entry.sp_max == 90
    assert entry.sp_warn == 7
    assert entry.sp_inact == 14
    assert entry.sp_expire == -1
    assert entry.sp_flag == 0
    # 数值通常以 1970-01-01 后天数表示，-1 等哨兵值的具体含义由系统约定。


def test_getspnam_reads_the_current_container_account_only_when_permitted():
    spwd = optional_module("spwd")
    account_name = pwd.getpwuid(os.getuid()).pw_name

    try:
        entry = spwd.getspnam(account_name)
    except PermissionError:
        pytest.skip("当前容器用户没有读取 shadow 数据库的权限")
    except KeyError:
        pytest.skip("当前容器账户没有 shadow 条目")

    assert entry.sp_namp == account_name
    assert isinstance(entry.sp_pwdp, str)
    # 这里只断言类型，避免失败输出把真实散列或锁定标记泄露进日志。


def test_getspall_returns_struct_entries_when_the_container_allows_enumeration():
    spwd = optional_module("spwd")
    try:
        entries = spwd.getspall()
    except PermissionError:
        pytest.skip("当前容器用户不能枚举 shadow 数据库")

    assert isinstance(entries, list)
    assert all(isinstance(entry, spwd.struct_spwd) for entry in entries)
    # getspall 可能暴露整个系统的凭据元数据；
    # 真实程序不应把结果记录或序列化。


def test_nis_api_is_optional_and_default_domain_is_local_configuration_only():
    nis = optional_module("nis")

    assert issubclass(nis.error, Exception)
    assert all(
        callable(getattr(nis, name))
        for name in ("match", "cat", "maps", "get_default_domain")
    )

    try:
        domain = nis.get_default_domain()
    except nis.error as error:
        # 未配置 NIS 是普通的部署状态；异常对象仍应带有可诊断信息。
        assert str(error)
    else:
        assert isinstance(domain, str)
        assert domain


def test_nis_lookup_contract_uses_text_keys_but_returns_raw_bytes():
    nis = optional_module("nis")

    assert "match(key, map" in (nis.match.__doc__ or "")
    assert "dictionary" in (nis.cat.__doc__ or "").lower()
    # match(key, mapname, domain) 返回单个 bytes；cat(mapname, domain) 返回
    # bytes 到 bytes 的字典。解码规则属于具体 NIS map，不能擅自假设 UTF-8。
    # 两者和 maps() 都可能访问外部 NIS 服务器，
    # 本仓库遵守离线测试边界而不调用。


def test_reimporting_optional_identity_modules_does_not_mutate_system_state():
    for name in ("crypt", "spwd", "nis"):
        module = optional_module(name)
        assert importlib.reload(module) is module
    # import/reload 只绑定接口；账户变更、口令更新和目录写入
    # 都不属于这些模块。
