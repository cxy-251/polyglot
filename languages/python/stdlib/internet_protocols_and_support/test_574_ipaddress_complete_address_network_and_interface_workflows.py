"""学习 ipaddress 的地址、网络、接口、范围聚合及其完整转换工作流。"""

import ipaddress

import pytest


# polyglot-covers: python.stdlib.ipaddress.factory.ip-address
# polyglot-covers: python.stdlib.ipaddress.factory.version-selection
# polyglot-covers: python.stdlib.ipaddress.factory.generic-errors
# polyglot-covers: python.stdlib.ipaddress.ipv4.construction
# polyglot-covers: python.stdlib.ipaddress.ipv4.integer-packed-roundtrip
# polyglot-covers: python.stdlib.ipaddress.ipv4.leading-zero-rejection
# polyglot-covers: python.stdlib.ipaddress.ipv4.range-errors
# polyglot-covers: python.stdlib.ipaddress.ipv6.compressed-exploded
# polyglot-covers: python.stdlib.ipaddress.ipv6.integer-packed-roundtrip
# polyglot-covers: python.stdlib.ipaddress.ipv6.scope-zone
# polyglot-covers: python.stdlib.ipaddress.ipv6.scoped-equality


def test_ip_address_factory_accepts_text_integer_and_packed_bytes() -> None:
    """工厂从值的范围或字节长度判断版本，不要求调用者先选类型。"""
    ipv4 = ipaddress.ip_address("192.0.2.1")
    assert ipv4 == ipaddress.IPv4Address("192.0.2.1")
    assert ipaddress.ip_address(0xC000_0201) == ipv4
    assert ipaddress.ip_address(ipv4.packed) == ipv4

    ipv6 = ipaddress.ip_address("2001:db8::1")
    assert ipv6 == ipaddress.IPv6Address("2001:db8::1")
    assert ipaddress.ip_address(int(ipv6)) == ipv6
    assert ipaddress.ip_address(ipv6.packed) == ipv6


def test_integer_factory_prefers_ipv4_until_the_32_bit_boundary() -> None:
    """无显式版本信息的整数小于 2**32 时按 IPv4 解释。"""
    assert isinstance(ipaddress.ip_address(0), ipaddress.IPv4Address)
    assert ipaddress.ip_address((1 << 32) - 1) == ipaddress.IPv4Address(
        "255.255.255.255"
    )

    first_ipv6_only_integer = ipaddress.ip_address(1 << 32)
    assert isinstance(first_ipv6_only_integer, ipaddress.IPv6Address)
    assert int(first_ipv6_only_integer) == 1 << 32


def test_network_and_interface_factories_select_the_matching_version() -> None:
    """三个顶层工厂分别返回地址、网络和接口对象，不能混作同一抽象。"""
    network4 = ipaddress.ip_network("192.0.2.0/24")
    network6 = ipaddress.ip_network("2001:db8::/32")
    interface4 = ipaddress.ip_interface("192.0.2.7/24")
    interface6 = ipaddress.ip_interface("2001:db8::7/64")

    assert isinstance(network4, ipaddress.IPv4Network)
    assert isinstance(network6, ipaddress.IPv6Network)
    assert isinstance(interface4, ipaddress.IPv4Interface)
    assert isinstance(interface6, ipaddress.IPv6Interface)


def test_generic_factories_have_less_specific_errors_than_version_types() -> None:
    """通用工厂尝试多个版本，诊断输入时可改用版本专用构造器。"""
    with pytest.raises(ValueError):
        ipaddress.ip_address("999.0.0.1")
    with pytest.raises(ipaddress.AddressValueError):
        ipaddress.IPv4Address("999.0.0.1")
    with pytest.raises(ValueError):
        ipaddress.ip_network("not-a-network")
    with pytest.raises(ValueError):
        ipaddress.ip_interface("not-an-interface")


