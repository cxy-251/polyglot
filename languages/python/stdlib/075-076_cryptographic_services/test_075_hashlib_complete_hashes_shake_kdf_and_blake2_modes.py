"""075｜``hashlib`` 通用 hash object、增量输入、copy 与算法发现。

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
import hmac

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


# ``hashlib`` SHAKE 可变摘要、PBKDF2 与 scrypt 密码派生。
#
# SHAKE 是 extendable-output function，调用 digest 时必须指定字节数。密码存储
# 不能直接使用一次快速 SHA-256；PBKDF2/scrypt 通过 salt 与可调 cost 做
# key stretching。
# 测试使用很小 cost；生产参数要依据当前硬件和安全要求制定。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.hashlib.shake-128 python.hashlib.shake-256
# polyglot-covers: python.hashlib.shake.digest-length python.hashlib.shake.hexdigest-length
# polyglot-covers: python.hashlib.shake-prefix python.hashlib.shake-length-required
# polyglot-covers: python.hashlib.pbkdf2-hmac python.hashlib.pbkdf2-known-vector
# polyglot-covers: python.hashlib.pbkdf2-dklen python.hashlib.pbkdf2-salt
# polyglot-covers: python.hashlib.pbkdf2-iterations python.hashlib.password-bytes
# polyglot-covers: python.hashlib.scrypt python.hashlib.scrypt-cost
# polyglot-covers: python.hashlib.scrypt-dklen python.hashlib.password-hash-pitfall




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


# ``hashlib.blake2b/blake2s`` digest size、key、salt、person 与 tree mode。
#
# BLAKE2 除普通 hash 外还原生支持 keyed MAC、随机化 salt、domain-separation person 和
# tree hashing。digest_size 是算法参数，因此短摘要不是长摘要的 prefix。salt/person
# 会补零到固定宽度；key 的尾随 NUL 是真实 material，三者不能混用。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.hashlib.blake2b python.hashlib.blake2s
# polyglot-covers: python.hashlib.blake2-digest-size python.hashlib.blake2-not-prefix
# polyglot-covers: python.hashlib.blake2-keyed python.hashlib.blake2-MAC
# polyglot-covers: python.hashlib.blake2-salt python.hashlib.blake2-salt-padding
# polyglot-covers: python.hashlib.blake2-person python.hashlib.blake2-domain-separation
# polyglot-covers: python.hashlib.blake2-key-nul-significant
# polyglot-covers: python.hashlib.blake2-constants python.hashlib.blake2-parameter-bounds
# polyglot-covers: python.hashlib.blake2-positional-data python.hashlib.blake2-tree-mode
# polyglot-covers: python.hashlib.blake2-node-offset python.hashlib.blake2-last-node




def test_digest_size_selects_a_distinct_blake2_function_not_truncation():
    """parameter block 包含 digest_size；短结果不等于默认结果前缀。"""

    message = b"same message"
    short = hashlib.blake2b(message, digest_size=16).digest()
    long = hashlib.blake2b(message, digest_size=64).digest()

    assert len(short) == 16
    assert len(long) == 64
    assert short != long[:16]
    assert hashlib.blake2s(message, digest_size=16).digest() != short


def test_keyed_mode_authenticates_message_and_key_together():
    """修改 message 或 key 都改变 MAC；验证外部 tag 时仍应使用 compare_digest。"""

    def sign(message, key):
        return hashlib.blake2b(message, key=key, digest_size=16).digest()

    tag = sign(b"user=alice", b"server-secret")

    assert hmac.compare_digest(tag, sign(b"user=alice", b"server-secret"))
    assert not hmac.compare_digest(tag, sign(b"user=bob", b"server-secret"))
    assert not hmac.compare_digest(tag, sign(b"user=alice", b"other-secret"))


def test_salt_is_zero_padded_but_key_trailing_nul_is_significant():
    """短 salt 补零到 SALT_SIZE；key 不补零，因此 b'key' 与 b'key\0' 不同。"""

    message = b"payload"

    assert hashlib.blake2b(message, salt=b"salt").digest() == hashlib.blake2b(
        message,
        salt=b"salt\0",
    ).digest()
    assert hashlib.blake2b(message, key=b"key").digest() != hashlib.blake2b(
        message,
        key=b"key\0",
    ).digest()


def test_personalization_separates_protocol_domains_for_identical_input():
    """person 建立 domain separation，避免相同输入跨协议复用 digest。"""

    content = b"identical bytes"
    file_digest = hashlib.blake2b(content, person=b"files", digest_size=32).digest()
    block_digest = hashlib.blake2b(content, person=b"blocks", digest_size=32).digest()

    assert file_digest != block_digest
    assert file_digest == hashlib.blake2b(
        content,
        person=b"files",
        digest_size=32,
    ).digest()


def test_blake2_constants_describe_variant_specific_limits():
    """b 的 digest/key/salt/person 上限均比 s 大，constructor 检查边界。"""

    assert hashlib.blake2b.MAX_DIGEST_SIZE == 64
    assert hashlib.blake2s.MAX_DIGEST_SIZE == 32
    assert hashlib.blake2b.MAX_KEY_SIZE == 64
    assert hashlib.blake2s.MAX_KEY_SIZE == 32
    assert hashlib.blake2b.SALT_SIZE == 16
    assert hashlib.blake2s.SALT_SIZE == 8
    assert hashlib.blake2b.PERSON_SIZE == 16
    assert hashlib.blake2s.PERSON_SIZE == 8

    with pytest.raises(ValueError):
        hashlib.blake2b(digest_size=0)
    with pytest.raises(ValueError):
        hashlib.blake2s(key=b"x" * 33)
    with pytest.raises(ValueError):
        hashlib.blake2b(person=b"x" * 17)


def test_initial_data_is_positional_only_while_mode_parameters_are_keywords():
    """data 只作第一个位置参数；其余 keyword-only，防止 bytes 参数错位。"""

    incremental = hashlib.blake2b()
    incremental.update(b"data")
    assert hashlib.blake2b(b"data").digest() == incremental.digest()

    with pytest.raises(TypeError):
        hashlib.blake2b(data=b"data")


def test_tree_mode_combines_parameterized_leaf_digests_at_a_root():
    """node_offset/node_depth/last_node 是 tree domain metadata，不只是并行调度提示。"""

    parts = [b"left", b"rght"]
    common = {
        "fanout": 2,
        "depth": 2,
        "leaf_size": 4,
        "inner_size": 64,
    }
    leaves = []
    for index, part in enumerate(parts):
        leaf = hashlib.blake2b(
            part,
            digest_size=64,
            node_offset=index,
            node_depth=0,
            last_node=index == len(parts) - 1,
            **common,
        )
        leaves.append(leaf.digest())

    root = hashlib.blake2b(
        digest_size=32,
        node_offset=0,
        node_depth=1,
        last_node=True,
        **common,
    )
    for leaf_digest in leaves:
        root.update(leaf_digest)

    tree_digest = root.digest()
    assert len(tree_digest) == 32
    assert tree_digest != hashlib.blake2b(b"".join(parts), digest_size=32).digest()

    # last_node 进入 parameter block；即使 payload 相同，右叶标志变化也改变 root。
    non_last_right = hashlib.blake2b(
        parts[1],
        digest_size=64,
        node_offset=1,
        node_depth=0,
        last_node=False,
        **common,
    ).digest()
    assert non_last_right != leaves[1]
