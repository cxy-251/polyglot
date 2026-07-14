"""148｜``secrets`` OS randomness、bounded values、token encodings 与安全比较。

``secrets`` 面向 password、reset token 和 authentication secret，底层使用操作系统
随机源；``random`` 面向模拟，不能替代它。随机测试只验证不变量，
不假设两次输出必然不同。token_* 参数表示 entropy bytes；默认长度可改变。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.secrets.SystemRandom python.secrets.os-randomness
# polyglot-covers: python.secrets.choice python.secrets.empty-choice
# polyglot-covers: python.secrets.randbelow python.secrets.randbelow-exclusive-upper
# polyglot-covers: python.secrets.randbits python.secrets.randbits-zero
# polyglot-covers: python.secrets.token-bytes python.secrets.token-hex
# polyglot-covers: python.secrets.token-urlsafe python.secrets.entropy-byte-count
# polyglot-covers: python.secrets.urlsafe-base64 python.secrets.default-token-length-variable
# polyglot-covers: python.secrets.compare-digest python.secrets.password-recipe
# polyglot-covers: python.secrets.random-vs-secrets python.secrets.random-test-invariants

import base64
import secrets
import string

import pytest


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