def test_ipv4_text_integer_and_packed_forms_are_equivalent() -> None:
    """IPv4 地址本质上是 32 位整数；packed 使用网络字节序。"""
    from_text = ipaddress.IPv4Address("192.0.2.1")
    from_integer = ipaddress.IPv4Address(0xC000_0201)
    from_packed = ipaddress.IPv4Address(b"\xc0\x00\x02\x01")

    assert from_text == from_integer == from_packed
    assert int(from_text) == 0xC000_0201
    assert from_text.packed == b"\xc0\x00\x02\x01"
    assert str(from_text) == "192.0.2.1"
    assert repr(from_text) == "IPv4Address('192.0.2.1')"
    assert from_text.version == 4
    assert from_text.max_prefixlen == 32
    assert from_text.compressed == from_text.exploded == str(from_text)


def test_ipv4_rejects_leading_zero_octets_and_out_of_range_inputs() -> None:
    """3.10 不把前导零当宽度或八进制标记，整数和字节长度也必须匹配。"""
    for text in ("192.168.001.1", "010.0.0.1"):
        with pytest.raises(ipaddress.AddressValueError):
            ipaddress.IPv4Address(text)

    for value in (-1, 1 << 32, b"\xc0\x00\x02"):
        with pytest.raises(ipaddress.AddressValueError):
            ipaddress.IPv4Address(value)


def test_ipv6_compressed_and_exploded_forms_preserve_one_value() -> None:
    """双冒号只影响展示；exploded 总是补齐八组四位十六进制数。"""
    address = ipaddress.IPv6Address("2001:0db8:0:0:0:0:0:1")

    assert str(address) == "2001:db8::1"
    assert address.compressed == "2001:db8::1"
    assert address.exploded == "2001:0db8:0000:0000:0000:0000:0000:0001"
    assert address.version == 6
    assert address.max_prefixlen == 128


def test_ipv6_integer_and_packed_forms_round_trip() -> None:
    """IPv6 使用 128 位大端整数，十六字节 packed 适合二进制协议字段。"""
    address = ipaddress.IPv6Address("2001:db8::dead:beef")

    assert len(address.packed) == 16
    assert ipaddress.IPv6Address(address.packed) == address
    assert ipaddress.IPv6Address(int(address)) == address


def test_ipv6_scope_zone_affects_identity_but_not_packed_bits() -> None:
    """链路本地地址的作用域区选择接口，但不属于 128 位地址字段。"""
    unscoped = ipaddress.IPv6Address("fe80::1234")
    ethernet = ipaddress.IPv6Address("fe80::1234%eth0")
    wifi = ipaddress.IPv6Address("fe80::1234%wlan0")

    assert ethernet.scope_id == "eth0"
    assert str(ethernet) == "fe80::1234%eth0"
    assert ethernet != unscoped
    assert ethernet != wifi
    assert ethernet.packed == unscoped.packed
    assert int(ethernet) == int(unscoped)

    restored = ipaddress.IPv6Address(int(ethernet))
    assert restored == unscoped
    assert restored.scope_id is None


def test_ipv6_scope_zone_must_be_one_nonempty_component() -> None:
    """区标识不能为空，也不能再含百分号。"""
    for text in ("fe80::1%", "fe80::1%eth%0"):
        with pytest.raises(ipaddress.AddressValueError):
            ipaddress.IPv6Address(text)

# 地址属性、格式协议、比较算术与 IPv6 过渡地址。


# polyglot-covers: python.stdlib.ipaddress.address.classification-flags
# polyglot-covers: python.stdlib.ipaddress.address.reverse-pointer
# polyglot-covers: python.stdlib.ipaddress.address.format-protocol
# polyglot-covers: python.stdlib.ipaddress.address.hashing
# polyglot-covers: python.stdlib.ipaddress.address.ordering
# polyglot-covers: python.stdlib.ipaddress.address.cross-version-comparison
# polyglot-covers: python.stdlib.ipaddress.address.integer-arithmetic
# polyglot-covers: python.stdlib.ipaddress.address.arithmetic-overflow
# polyglot-covers: python.stdlib.ipaddress.ipv6.ipv4-mapped
# polyglot-covers: python.stdlib.ipaddress.ipv6.sixtofour
# polyglot-covers: python.stdlib.ipaddress.ipv6.teredo


