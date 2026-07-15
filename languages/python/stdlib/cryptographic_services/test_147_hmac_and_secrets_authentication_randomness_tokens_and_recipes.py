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
import base64
import secrets
import string

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


# 148｜``secrets`` OS randomness、bounded values、token encodings 与安全比较。
#
# ``secrets`` 面向 password、reset token 和 authentication secret，底层使用操作系统
# 随机源；``random`` 面向模拟，不能替代它。随机测试只验证不变量，
# 不假设两次输出必然不同。token_* 参数表示 entropy bytes；默认长度可改变。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.secrets.SystemRandom python.secrets.os-randomness
# polyglot-covers: python.secrets.choice python.secrets.empty-choice
# polyglot-covers: python.secrets.randbelow python.secrets.randbelow-exclusive-upper
# polyglot-covers: python.secrets.randbits python.secrets.randbits-zero
# polyglot-covers: python.secrets.token-bytes python.secrets.token-hex
# polyglot-covers: python.secrets.token-urlsafe python.secrets.entropy-byte-count
# polyglot-covers: python.secrets.urlsafe-base64 python.secrets.default-token-length-variable
# polyglot-covers: python.secrets.compare-digest python.secrets.password-recipe
# polyglot-covers: python.secrets.random-vs-secrets python.secrets.random-test-invariants




def test_choice_returns_an_element_and_empty_sequences_raise():
    """不验证某个固定结果；正确不变量是返回值属于输入 domain。"""

    alphabet = "abc123"

    assert secrets.choice(alphabet) in alphabet
    with pytest.raises(IndexError):
        secrets.choice(())


def test_randbelow_uses_an_exclusive_upper_bound_and_rejects_empty_range():
    """结果范围是 [0, n)，因此可直接安全索引长度为 n 的 sequence。"""

    value = secrets.randbelow(10)

    assert type(value) is int
    assert 0 <= value < 10
    with pytest.raises(ValueError):
        secrets.randbelow(0)
    with pytest.raises(ValueError):
        secrets.randbelow(-1)


def test_randbits_limits_bit_width_and_zero_bits_is_exactly_zero():
    """k 表示最多使用的 bit 数；前导零不保留，所以 bit_length 可以小于 k。"""

    value = secrets.randbits(17)

    assert type(value) is int
    assert 0 <= value < 2**17
    assert value.bit_length() <= 17
    assert secrets.randbits(0) == 0
    with pytest.raises(ValueError):
        secrets.randbits(-1)


def test_system_random_exposes_the_operating_system_backed_generator():
    """SystemRandom 不依赖可复现 PRNG state；案例只检查 public random API contract。"""

    generator = secrets.SystemRandom()

    assert 0.0 <= generator.random() < 1.0
    assert 0 <= generator.randrange(5) < 5
    assert 0 <= generator.getrandbits(12) < 2**12


def test_token_byte_count_maps_to_each_output_encoding():
    """hex 每 byte 两字符；urlsafe 解码后仍是指定 entropy bytes。"""

    raw = secrets.token_bytes(10)
    hexadecimal = secrets.token_hex(10)
    urlsafe = secrets.token_urlsafe(10)

    assert type(raw) is bytes
    assert len(raw) == 10
    assert len(hexadecimal) == 20
    assert len(bytes.fromhex(hexadecimal)) == 10

    padding = "=" * (-len(urlsafe) % 4)
    decoded = base64.urlsafe_b64decode(urlsafe + padding)
    assert len(decoded) == 10
    assert set(urlsafe) <= set(string.ascii_letters + string.digits + "-_")


def test_zero_length_tokens_are_valid_empty_values():
    """显式 0 与省略参数不同；它能说明长度语义，但没有 entropy。"""

    assert secrets.token_bytes(0) == b""
    assert secrets.token_hex(0) == ""
    assert secrets.token_urlsafe(0) == ""


def test_default_token_length_is_intentionally_not_hard_coded():
    """官方允许默认值在 maintenance release 改变，调用协议应显式传长度。"""

    raw = secrets.token_bytes()
    hexadecimal = secrets.token_hex()
    urlsafe = secrets.token_urlsafe()

    assert isinstance(raw, bytes) and raw
    assert isinstance(hexadecimal, str) and hexadecimal
    assert isinstance(urlsafe, str) and urlsafe


def test_password_recipe_draws_each_character_from_a_deliberate_alphabet():
    """可确定验证长度/domain；不要断言每次都包含所有字符类别。"""

    alphabet = string.ascii_letters + string.digits
    password = "".join(secrets.choice(alphabet) for _ in range(20))

    assert len(password) == 20
    assert set(password) <= set(alphabet)


def test_compare_digest_is_the_timing_aware_verification_entry_point():
    """secrets 转出 compare_digest，遵守与 hmac 相同的同类型/ASCII text 规则。"""

    assert secrets.compare_digest(b"token", b"token") is True
    assert secrets.compare_digest(b"token", b"tampered") is False

    with pytest.raises(TypeError):
        secrets.compare_digest(b"token", "token")
