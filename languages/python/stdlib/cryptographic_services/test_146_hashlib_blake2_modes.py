"""146｜``hashlib.blake2b/blake2s`` digest size、key、salt、person 与 tree mode。

BLAKE2 除普通 hash 外还原生支持 keyed MAC、随机化 salt、domain-separation person 和
tree hashing。digest_size 是算法参数，因此短摘要不是长摘要的 prefix。salt/person
会补零到固定宽度；key 的尾随 NUL 是真实 material，三者不能混用。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.hashlib.blake2b python.hashlib.blake2s
# polyglot-covers: python.hashlib.blake2-digest-size python.hashlib.blake2-not-prefix
# polyglot-covers: python.hashlib.blake2-keyed python.hashlib.blake2-MAC
# polyglot-covers: python.hashlib.blake2-salt python.hashlib.blake2-salt-padding
# polyglot-covers: python.hashlib.blake2-person python.hashlib.blake2-domain-separation
# polyglot-covers: python.hashlib.blake2-key-nul-significant
# polyglot-covers: python.hashlib.blake2-constants python.hashlib.blake2-parameter-bounds
# polyglot-covers: python.hashlib.blake2-positional-data python.hashlib.blake2-tree-mode
# polyglot-covers: python.hashlib.blake2-node-offset python.hashlib.blake2-last-node

import hashlib
import hmac

import pytest


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