def test_special_ranges_expose_boolean_classification_flags() -> None:
    """分类属性封装地址注册表判断；这里选择跨补丁版本稳定的范围。"""
    assert ipaddress.IPv4Address("127.0.0.1").is_loopback
    assert ipaddress.IPv4Address("169.254.10.20").is_link_local
    assert ipaddress.IPv4Address("224.0.0.1").is_multicast
    assert ipaddress.IPv4Address("0.0.0.0").is_unspecified
    assert ipaddress.IPv6Address("::1").is_loopback
    assert ipaddress.IPv6Address("fe80::1").is_link_local
    assert ipaddress.IPv6Address("ff02::1").is_multicast
    assert ipaddress.IPv6Address("::").is_unspecified


def test_reverse_pointer_builds_a_reverse_dns_query_name_only() -> None:
    """该属性不会访问 DNS，也不保证对应 PTR 记录存在。"""
    ipv4 = ipaddress.IPv4Address("192.0.2.1")
    ipv6 = ipaddress.IPv6Address("2001:db8::1")

    assert ipv4.reverse_pointer == "1.2.0.192.in-addr.arpa"
    assert ipv6.reverse_pointer.endswith(".ip6.arpa")
    reversed_nibbles = ipv6.reverse_pointer.removesuffix(".ip6.arpa").split(".")
    assert reversed_nibbles[:4] == ["1", "0", "0", "0"]
    assert len(reversed_nibbles) == 32


def test_address_format_supports_binary_hex_prefixes_and_separators() -> None:
    """地址实现 __format__，可直接生成固定宽度的位级协议表示。"""
    ipv4 = ipaddress.IPv4Address("192.0.2.1")
    ipv6 = ipaddress.IPv6Address("2001:db8::1")

    assert format(ipv4, "s") == "192.0.2.1"
    assert format(ipv4, "b") == "11000000000000000000001000000001"
    grouped_binary = "0b1100_0000_0000_0000_0000_0010_0000_0001"
    assert format(ipv4, "#_b") == grouped_binary
    assert format(ipv4, "n") == format(ipv4, "b")
    assert format(ipv6, "X") == "20010DB8000000000000000000000001"
    assert format(ipv6, "#x").startswith("0x20010db8")
    assert format(ipv6, "n") == format(ipv6, "x")


def test_equal_address_objects_share_hashes_and_mapping_keys() -> None:
    """不可变地址按数值和版本哈希，不按输入文本哈希。"""
    first = ipaddress.IPv6Address("2001:0db8::1")
    second = ipaddress.IPv6Address("2001:db8:0:0:0:0:0:1")
    labels = {first: "documentation-host"}

    assert first == second
    assert hash(first) == hash(second)
    assert labels[second] == "documentation-host"


def test_one_address_family_orders_by_numeric_value() -> None:
    """同版本地址可排序，十进制字符串的字典序不能替代地址数值顺序。"""
    addresses = [
        ipaddress.IPv4Address("192.0.2.10"),
        ipaddress.IPv4Address("192.0.2.2"),
        ipaddress.IPv4Address("192.0.2.1"),
    ]

    assert sorted(addresses) == [
        ipaddress.IPv4Address("192.0.2.1"),
        ipaddress.IPv4Address("192.0.2.2"),
        ipaddress.IPv4Address("192.0.2.10"),
    ]


def test_ipv4_and_ipv6_have_no_implicit_ordering() -> None:
    """即使整数值相同，不同地址族也必须由调用者显式提供排序规则。"""
    ipv4 = ipaddress.IPv4Address("0.0.0.1")
    ipv6 = ipaddress.IPv6Address("::1")

    assert ipv4 != ipv6
    with pytest.raises(TypeError):
        _ = ipv4 < ipv6


def test_integer_arithmetic_moves_by_whole_addresses() -> None:
    """加减整数不修改对象，并保持原地址族。"""
    ipv4 = ipaddress.IPv4Address("192.0.2.1")
    ipv6 = ipaddress.IPv6Address("2001:db8::10")

    assert ipv4 + 5 == ipaddress.IPv4Address("192.0.2.6")
    assert ipv4 - 1 == ipaddress.IPv4Address("192.0.2.0")
    assert ipv6 + 16 == ipaddress.IPv6Address("2001:db8::20")
    assert ipv6 - 1 == ipaddress.IPv6Address("2001:db8::f")


