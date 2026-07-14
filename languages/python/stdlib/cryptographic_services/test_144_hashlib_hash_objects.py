"""144｜``hashlib`` 通用 hash object、增量输入、copy 与算法发现。

hash 函数接收 bytes-like 数据并生成摘要；它不是加密，不能还原输入。
``digest``/``hexdigest`` 不会 finalize object，后续仍可 update。``copy`` 适合复用公共
prefix；算法名称集合则区分跨平台保证与当前 OpenSSL build 额外提供的实现。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.hashlib.sha256 python.hashlib.named-constructor
# polyglot-covers: python.hashlib.md5 python.hashlib.sha1
# polyglot-covers: python.hashlib.sha224 python.hashlib.sha384
# polyglot-covers: python.hashlib.sha512 python.hashlib.sha3-family
# polyglot-covers: python.hashlib.new python.hashlib.algorithms-guaranteed
# polyglot-covers: python.hashlib.algorithms-available python.hashlib.unknown-algorithm
# polyglot-covers: python.hashlib.hash.update python.hashlib.incremental-equivalence
# polyglot-covers: python.hashlib.bytes-like-input python.hashlib.text-input-error
# polyglot-covers: python.hashlib.hash.digest python.hashlib.hash.hexdigest
# polyglot-covers: python.hashlib.hash.digest-size python.hashlib.hash.block-size
# polyglot-covers: python.hashlib.hash.name python.hashlib.non-finalizing-digest
# polyglot-covers: python.hashlib.hash.copy python.hashlib.common-prefix-branch
# polyglot-covers: python.hashlib.usedforsecurity python.hashlib.hash-not-encryption

import hashlib

import pytest


def test_sha256_known_vector_and_hash_object_metadata():
    """已知向量同时说明 digest 是 bytes，hexdigest 是两倍长度的 ASCII hex。"""

    hashed = hashlib.sha256(b"abc")

    assert hashed.hexdigest() == (
        "ba7816bf8f01cfea414140de5dae2223"
        "b00361a396177a9cb410ff61f20015ad"
    )
    assert hashed.digest().hex() == hashed.hexdigest()
    assert isinstance(hashed.digest(), bytes)
    assert hashed.digest_size == 32
    assert hashed.block_size == 64
    assert hashed.name == "sha256"


@pytest.mark.parametrize(
    ("constructor", "digest_size"),
    [
        (hashlib.md5, 16),
        (hashlib.sha1, 20),
        (hashlib.sha224, 28),
        (hashlib.sha256, 32),
        (hashlib.sha384, 48),
        (hashlib.sha512, 64),
        (hashlib.sha3_224, 28),
        (hashlib.sha3_256, 32),
        (hashlib.sha3_384, 48),
        (hashlib.sha3_512, 64),
    ],
)
def test_guaranteed_named_fixed_digest_constructors_share_one_interface(
    constructor,
    digest_size,
):
    """MD5/SHA-1 仅作兼容展示；known collision weakness 下不应用于新安全设计。"""

    hashed = constructor(b"abc", usedforsecurity=False)

    assert len(hashed.digest()) == digest_size
    assert len(hashed.hexdigest()) == digest_size * 2
    assert hashlib.new(
        hashed.name,
        b"abc",
        usedforsecurity=False,
    ).digest() == hashed.digest()


def test_incremental_updates_equal_hashing_the_concatenated_bytes():
    """chunk boundary 不进入摘要语义，适合逐块读取大文件或网络数据。"""

    incremental = hashlib.sha256()
    assert incremental.update(b"prefix-") is None
    incremental.update(memoryview(b"payload"))

    assert incremental.digest() == hashlib.sha256(b"prefix-payload").digest()


def test_hashes_accept_bytes_like_objects_but_reject_text():
    """str 必须先选择 encoding；隐式编码会让同一文本产生歧义。"""

    assert hashlib.sha256(bytearray(b"data")).digest() == hashlib.sha256(b"data").digest()

    with pytest.raises(TypeError):
        hashlib.sha256("data")
    with pytest.raises(TypeError):
        hashlib.sha256().update("data")


def test_reading_digest_does_not_finalize_or_consume_state():
    """可在中途查看 snapshot 后继续 update；已返回的 bytes 不会变化。"""

    hashed = hashlib.sha256(b"first")
    first_snapshot = hashed.digest()

    assert hashed.digest() == first_snapshot
    hashed.update(b"-second")

    assert first_snapshot == hashlib.sha256(b"first").digest()
    assert hashed.digest() == hashlib.sha256(b"first-second").digest()


def test_copy_branches_from_a_shared_prefix_without_rehashing_it():
    """copy clone 当前内部 state；两个 branch 后续 update 互不影响。"""

    common = hashlib.sha256(b"version=1&")
    admin = common.copy()
    guest = common.copy()
    admin.update(b"role=admin")
    guest.update(b"role=guest")

    assert admin.digest() == hashlib.sha256(b"version=1&role=admin").digest()
    assert guest.digest() == hashlib.sha256(b"version=1&role=guest").digest()
    assert common.digest() == hashlib.sha256(b"version=1&").digest()


def test_generic_constructor_and_algorithm_sets_separate_portable_from_local():
    """guaranteed 是 portable baseline；available 可含 OpenSSL aliases 和额外算法。"""

    assert hashlib.algorithms_guaranteed <= hashlib.algorithms_available
    assert {"sha256", "sha512", "blake2b", "blake2s"} <= (
        hashlib.algorithms_guaranteed
    )

    generic = hashlib.new("sha256", b"payload")
    assert generic.name == "sha256"
    assert generic.digest() == hashlib.sha256(b"payload").digest()

    with pytest.raises(ValueError, match="unsupported hash type"):
        hashlib.new("definitely-not-an-algorithm")


def test_usedforsecurity_marks_policy_intent_without_changing_sha256_math():
    """False 标记受限 build 中的非安全用途，不改变算法摘要。"""

    security = hashlib.sha256(b"content", usedforsecurity=True)
    non_security = hashlib.sha256(b"content", usedforsecurity=False)

    assert security.digest() == non_security.digest()
