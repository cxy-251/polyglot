"""147｜``hmac`` 增量消息认证、one-shot digest、copy 与 constant-time compare。

HMAC 用 secret key 和 hash 构造 message authentication code，既验证完整性也验证持有
同一 key；普通 hash 只能检测偶然变化，不能证明发送方。外部 tag 应使用
``compare_digest``，避免 ``==`` 按第一个不同位置提前返回所带来的 timing signal。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.hmac.new python.hmac.required-digestmod
# polyglot-covers: python.hmac.key-bytes python.hmac.key-bytearray
# polyglot-covers: python.hmac.initial-message python.hmac.HMAC.update
# polyglot-covers: python.hmac.digestmod-name python.hmac.digestmod-constructor
# polyglot-covers: python.hmac.HMAC.digest python.hmac.HMAC.hexdigest
# polyglot-covers: python.hmac.HMAC.digest-size python.hmac.HMAC.block-size
# polyglot-covers: python.hmac.HMAC.name python.hmac.HMAC.copy
# polyglot-covers: python.hmac.digest-one-shot python.hmac.incremental-equivalence
# polyglot-covers: python.hmac.compare-digest python.hmac.timing-safe-verification
# polyglot-covers: python.hmac.compare-type-rule python.hmac.ascii-str-only
# polyglot-covers: python.hmac.key-changes-tag python.hmac.message-changes-tag

import hashlib
import hmac

import pytest


def test_hmac_sha256_matches_a_known_vector_and_exposes_metadata():
    """digestmod 必填；name 组合 hmac- 与 canonical hash name。"""

    authenticated = hmac.new(
        b"key",
        b"The quick brown fox jumps over the lazy dog",
        digestmod="sha256",
    )

    assert authenticated.hexdigest() == (
        "f7bc83f430538424b13298e6aa6fb143"
        "ef4d59a14946175997479dbc2d1a3cd8"
    )
    assert authenticated.digest().hex() == authenticated.hexdigest()
    assert authenticated.digest_size == 32
    assert authenticated.block_size == 64
    assert authenticated.name == "hmac-sha256"

    with pytest.raises(TypeError, match="digestmod"):
        hmac.new(b"key")


def test_digestmod_accepts_algorithm_name_or_constructor():
    """字符串名称可走 OpenSSL optimized path；constructor 形式便于注入算法。"""

    by_name = hmac.new(b"key", b"message", digestmod="sha256")
    by_constructor = hmac.new(b"key", b"message", digestmod=hashlib.sha256)

    assert by_name.digest() == by_constructor.digest()


def test_bytearray_key_and_bytes_like_message_are_supported():
    """key 明确只接受 bytes/bytearray；message follow hashlib 的 buffer protocol。"""

    mutable_inputs = hmac.new(
        bytearray(b"key"),
        memoryview(b"message"),
        digestmod="sha256",
    )
    immutable_inputs = hmac.new(b"key", b"message", digestmod="sha256")

    assert mutable_inputs.digest() == immutable_inputs.digest()
    with pytest.raises(TypeError):
        hmac.new("key", b"message", digestmod="sha256")


def test_incremental_update_and_one_shot_digest_produce_the_same_tag():
    """chunk boundary 不影响 MAC；hmac.digest 适合内存中的完整 message。"""

    streamed = hmac.new(b"secret", digestmod="sha256")
    assert streamed.update(b"part-1") is None
    streamed.update(b"-part-2")

    expected = hmac.digest(b"secret", b"part-1-part-2", "sha256")

    assert streamed.digest() == expected
    assert hmac.digest(b"secret", b"part-1-part-2", hashlib.sha256) == expected


def test_copy_branches_from_a_shared_authenticated_prefix():
    """与 hash.copy 相同，HMAC copy clone 内部 pad/state，随后分支互不影响。"""

    common = hmac.new(b"secret", b"version=1&", digestmod="sha256")
    admin = common.copy()
    guest = common.copy()
    admin.update(b"role=admin")
    guest.update(b"role=guest")

    assert admin.digest() == hmac.digest(
        b"secret",
        b"version=1&role=admin",
        "sha256",
    )
    assert guest.digest() == hmac.digest(
        b"secret",
        b"version=1&role=guest",
        "sha256",
    )
    assert common.digest() != admin.digest()


def test_key_and_message_both_participate_in_authentication_tag():
    """攻击者只重算普通 hash 不够；不知道 secret key 就不能生成正确 HMAC。"""

    original = hmac.digest(b"secret-A", b"amount=10", "sha256")

    assert original != hmac.digest(b"secret-B", b"amount=10", "sha256")
    assert original != hmac.digest(b"secret-A", b"amount=100", "sha256")


def test_compare_digest_supports_matching_ascii_or_bytes_like_types():
    """函数避免按内容早退；类型/长度仍可能泄露，应固定 tag 格式。"""

    assert hmac.compare_digest(b"same", b"same") is True
    assert hmac.compare_digest(memoryview(b"same"), b"same") is True
    assert hmac.compare_digest(b"same", b"different") is False
    assert hmac.compare_digest("a0ff", "a0ff") is True

    with pytest.raises(TypeError):
        hmac.compare_digest(b"same", "same")
    with pytest.raises(TypeError):
        hmac.compare_digest("你好", "你好")