def test_address_arithmetic_rejects_overflow_and_noninteger_steps() -> None:
    """算术不会环绕，越过地址族边界会得到 AddressValueError。"""
    with pytest.raises(ipaddress.AddressValueError):
        _ = ipaddress.IPv4Address("255.255.255.255") + 1
    with pytest.raises(ipaddress.AddressValueError):
        _ = ipaddress.IPv6Address("::") - 1
    with pytest.raises(TypeError):
        _ = ipaddress.IPv4Address("192.0.2.1") + 1.5


def test_ipv4_mapped_property_requires_the_standard_prefix() -> None:
    """只有 ::ffff:0:0/96 表示 IPv4 映射地址，不能仅凭尾部数字猜测。"""
    mapped = ipaddress.IPv6Address("::ffff:192.0.2.128")
    ordinary = ipaddress.IPv6Address("2001:db8::192.0.2.128")

    assert mapped.ipv4_mapped == ipaddress.IPv4Address("192.0.2.128")
    assert ordinary.ipv4_mapped is None


def test_sixtofour_and_teredo_properties_decode_transition_fields() -> None:
    """属性只解析匹配前缀的位字段，不执行隧道连接或验证服务器。"""
    sixtofour = ipaddress.IPv6Address("2002:c000:0204::")
    teredo = ipaddress.IPv6Address("2001:0000:4136:e378:8000:63bf:3fff:fdd2")

    assert sixtofour.sixtofour == ipaddress.IPv4Address("192.0.2.4")
    assert ipaddress.IPv6Address("2001:db8::1").sixtofour is None
    assert teredo.teredo == (
        ipaddress.IPv4Address("65.54.227.120"),
        ipaddress.IPv4Address("192.0.2.45"),
    )
    assert ipaddress.IPv6Address("2001:db8::1").teredo is None

# 网络构造、掩码、边界属性、文本形式与对象身份。


# polyglot-covers: python.stdlib.ipaddress.network.construction
# polyglot-covers: python.stdlib.ipaddress.network.strict-host-bits
# polyglot-covers: python.stdlib.ipaddress.network.netmask-hostmask
# polyglot-covers: python.stdlib.ipaddress.network.version-specific-errors
# polyglot-covers: python.stdlib.ipaddress.network.derived-addresses
# polyglot-covers: python.stdlib.ipaddress.network.text-forms
# polyglot-covers: python.stdlib.ipaddress.network.hash-order
# polyglot-covers: python.stdlib.ipaddress.network.classification-flags
# polyglot-covers: python.stdlib.ipaddress.network.compare-networks


def test_network_accepts_prefix_text_integer_bytes_and_tuple() -> None:
    """无前缀整数或字节表示单主机网络；二元组把地址与掩码分开。"""
    expected_host = ipaddress.IPv4Network("192.0.2.1/32")

    assert ipaddress.IPv4Network(0xC000_0201) == expected_host
    assert ipaddress.IPv4Network(b"\xc0\x00\x02\x01") == expected_host
    assert ipaddress.IPv4Network(
        ("192.0.2.0", "255.255.255.0")
    ) == ipaddress.IPv4Network("192.0.2.0/24")
    assert ipaddress.IPv6Network("2001:db8::/32").prefixlen == 32


def test_strict_mode_rejects_host_bits_and_non_strict_masks_them() -> None:
    """默认严格模式发现误写；strict=False 才明确表示向下取网络地址。"""
    with pytest.raises(ValueError, match="host bits set"):
        ipaddress.ip_network("192.0.2.129/24")

    masked = ipaddress.ip_network("192.0.2.129/24", strict=False)
    assert masked == ipaddress.IPv4Network("192.0.2.0/24")


def test_ipv4_distinguishes_netmask_and_hostmask() -> None:
    """首段非零按网络掩码解释，首段为零通常按通配符式 hostmask 解释。"""
    from_netmask = ipaddress.IPv4Network("192.0.2.0/255.255.255.0")
    from_hostmask = ipaddress.IPv4Network("192.0.2.0/0.0.0.255")

    assert from_netmask == from_hostmask == ipaddress.IPv4Network("192.0.2.0/24")
    # 全零是特例：表示 /0 网络掩码，不是 /32 的 hostmask。
    assert ipaddress.IPv4Network("0.0.0.0/0.0.0.0").prefixlen == 0


