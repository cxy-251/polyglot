"""133｜uuid.UUID 的多种表示、位字段、版本生成器、节点选择和安全标记。

UUID 是不可变的 128 位值；文本、网络字节序、Microsoft 小端字段和分解字段
只是不同视图。随机与时间型入口只断言协议位及调用方可控字段，
避免依赖宿主机。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过
pytest 统一验证。
"""

# polyglot-covers: python.stdlib.uuid python.uuid.UUID-hex-normalization
# polyglot-covers: python.uuid.UUID-bytes python.uuid.UUID-bytes_le
# polyglot-covers: python.uuid.UUID-fields python.uuid.UUID-int
# polyglot-covers: python.uuid.UUID-version-override python.uuid.UUID-input-exclusivity
# polyglot-covers: python.uuid.UUID-properties python.uuid.UUID-urn
# polyglot-covers: python.uuid.UUID-immutable-hash-order
# polyglot-covers: python.uuid.variant-constants python.uuid.SafeUUID
# polyglot-covers: python.uuid.uuid1-node-clock-seq python.uuid.uuid1-rfc-bits
# polyglot-covers: python.uuid.uuid3 python.uuid.uuid5 python.uuid.namespaces
# polyglot-covers: python.uuid.uuid4-random-bytes-and-forced-bits
# polyglot-covers: python.uuid.getnode-validation-cache python.uuid.random-node-multicast-bit

import pickle

import uuid
import pytest


CANONICAL = "12345678-1234-5678-9234-567812345678"
NETWORK_BYTES = bytes.fromhex("12345678123456789234567812345678")
LITTLE_ENDIAN_BYTES = bytes.fromhex("78563412341278569234567812345678")


@pytest.mark.parametrize(
    "text",
    [
        CANONICAL,
        "12345678123456789234567812345678",
        "{12345678-1234-5678-9234-567812345678}",
        "urn:uuid:12345678-1234-5678-9234-567812345678",
    ],
)
def test_uuid_hex_constructor_normalizes_common_text_forms(text):
    value = uuid.UUID(text)

    assert str(value) == CANONICAL
    assert value.hex == CANONICAL.replace("-", "")
    assert value.urn == f"urn:uuid:{CANONICAL}"


def test_uuid_network_and_little_endian_bytes_are_distinct_views_of_same_value():
    network = uuid.UUID(bytes=NETWORK_BYTES)
    little = uuid.UUID(bytes_le=LITTLE_ENDIAN_BYTES)

    assert network == little == uuid.UUID(CANONICAL)
    assert network.bytes == NETWORK_BYTES
    assert network.bytes_le == LITTLE_ENDIAN_BYTES
    # bytes_le 只反转 time_low/time_mid/time_hi 三个字段；
    # 节点和 clock sequence 不反转。
    assert network.bytes[8:] == network.bytes_le[8:]


def test_uuid_fields_constructor_round_trips_each_rfc_component():
    fields = (
        0x12345678,
        0x1234,
        0x5678,
        0x92,
        0x34,
        0x567812345678,
    )
    value = uuid.UUID(fields=fields)

    assert value.fields == fields
    assert value.time_low == 0x12345678
    assert value.time_mid == 0x1234
    assert value.time_hi_version == 0x5678
    assert value.clock_seq_hi_variant == 0x92
    assert value.clock_seq_low == 0x34
    assert value.node == 0x567812345678
    assert value.clock_seq == 0x1234
    assert value.time == 0x678123412345678


def test_uuid_int_is_exact_128_bit_network_value():
    value = uuid.UUID(int=int.from_bytes(NETWORK_BYTES, "big"))

    assert value.bytes == NETWORK_BYTES
    assert value.int == int(CANONICAL.replace("-", ""), 16)


def test_uuid_version_override_rewrites_only_version_and_rfc_variant_bits():
    raw = uuid.UUID(int=0)
    versioned = uuid.UUID(int=0, version=4)

    assert raw.int == 0
    assert raw.version is None
    assert raw.variant == uuid.RESERVED_NCS

    assert versioned.version == 4
    assert versioned.variant == uuid.RFC_4122
    assert versioned.int != 0
    assert versioned.int & (0xF << 76) == 4 << 76
    assert versioned.int & (0b11 << 62) == 0b10 << 62


def test_uuid_constructor_requires_exactly_one_representation_and_valid_ranges():
    with pytest.raises(TypeError, match="one of the hex, bytes, bytes_le, fields, or int"):
        uuid.UUID()

    with pytest.raises(TypeError, match="one of the hex"):
        uuid.UUID(CANONICAL, bytes=NETWORK_BYTES)

    with pytest.raises(ValueError, match="16-char"):
        uuid.UUID(bytes=b"too short")

    with pytest.raises(ValueError, match="128-bit"):
        uuid.UUID(int=1 << 128)

    with pytest.raises(ValueError, match="illegal version number"):
        uuid.UUID(int=0, version=6)

    with pytest.raises(ValueError, match="field 1 out of range"):
        uuid.UUID(fields=(1 << 32, 0, 0, 0, 0, 0))


