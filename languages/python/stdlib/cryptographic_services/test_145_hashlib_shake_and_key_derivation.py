"""145｜``hashlib`` SHAKE 可变摘要、PBKDF2 与 scrypt 密码派生。

SHAKE 是 extendable-output function，调用 digest 时必须指定字节数。密码存储
不能直接使用一次快速 SHA-256；PBKDF2/scrypt 通过 salt 与可调 cost 做
key stretching。
测试使用很小 cost；生产参数要依据当前硬件和安全要求制定。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.hashlib.shake-128 python.hashlib.shake-256
# polyglot-covers: python.hashlib.shake.digest-length python.hashlib.shake.hexdigest-length
# polyglot-covers: python.hashlib.shake-prefix python.hashlib.shake-length-required
# polyglot-covers: python.hashlib.pbkdf2-hmac python.hashlib.pbkdf2-known-vector
# polyglot-covers: python.hashlib.pbkdf2-dklen python.hashlib.pbkdf2-salt
# polyglot-covers: python.hashlib.pbkdf2-iterations python.hashlib.password-bytes
# polyglot-covers: python.hashlib.scrypt python.hashlib.scrypt-cost
# polyglot-covers: python.hashlib.scrypt-dklen python.hashlib.password-hash-pitfall

import hashlib

import pytest


@pytest.mark.parametrize("constructor", [hashlib.shake_128, hashlib.shake_256])
def test_shake_requires_output_length_and_hex_uses_twice_as_many_characters(constructor):
    """length 单位是 bytes；hexdigest(length) 因 hex encoding 长两倍。"""

    extendable = constructor(b"payload")

    assert len(extendable.digest(16)) == 16
    assert len(extendable.hexdigest(16)) == 32
    assert bytes.fromhex(extendable.hexdigest(16)) == extendable.digest(16)

    with pytest.raises(TypeError):
        extendable.digest()


def test_longer_shake_output_extends_the_same_prefix():
    """XOF 的短输出是同一 state 的长输出前缀，并非另一 digest mode。"""

    shake = hashlib.shake_256(b"same input")

    assert shake.digest(16) == shake.digest(32)[:16]
    assert shake.hexdigest(16) == shake.hexdigest(32)[:32]


def test_pbkdf2_hmac_matches_a_known_sha256_vector_and_dklen_truncates():
    """固定向量验证参数顺序；dklen=None 默认使用底层 digest size。"""

    full = hashlib.pbkdf2_hmac("sha256", b"password", b"salt", 1)

    assert full.hex() == (
        "120fb6cffcf8b32c43e7225256c4f837"
        "a86548c92ccc35480805987cb70be17b"
    )
    assert len(full) == hashlib.sha256().digest_size
    assert hashlib.pbkdf2_hmac("sha256", b"password", b"salt", 1, 16) == full[:16]


def test_pbkdf2_salt_and_iteration_count_are_part_of_derived_key():
    """salt 不必保密，但应随机且每个 credential 独立；cost 也进入结果。"""

    base = hashlib.pbkdf2_hmac("sha256", b"password", b"salt-A", 10, 16)
    other_salt = hashlib.pbkdf2_hmac("sha256", b"password", b"salt-B", 10, 16)
    other_cost = hashlib.pbkdf2_hmac("sha256", b"password", b"salt-A", 11, 16)

    assert base != other_salt
    assert base != other_cost


def test_password_and_salt_must_be_bytes_like_not_implicitly_encoded_text():
    """应用先固定 password normalization/encoding，再把 bytes 交给 KDF。"""

    with pytest.raises(TypeError):
        hashlib.pbkdf2_hmac("sha256", "password", b"salt", 1)
    with pytest.raises(TypeError):
        hashlib.pbkdf2_hmac("sha256", b"password", "salt", 1)


@pytest.mark.skipif(not hasattr(hashlib, "scrypt"), reason="此 build 未提供 OpenSSL scrypt")
def test_scrypt_uses_memory_cost_parameters_and_explicit_output_length():
    """小参数仅用于可执行示例；n 必须是大于 1 的 2 次幂。"""

    first = hashlib.scrypt(
        b"password",
        salt=b"0123456789abcdef",
        n=16,
        r=1,
        p=1,
        dklen=24,
    )
    second = hashlib.scrypt(
        b"password",
        salt=b"fedcba9876543210",
        n=16,
        r=1,
        p=1,
        dklen=24,
    )

    assert len(first) == 24
    assert first != second

    with pytest.raises(ValueError):
        hashlib.scrypt(b"password", salt=b"salt", n=15, r=1, p=1)


def test_plain_fast_hash_has_no_salt_or_cost_and_is_not_a_password_kdf():
    """相同 password 的裸 SHA-256 总相同；这个反例解释为何应选 KDF。"""

    first = hashlib.sha256(b"password").digest()
    second = hashlib.sha256(b"password").digest()

    assert first == second
    assert first != hashlib.pbkdf2_hmac("sha256", b"password", b"unique-salt", 10)