def test_ipv6_uses_prefix_lengths_instead_of_expanded_mask_text() -> None:
    """IPv6 构造器不接受完整十六进制掩码，应使用 /64 形式。"""
    with pytest.raises(ValueError):
        ipaddress.IPv6Network("2001:db8::/ffff:ffff:ffff:ffff::")


def test_specific_network_constructor_distinguishes_address_and_mask_errors() -> None:
    """专用构造器给配置校验提供比通用工厂更精确的异常类型。"""
    with pytest.raises(ipaddress.AddressValueError):
        ipaddress.IPv4Network("999.0.0.0/24")
    with pytest.raises(ipaddress.NetmaskValueError):
        ipaddress.IPv4Network("192.0.2.0/33")


def test_ipv4_network_derives_boundaries_masks_prefix_and_size() -> None:
    """网络对象提供完整地址范围语义，不只是保存一段斜杠文本。"""
    network = ipaddress.IPv4Network("192.0.2.0/26")

    assert network.network_address == ipaddress.IPv4Address("192.0.2.0")
    assert network.broadcast_address == ipaddress.IPv4Address("192.0.2.63")
    assert network.netmask == ipaddress.IPv4Address("255.255.255.192")
    assert network.hostmask == ipaddress.IPv4Address("0.0.0.63")
    assert network.prefixlen == 26
    assert network.num_addresses == 64
    assert network.version == 4
    assert network.max_prefixlen == 32


def test_network_text_properties_offer_three_mask_views() -> None:
    """with_* 形式表达同一网络，便于输出给使用不同掩码约定的工具。"""
    network = ipaddress.IPv4Network("192.0.2.0/26")

    assert str(network) == "192.0.2.0/26"
    assert repr(network) == "IPv4Network('192.0.2.0/26')"
    assert network.with_prefixlen == "192.0.2.0/26"
    assert network.with_netmask == "192.0.2.0/255.255.255.192"
    assert network.with_hostmask == "192.0.2.0/0.0.0.63"
    assert network.compressed == network.with_prefixlen
    assert network.exploded == network.with_prefixlen


def test_network_hash_order_and_legacy_three_way_comparison() -> None:
    """排序先看网络地址再看掩码；同一地址处较宽的网络排在前面。"""
    wide = ipaddress.IPv4Network("192.0.2.0/24")
    narrow = ipaddress.IPv4Network("192.0.2.0/25")
    later = ipaddress.IPv4Network("198.51.100.0/24")
    same_wide = ipaddress.IPv4Network((0xC000_0200, 24))

    assert wide == same_wide
    assert hash(wide) == hash(same_wide)
    assert sorted([later, narrow, wide]) == [wide, narrow, later]
    assert wide.compare_networks(narrow) == -1
    assert wide.compare_networks(same_wide) == 0


def test_network_flags_require_the_whole_range_to_match() -> None:
    """网络分类同时考虑网络地址和广播地址，不只抽查第一个地址。"""
    assert ipaddress.IPv4Network("127.0.0.0/8").is_loopback
    assert ipaddress.IPv4Network("224.0.0.0/4").is_multicast
    assert ipaddress.IPv6Network("ff00::/8").is_multicast

# 网络迭代、主机规则、索引、拆分聚合与包含关系。


# polyglot-covers: python.stdlib.ipaddress.network.iteration
# polyglot-covers: python.stdlib.ipaddress.network.hosts
# polyglot-covers: python.stdlib.ipaddress.network.point-to-point-hosts
# polyglot-covers: python.stdlib.ipaddress.network.indexing
# polyglot-covers: python.stdlib.ipaddress.network.membership
# polyglot-covers: python.stdlib.ipaddress.network.subnets
# polyglot-covers: python.stdlib.ipaddress.network.supernet
# polyglot-covers: python.stdlib.ipaddress.network.subnet-supernet-relations
# polyglot-covers: python.stdlib.ipaddress.network.overlaps
# polyglot-covers: python.stdlib.ipaddress.network.prefix-errors


def test_iteration_includes_boundaries_while_hosts_normally_omits_them() -> None:
    """直接迭代表示整个地址空间；hosts 才应用传统可分配主机规则。"""
    network = ipaddress.IPv4Network("192.0.2.0/30")

    assert list(network) == [
        ipaddress.IPv4Address("192.0.2.0"),
        ipaddress.IPv4Address("192.0.2.1"),
        ipaddress.IPv4Address("192.0.2.2"),
        ipaddress.IPv4Address("192.0.2.3"),
    ]
    assert list(network.hosts()) == [
        ipaddress.IPv4Address("192.0.2.1"),
        ipaddress.IPv4Address("192.0.2.2"),
    ]


