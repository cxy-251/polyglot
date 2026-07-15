"""462｜SAX Attributes/AttributesNS 的 DOM 风格查询与 Python mapping 协议。

非 namespace 属性以字符串键保存；namespace 版本用 ``(URI, localName)`` 键并另存源 qname。
两者都实现 copy/get/contains/items/keys/values，以及 getLength/getNames/getType/getValue。属性对象
可能被 parser 复用，因此需要长期保存时复制普通 dict，而不是持有回调参数本身。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.sax.xmlreader.AttributesImpl
# polyglot-covers: python.xml.sax.xmlreader.Attributes.getLength
# polyglot-covers: python.xml.sax.xmlreader.Attributes.getNames
# polyglot-covers: python.xml.sax.xmlreader.Attributes.getType
# polyglot-covers: python.xml.sax.xmlreader.Attributes.getValue
# polyglot-covers: python.xml.sax.xmlreader.Attributes-mapping-protocol
# polyglot-covers: python.xml.sax.xmlreader.AttributesNSImpl
# polyglot-covers: python.xml.sax.xmlreader.AttributesNS.getValueByQName
# polyglot-covers: python.xml.sax.xmlreader.AttributesNS.getNameByQName
# polyglot-covers: python.xml.sax.xmlreader.AttributesNS.getQNameByName
# polyglot-covers: python.xml.sax.xmlreader.AttributesNS.getQNames

from xml.sax import xmlreader


def test_attributes_impl_supports_sax_queries_and_mapping_operations():
    attrs = xmlreader.AttributesImpl({"id": "one", "empty": ""})

    assert attrs.getLength() == len(attrs) == 2
    assert set(attrs.getNames()) == {"id", "empty"}
    assert attrs.getType("id") == "CDATA"
    assert attrs.getValue("id") == attrs["id"] == "one"
    assert "empty" in attrs
    assert attrs.get("missing", "fallback") == "fallback"
    assert attrs.copy() == {"id": "one", "empty": ""}
    assert dict(attrs.items()) == {"id": "one", "empty": ""}


def test_attributes_ns_maps_expanded_names_to_original_qualified_names():
    state = ("urn:state", "mode")
    plain = (None, "plain")
    attrs = xmlreader.AttributesNSImpl(
        {state: "ready", plain: "value"},
        {state: "s:mode", plain: "plain"},
    )

    assert attrs.getValue(state) == "ready"
    assert attrs.getValueByQName("s:mode") == "ready"
    assert attrs.getNameByQName("s:mode") == state
    assert attrs.getQNameByName(state) == "s:mode"
    assert set(attrs.getQNames()) == {"s:mode", "plain"}
    assert set(attrs.getNames()) == {state, plain}