def test_uuid_is_immutable_hashable_orderable_and_pickleable():
    first = uuid.UUID(int=1)
    second = uuid.UUID(int=2)
    mapping = {first: "one"}

    assert mapping[uuid.UUID(int=1)] == "one"
    assert first < second
    assert sorted([second, first]) == [first, second]
    assert pickle.loads(pickle.dumps(first)) == first

    with pytest.raises(TypeError, match="immutable"):
        first.int = 3

    with pytest.raises(TypeError):
        first < "not a UUID"


def test_uuid_variant_constants_and_safe_enum_are_separate_concepts():
    assert uuid.RESERVED_NCS != uuid.RFC_4122
    assert uuid.RFC_4122 != uuid.RESERVED_MICROSOFT
    assert uuid.RESERVED_MICROSOFT != uuid.RESERVED_FUTURE

    assert {member.name for member in uuid.SafeUUID} == {"safe", "unsafe", "unknown"}
    safe = uuid.UUID(int=0, is_safe=uuid.SafeUUID.safe)
    assert safe.is_safe is uuid.SafeUUID.safe
    # is_safe 是生成来源元数据，不会改变 UUID 的 128 位身份值。
    assert safe == uuid.UUID(int=0, is_safe=uuid.SafeUUID.unknown)


def test_uuid1_uses_supplied_node_and_clock_sequence_but_generates_timestamp():
    value = uuid.uuid1(node=0x123456789ABC, clock_seq=0x1234)

    assert value.version == 1
    assert value.variant == uuid.RFC_4122
    assert value.node == 0x123456789ABC
    assert value.clock_seq == 0x1234
    assert value.time > 0


def test_uuid3_and_uuid5_are_deterministic_namespace_name_hashes():
    dns_md5 = uuid.uuid3(uuid.NAMESPACE_DNS, "example.test")
    dns_sha1 = uuid.uuid5(uuid.NAMESPACE_DNS, "example.test")

    assert dns_md5 == uuid.uuid3(uuid.NAMESPACE_DNS, "example.test")
    assert dns_sha1 == uuid.uuid5(uuid.NAMESPACE_DNS, "example.test")
    assert dns_md5.version == 3
    assert dns_sha1.version == 5
    assert dns_md5.variant == dns_sha1.variant == uuid.RFC_4122
    assert dns_md5 != dns_sha1
    assert dns_md5 != uuid.uuid3(uuid.NAMESPACE_URL, "example.test")


def test_uuid_predefined_namespaces_are_fixed_version_one_identifiers():
    namespaces = {
        uuid.NAMESPACE_DNS,
        uuid.NAMESPACE_URL,
        uuid.NAMESPACE_OID,
        uuid.NAMESPACE_X500,
    }

    assert len(namespaces) == 4
    assert all(item.version == 1 for item in namespaces)
    assert all(item.variant == uuid.RFC_4122 for item in namespaces)


def test_uuid4_reads_16_random_bytes_then_forces_version_and_variant(monkeypatch):
    calls = []

    def deterministic_urandom(size):
        calls.append(size)
        return b"\x00" * size

    monkeypatch.setattr(uuid.os, "urandom", deterministic_urandom)

    value = uuid.uuid4()

    assert calls == [16]
    assert value.version == 4
    assert value.variant == uuid.RFC_4122
    assert value.int == (4 << 76) | (0b10 << 62)


def test_getnode_skips_invalid_getters_and_caches_first_valid_node(monkeypatch):
    calls = []

    def invalid_getter():
        calls.append("invalid")
        return 1 << 48

    def valid_getter():
        calls.append("valid")
        return 0x001122334455

    monkeypatch.setattr(uuid, "_node", None)
    monkeypatch.setattr(uuid, "_GETTERS", [invalid_getter, valid_getter])
    monkeypatch.setattr(uuid, "_random_getnode", lambda: 0x010000000001)

    assert uuid.getnode() == 0x001122334455
    assert calls == ["invalid", "valid"]

    # getnode 是进程级缓存；后续调用不会再次枚举网卡或 getters。
    calls.clear()
    assert uuid.getnode() == 0x001122334455
    assert calls == []


def test_random_node_fallback_sets_multicast_bit_and_stays_48_bit():
    node = uuid._random_getnode()

    assert 0 <= node < 1 << 48
    assert node & (1 << 40)
