"""474｜Python 3.10 后期回移的 Expat reparse deferral 与内存放大防护 API。

3.10.14 回移 reparse deferral，避免大而未完成 token 反复解析造成二次复杂度；关闭它会削弱
防护，本例只读取并保持当前值。3.10.20 又加入内存分配阈值和最大放大倍数。跨 3.10 patch
运行必须 ``hasattr``，不能因主版本相同就假定 API 存在，也不能用真实攻击载荷验证安全机制。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.parsers.expat.xmlparser.SetReparseDeferralEnabled-3.10.14
# polyglot-covers: python.xml.parsers.expat.xmlparser.GetReparseDeferralEnabled-3.10.14
# polyglot-covers: python.xml.parsers.expat.reparse-deferral-large-token-protection
# polyglot-covers: python.xml.parsers.expat.reparse-deferral-version-guard
# polyglot-covers: python.xml.parsers.expat.xmlparser.SetAllocTrackerActivationThreshold-3.10.20
# polyglot-covers: python.xml.parsers.expat.xmlparser.SetAllocTrackerMaximumAmplification-3.10.20
# polyglot-covers: python.xml.parsers.expat.alloc-tracker-version-guard
# polyglot-covers: python.xml.parsers.expat-untrusted-xml-warning

from xml.parsers import expat


def test_reparse_deferral_is_capability_checked_and_never_disabled_here():
    parser = expat.ParserCreate()
    getter = getattr(parser, "GetReparseDeferralEnabled", None)
    setter = getattr(parser, "SetReparseDeferralEnabled", None)

    assert (getter is None) == (setter is None)
    if getter is not None:
        enabled = getter()
        setter(enabled)
        assert getter() == enabled

    parser.Parse("<root>small trusted input</root>", True)


def test_allocation_protection_settings_are_guarded_by_patch_level():
    parser = expat.ParserCreate()
    set_threshold = getattr(parser, "SetAllocTrackerActivationThreshold", None)
    set_amplification = getattr(
        parser,
        "SetAllocTrackerMaximumAmplification",
        None,
    )

    assert (set_threshold is None) == (set_amplification is None)
    if set_threshold is not None:
        # 使用文档默认值，不降低防护，也不构造资源耗尽输入。
        assert set_threshold(67_108_864) is None
        assert set_amplification(100.0) is None

    parser.Parse("<root/>", True)