def test_point_to_point_and_single_host_prefixes_have_special_host_rules() -> None:
    """RFC 3021 的 /31 两端都可用；/32 以及 IPv6 对应前缀也返回端点。"""
    ipv4_pair = ipaddress.IPv4Network("192.0.2.0/31")
    ipv4_single = ipaddress.IPv4Network("192.0.2.9/32")
    ipv6_pair = ipaddress.IPv6Network("2001:db8::/127")
    ipv6_single = ipaddress.IPv6Network("2001:db8::9/128")

    assert list(ipv4_pair.hosts()) == list(ipv4_pair)
    assert list(ipv4_single.hosts()) == [ipaddress.IPv4Address("192.0.2.9")]
    assert list(ipv6_pair.hosts()) == list(ipv6_pair)
    assert list(ipv6_single.hosts()) == [ipaddress.IPv6Address("2001:db8::9")]


def test_network_indexing_supports_negative_offsets_and_checks_bounds() -> None:
    """索引从网络地址开始，负索引从广播地址倒数，越界不会进入相邻网络。"""
    network = ipaddress.IPv4Network("198.51.100.0/30")

    assert network[0] == ipaddress.IPv4Address("198.51.100.0")
    assert network[2] == ipaddress.IPv4Address("198.51.100.2")
    assert network[-1] == ipaddress.IPv4Address("198.51.100.3")
    with pytest.raises(IndexError):
        _ = network[4]
    with pytest.raises(IndexError):
        _ = network[-5]


def test_membership_accepts_addresses_and_rejects_other_families() -> None:
    """文本应先显式解析；不同地址族不会被误判为成员。"""
    network = ipaddress.IPv4Network("192.0.2.0/24")

    assert ipaddress.ip_address("192.0.2.99") in network
    assert ipaddress.ip_address("198.51.100.1") not in network
    assert ipaddress.IPv6Address("::1") not in network


def test_subnets_split_lazily_by_difference_or_new_prefix() -> None:
    """subnets 返回迭代器，默认多一位，也可直接指定目标前缀。"""
    network = ipaddress.IPv4Network("192.0.2.0/24")

    assert list(network.subnets()) == [
        ipaddress.IPv4Network("192.0.2.0/25"),
        ipaddress.IPv4Network("192.0.2.128/25"),
    ]
    assert list(network.subnets(new_prefix=26)) == [
        ipaddress.IPv4Network("192.0.2.0/26"),
        ipaddress.IPv4Network("192.0.2.64/26"),
        ipaddress.IPv4Network("192.0.2.128/26"),
        ipaddress.IPv4Network("192.0.2.192/26"),
    ]


def test_supernet_moves_wider_and_root_is_its_own_supernet() -> None:
    """默认向上一级；根网络没有更宽父级，因此返回自身。"""
    network = ipaddress.IPv4Network("192.0.2.0/24")
    root = ipaddress.IPv4Network("0.0.0.0/0")

    assert network.supernet() == ipaddress.IPv4Network("192.0.2.0/23")
    assert network.supernet(prefixlen_diff=2) == ipaddress.IPv4Network("192.0.0.0/22")
    assert network.supernet(new_prefix=16) == ipaddress.IPv4Network("192.0.0.0/16")
    assert root.supernet() is root


def test_subnet_supernet_and_overlap_relations_are_distinct() -> None:
    """包含关系有方向，overlaps 是对称交集判断，相等网络也互为包含。"""
    parent = ipaddress.IPv4Network("192.0.2.0/24")
    child = ipaddress.IPv4Network("192.0.2.64/26")
    touching = ipaddress.IPv4Network("192.0.3.0/24")

    assert child.subnet_of(parent)
    assert parent.supernet_of(child)
    assert parent.subnet_of(parent)
    assert parent.supernet_of(parent)
    assert parent.overlaps(child)
    assert child.overlaps(parent)
    assert not parent.overlaps(touching)


def test_invalid_prefix_directions_and_mixed_version_ordering_raise() -> None:
    """拆分只能加长前缀，聚合只能缩短；IPv4 与 IPv6 网络也不能直接排序。"""
    network = ipaddress.IPv4Network("192.0.2.0/24")

    with pytest.raises(ValueError):
        list(network.subnets(new_prefix=23))
    with pytest.raises(ValueError):
        network.supernet(new_prefix=25)
    with pytest.raises(ValueError):
        list(network.subnets(prefixlen_diff=2, new_prefix=26))
    with pytest.raises(TypeError):
        _ = network < ipaddress.IPv6Network("2001:db8::/32")

# 网络差集分解，以及同时保留主机和网络视图的接口对象。


# polyglot-covers: python.stdlib.ipaddress.network.address-exclude
# polyglot-covers: python.stdlib.ipaddress.network.address-exclude-order
# polyglot-covers: python.stdlib.ipaddress.network.address-exclude-errors
# polyglot-covers: python.stdlib.ipaddress.interface.construction
# polyglot-covers: python.stdlib.ipaddress.interface.ip-network-views
# polyglot-covers: python.stdlib.ipaddress.interface.text-forms
# polyglot-covers: python.stdlib.ipaddress.interface.equality-hashing
# polyglot-covers: python.stdlib.ipaddress.interface.factory


def test_address_exclude_returns_ordered_cidr_blocks_for_the_difference() -> None:
    """差集不是逐地址列表，而是从大块到边界小块的一组最简 CIDR 网络。"""
    container = ipaddress.IPv4Network("192.0.2.0/28")
    excluded = ipaddress.IPv4Network("192.0.2.1/32")

    remainder = list(container.address_exclude(excluded))
    assert remainder == [
        ipaddress.IPv4Network("192.0.2.8/29"),
        ipaddress.IPv4Network("192.0.2.4/30"),
        ipaddress.IPv4Network("192.0.2.2/31"),
        ipaddress.IPv4Network("192.0.2.0/32"),
    ]
    assert sum(network.num_addresses for network in remainder) == 15
    omitted = ipaddress.IPv4Address("192.0.2.1")
    assert all(omitted not in network for network in remainder)


def test_excluding_the_same_network_returns_no_blocks() -> None:
    """集合减去自身为空，这是正常边界而不是异常。"""
    network = ipaddress.IPv6Network("2001:db8::/126")
    assert list(network.address_exclude(network)) == []


def test_address_exclude_requires_a_contained_same_version_network() -> None:
    """不相交网络和值域不同的网络分别触发 ValueError 与 TypeError。"""
    network = ipaddress.IPv4Network("192.0.2.0/24")

    with pytest.raises(ValueError):
        list(network.address_exclude(ipaddress.IPv4Network("198.51.100.0/24")))
    with pytest.raises(TypeError):
        list(network.address_exclude(ipaddress.IPv6Network("2001:db8::/32")))


def test_interface_preserves_host_bits_while_network_masks_them() -> None:
    """接口左侧仍是主机，network 视图才向下取网络地址。"""
    interface = ipaddress.IPv4Interface("192.0.2.129/24")

    assert interface.ip == ipaddress.IPv4Address("192.0.2.129")
    assert interface.network == ipaddress.IPv4Network("192.0.2.0/24")
    assert isinstance(interface, ipaddress.IPv4Address)
    assert int(interface) == int(interface.ip)


def test_interface_text_forms_keep_the_host_and_change_mask_notation() -> None:
    """与网络对象不同，接口三种文本左侧都保留具体主机地址。"""
    interface = ipaddress.IPv4Interface("192.0.2.129/26")

    assert str(interface) == "192.0.2.129/26"
    assert repr(interface) == "IPv4Interface('192.0.2.129/26')"
    assert interface.with_prefixlen == "192.0.2.129/26"
    assert interface.with_netmask == "192.0.2.129/255.255.255.192"
    assert interface.with_hostmask == "192.0.2.129/0.0.0.63"


def test_interface_identity_includes_both_ip_and_network() -> None:
    """同一 IP 配不同前缀代表不同接口，接口也不等于裸地址对象。"""
    first = ipaddress.IPv4Interface("192.0.2.129/24")
    same = ipaddress.IPv4Interface((0xC000_0281, 24))
    different_network = ipaddress.IPv4Interface("192.0.2.129/25")

    assert first == same
    assert hash(first) == hash(same)
    assert first != different_network
    assert first != first.ip


def test_interface_factory_selects_version_and_defaults_to_one_host() -> None:
    """省略前缀时使用地址族最大前缀，显式前缀仍保留主机位。"""
    ipv4 = ipaddress.ip_interface("192.0.2.9")
    ipv6 = ipaddress.ip_interface("2001:db8::9/64")

    assert ipv4 == ipaddress.IPv4Interface("192.0.2.9/32")
    assert ipv4.network == ipaddress.IPv4Network("192.0.2.9/32")
    assert isinstance(ipv6, ipaddress.IPv6Interface)
    assert ipv6.ip == ipaddress.IPv6Address("2001:db8::9")
    assert ipv6.network == ipaddress.IPv6Network("2001:db8::/64")

# 范围聚合、整数打包与混合对象排序辅助函数。


# polyglot-covers: python.stdlib.ipaddress.v4-v6-int-to-packed
# polyglot-covers: python.stdlib.ipaddress.summarize-address-range
# polyglot-covers: python.stdlib.ipaddress.collapse-addresses
# polyglot-covers: python.stdlib.ipaddress.get-mixed-type-key


def test_integer_packing_produces_fixed_width_network_order_bytes() -> None:
    """打包函数适合直接填协议字段，并严格检查地址族位宽。"""
    assert ipaddress.v4_int_to_packed(0xC000_0201) == b"\xc0\x00\x02\x01"
    assert ipaddress.v6_int_to_packed(1) == b"\x00" * 15 + b"\x01"

    with pytest.raises(ValueError):
        ipaddress.v4_int_to_packed(-1)
    with pytest.raises(ValueError):
        ipaddress.v6_int_to_packed(1 << 128)


def test_summarize_address_range_builds_a_minimal_cidr_cover() -> None:
    """闭区间端点被分解成不重叠、按地址排序的最少 CIDR 网络。"""
    first = ipaddress.IPv4Address("192.0.2.1")
    last = ipaddress.IPv4Address("192.0.2.6")

    assert list(ipaddress.summarize_address_range(first, last)) == [
        ipaddress.IPv4Network("192.0.2.1/32"),
        ipaddress.IPv4Network("192.0.2.2/31"),
        ipaddress.IPv4Network("192.0.2.4/31"),
        ipaddress.IPv4Network("192.0.2.6/32"),
    ]
    with pytest.raises(ValueError):
        list(ipaddress.summarize_address_range(last, first))
    with pytest.raises(TypeError):
        list(ipaddress.summarize_address_range(first, ipaddress.IPv6Address("::1")))


def test_collapse_addresses_merges_adjacent_and_overlapping_inputs() -> None:
    """地址先视为最大前缀网络，再与输入网络一起递归合并兄弟块。"""
    networks = [
        ipaddress.IPv4Network("192.0.2.0/25"),
        ipaddress.IPv4Network("192.0.2.128/25"),
        ipaddress.IPv4Network("192.0.2.64/26"),
    ]
    addresses = [
        ipaddress.IPv4Address("198.51.100.0"),
        ipaddress.IPv4Address("198.51.100.1"),
    ]

    assert list(ipaddress.collapse_addresses(networks)) == [
        ipaddress.IPv4Network("192.0.2.0/24")
    ]
    assert list(ipaddress.collapse_addresses(addresses)) == [
        ipaddress.IPv4Network("198.51.100.0/31")
    ]

    mixed_versions = [
        ipaddress.IPv4Address("192.0.2.1"),
        ipaddress.IPv6Address("::1"),
    ]
    with pytest.raises(TypeError):
        list(ipaddress.collapse_addresses(mixed_versions))


def test_mixed_type_key_explicitly_sorts_addresses_and_networks() -> None:
    """两类对象默认不可比较，官方键把它们映射到稳定排序元组。"""
    network = ipaddress.IPv4Network("192.0.2.0/24")
    address = ipaddress.IPv4Address("192.0.2.1")

    with pytest.raises(TypeError):
        sorted([address, network])

    assert sorted([address, network], key=ipaddress.get_mixed_type_key) == [
        network,
        address,
    ]
