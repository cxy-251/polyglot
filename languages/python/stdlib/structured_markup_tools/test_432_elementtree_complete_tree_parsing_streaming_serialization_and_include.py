"""432｜ElementTree 从字符串、片段列表、文件解析，以及 XMLID/dump/iselement。

fromstring/XML 返回根 Element，parse 返回持有根的 ElementTree；ElementTree.parse 会替换当前
tree 的根并返回该 Element。fromstringlist 适合已经分块但完整的 XML。XMLID 额外收集普通
``id`` 属性。iselement 只检查 Element 协议而非严格类型，dump 只用于调试输出。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.etree.ElementTree.fromstring
# polyglot-covers: python.xml.etree.ElementTree.XML
# polyglot-covers: python.xml.etree.ElementTree.fromstringlist
# polyglot-covers: python.xml.etree.ElementTree.parse
# polyglot-covers: python.xml.etree.ElementTree.ElementTree
# polyglot-covers: python.xml.etree.ElementTree.ElementTree.parse
# polyglot-covers: python.xml.etree.ElementTree.ElementTree.getroot
# polyglot-covers: python.xml.etree.ElementTree.XMLID
# polyglot-covers: python.xml.etree.ElementTree.iselement
# polyglot-covers: python.xml.etree.ElementTree.iselement-protocol-not-type-check
# polyglot-covers: python.xml.etree.ElementTree.dump



from xml.etree import ElementTree as ET
from copy import copy
import pytest
import io
from xml.etree import ElementInclude

XML_TEXT_432 = "<catalog><item id='a'>Alpha</item><item id='b'>Beta</item></catalog>"


def test_string_and_fragment_parsers_return_the_document_element():
    from_string = ET.fromstring(XML_TEXT_432)
    from_alias = ET.XML(XML_TEXT_432.encode())
    from_fragments = ET.fromstringlist(
        ["<catalog>", "<item id='a'>Alpha</item>", "</catalog>"]
    )

    assert from_string.tag == from_alias.tag == from_fragments.tag == "catalog"
    assert [item.text for item in from_string] == ["Alpha", "Beta"]
    assert from_fragments[0].attrib == {"id": "a"}


def test_module_and_tree_parse_have_different_return_shapes(tmp_path):
    path = tmp_path / "catalog.xml"
    path.write_text(XML_TEXT_432, encoding="utf-8")

    parsed_tree = ET.parse(path)
    reusable_tree = ET.ElementTree()
    returned_root = reusable_tree.parse(path)

    assert isinstance(parsed_tree, ET.ElementTree)
    assert parsed_tree.getroot().tag == "catalog"
    assert returned_root is reusable_tree.getroot()
    assert returned_root[1].text == "Beta"


def test_xmlid_collects_id_attributes_while_iselement_is_a_protocol_check():
    root, by_id = ET.XMLID(XML_TEXT_432)
    assert by_id == {"a": root[0], "b": root[1]}

    class ElementLike:
        tag = "duck"

    assert ET.iselement(root) is True
    assert ET.iselement(ElementLike()) is True
    assert ET.iselement(object()) is False


def test_dump_writes_a_debug_serialization_to_standard_output(capsys):
    root = ET.fromstring("<root><child /></root>")
    assert ET.dump(root) is None
    assert capsys.readouterr().out == "<root><child /></root>\n"


# 433｜Element/SubElement、Comment、ProcessingInstruction、QName 与 text/tail。
#
# Element 是 tag、可变 attrib 和有序 children 的节点；SubElement 创建并立即 append，makeelement
# 只创建同类节点而不挂树。text 位于开始/结束标签之间，tail 位于本元素结束标签之后，二者不能
# 互换。Comment/PI 使用特殊 tag 哨兵，QName 用 ``{uri}local`` 形式表达扩展名。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.etree.ElementTree.Element
# polyglot-covers: python.xml.etree.ElementTree.Element.tag
# polyglot-covers: python.xml.etree.ElementTree.Element.attrib
# polyglot-covers: python.xml.etree.ElementTree.SubElement
# polyglot-covers: python.xml.etree.ElementTree.Element.makeelement
# polyglot-covers: python.xml.etree.ElementTree.Element.text
# polyglot-covers: python.xml.etree.ElementTree.Element.tail
# polyglot-covers: python.xml.etree.ElementTree.Comment
# polyglot-covers: python.xml.etree.ElementTree.ProcessingInstruction
# polyglot-covers: python.xml.etree.ElementTree.QName
# polyglot-covers: python.xml.etree.ElementTree-expanded-name-syntax
# polyglot-covers: python.xml.etree.ElementTree.attribute-insertion-order



def test_element_and_subelement_build_an_ordered_tree_with_text_and_tail():
    root = ET.Element("root", {"first": "1"}, second="2")
    first = ET.SubElement(root, "child", role="first")
    first.text = "inside"
    first.tail = "after-child"
    second = ET.SubElement(root, "child", role="second")

    assert root.tag == "root"
    assert list(root.attrib.items()) == [("first", "1"), ("second", "2")]
    assert list(root) == [first, second]
    assert first.text == "inside"
    assert first.tail == "after-child"


def test_makeelement_returns_a_compatible_unattached_node():
    root = ET.Element("root")
    child = root.makeelement("child", {"id": "one"})

    assert ET.iselement(child)
    assert child.tag == "child"
    assert child.attrib == {"id": "one"}
    assert len(root) == 0


def test_comment_processing_instruction_and_qname_serialize_as_markup_nodes():
    root = ET.Element("root")
    root.append(ET.Comment("note"))
    root.append(ET.ProcessingInstruction("build", "mode='fast'"))
    namespaced = ET.SubElement(root, ET.QName("urn:demo", "item"))
    namespaced.set("kind", ET.QName("urn:demo", "special"))

    assert str(ET.QName("urn:demo", "item")) == "{urn:demo}item"
    wire = ET.tostring(root, encoding="unicode")
    assert "<!--note-->" in wire
    assert "<?build mode='fast'?>" in wire
    assert "urn:demo" in wire


# 434｜Element 的属性映射、子节点序列、浅复制、itertext 与 clear。
#
# attrib 是活 dict；get/set/keys/items 操作同一对象。Element 同时实现可变序列协议，append/
# extend/insert 和索引切片都直接管理 child 对象。copy.copy 复制容器和属性字典但仍共享 child；
# clear 会删除 children/attributes 并把 text/tail 置 None。空 Element 在 3.10 中是假值，勿拿它判空缺。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.etree.ElementTree.Element.get
# polyglot-covers: python.xml.etree.ElementTree.Element.set
# polyglot-covers: python.xml.etree.ElementTree.Element.keys
# polyglot-covers: python.xml.etree.ElementTree.Element.items
# polyglot-covers: python.xml.etree.ElementTree.Element.attrib-live-dict
# polyglot-covers: python.xml.etree.ElementTree.Element.append
# polyglot-covers: python.xml.etree.ElementTree.Element.extend
# polyglot-covers: python.xml.etree.ElementTree.Element.insert
# polyglot-covers: python.xml.etree.ElementTree.Element-sequence-protocol
# polyglot-covers: python.xml.etree.ElementTree.Element-shallow-copy-shares-children
# polyglot-covers: python.xml.etree.ElementTree.Element.itertext
# polyglot-covers: python.xml.etree.ElementTree.Element.clear
# polyglot-covers: python.xml.etree.ElementTree.empty-element-false-trap



def test_attribute_helpers_and_attrib_reference_mutate_the_same_mapping():
    element = ET.Element("item", {"a": "1"})
    live_attributes = element.attrib
    element.set("b", "2")
    live_attributes["c"] = "3"

    assert element.get("a") == "1"
    assert element.get("missing", "fallback") == "fallback"
    assert element.keys() == ["a", "b", "c"]
    assert element.items() == [("a", "1"), ("b", "2"), ("c", "3")]


def test_children_follow_mutable_sequence_order_and_shallow_copy_shares_nodes():
    root = ET.Element("root")
    one = ET.Element("one")
    two = ET.Element("two")
    zero = ET.Element("zero")
    root.append(one)
    root.extend([two])
    root.insert(0, zero)

    assert [child.tag for child in root] == ["zero", "one", "two"]
    assert root[1] is one
    assert [child.tag for child in root[1:]] == ["one", "two"]

    cloned = copy(root)
    cloned.attrib["copy-only"] = "yes"
    cloned[0].set("shared", "yes")
    assert "copy-only" not in root.attrib
    assert root[0].get("shared") == "yes"


def test_itertext_includes_descendant_text_and_tails_in_document_order():
    root = ET.fromstring("<root>before<a>A<b>B</b>tail-b</a>tail-a</root>")
    assert list(root.itertext()) == ["before", "A", "B", "tail-b", "tail-a"]
    assert "".join(root.itertext()) == "beforeABtail-btail-a"


def test_clear_resets_complete_node_state_and_empty_element_is_false_in_310():
    root = ET.fromstring("<root a='1'>text<child />tail</root>")
    root.clear()

    assert root.tag == "root"
    assert root.attrib == {}
    assert root.text is None
    assert root.tail is None
    assert len(root) == 0
    assert bool(root) is False
    assert root is not None


# 435｜ElementTree 的 find/findall/iterfind/findtext、深度遍历与 namespace。
#
# find("tag") 只看直接 child，``.//tag`` 才递归；findall 返回列表，iterfind 延迟产生匹配项。
# findtext 区分“未找到”与“找到了空元素”。XML namespace 在内存中是 ``{uri}local``，XPath 可用
# prefix 映射或 3.8 起的 namespace wildcard；默认 namespace 也必须显式绑定一个查询前缀。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.etree.ElementTree.Element.find
# polyglot-covers: python.xml.etree.ElementTree.Element.findall
# polyglot-covers: python.xml.etree.ElementTree.Element.iterfind
# polyglot-covers: python.xml.etree.ElementTree.Element.findtext
# polyglot-covers: python.xml.etree.ElementTree.Element.iter
# polyglot-covers: python.xml.etree.ElementTree.ElementTree.find
# polyglot-covers: python.xml.etree.ElementTree.ElementTree.findall
# polyglot-covers: python.xml.etree.ElementTree.ElementTree.iterfind
# polyglot-covers: python.xml.etree.ElementTree.ElementTree.findtext
# polyglot-covers: python.xml.etree.ElementTree.ElementTree.iter
# polyglot-covers: python.xml.etree.ElementTree.xpath-direct-child-versus-descendant
# polyglot-covers: python.xml.etree.ElementTree.findtext-missing-versus-empty
# polyglot-covers: python.xml.etree.ElementTree.namespace-expanded-name
# polyglot-covers: python.xml.etree.ElementTree.namespace-prefix-map
# polyglot-covers: python.xml.etree.ElementTree.namespace-wildcards-3.8



XML_TEXT_435 = """\
<catalog xmlns="urn:catalog" xmlns:m="urn:meta">
  <item id="a"><name>Alpha</name><m:rank>1</m:rank></item>
  <group><item id="b"><name /></item></group>
</catalog>
"""


def test_find_paths_distinguish_direct_children_descendants_and_empty_text():
    root = ET.fromstring("<root><item>A</item><group><item /></group></root>")
    tree = ET.ElementTree(root)

    assert root.find("item").text == "A"
    assert len(root.findall("item")) == 1
    assert len(root.findall(".//item")) == 2
    assert list(root.iterfind(".//item")) == root.findall(".//item")
    assert [node.tag for node in root.iter()] == ["root", "item", "group", "item"]
    assert root.findtext("item") == "A"
    assert root.findtext("group/item") == ""
    assert root.findtext("missing", "fallback") == "fallback"

    assert tree.find("item") is root[0]
    assert tree.findall(".//item") == root.findall(".//item")
    assert list(tree.iterfind(".//item")) == root.findall(".//item")
    assert tree.findtext("item") == "A"
    assert list(tree.iter()) == list(root.iter())


def test_namespace_queries_use_expanded_names_prefix_maps_and_wildcards():
    root = ET.fromstring(XML_TEXT_435)
    ns = {"c": "urn:catalog", "m": "urn:meta"}

    assert root.tag == "{urn:catalog}catalog"
    assert [node.get("id") for node in root.findall(".//c:item", ns)] == ["a", "b"]
    assert root.findtext("c:item/c:name", namespaces=ns) == "Alpha"
    assert root.find(".//m:rank", ns).text == "1"
    assert [node.tag for node in root.findall(".//{*}rank")] == ["{urn:meta}rank"]
    assert len(root.findall(".//{urn:catalog}*")) == 5


# 436｜ElementTree 支持的 XPath 属性/文本谓词、位置函数与边界。
#
# ElementTree 只实现 XPath 子集：属性存在/相等、3.10 新增不等，完整文本相等/不等，以及
# ``[n]``、``[last()]``、``[last()-n]``。谓词必须跟在 tag、``*`` 或另一谓词后；绝对路径不能
# 直接用于 Element。它不提供任意 XPath 函数、布尔运算或完整 XPath 1.0 引擎。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.etree.ElementTree.xpath-attribute-exists
# polyglot-covers: python.xml.etree.ElementTree.xpath-attribute-equality
# polyglot-covers: python.xml.etree.ElementTree.xpath-attribute-inequality-3.10
# polyglot-covers: python.xml.etree.ElementTree.xpath-text-equality
# polyglot-covers: python.xml.etree.ElementTree.xpath-text-inequality-3.10
# polyglot-covers: python.xml.etree.ElementTree.xpath-child-text-predicate
# polyglot-covers: python.xml.etree.ElementTree.xpath-position
# polyglot-covers: python.xml.etree.ElementTree.xpath-last
# polyglot-covers: python.xml.etree.ElementTree.xpath-last-minus
# polyglot-covers: python.xml.etree.ElementTree.xpath-supported-subset
# polyglot-covers: python.xml.etree.ElementTree.absolute-path-on-element-syntaxerror




XML_TEXT_436 = """\
<catalog>
  <item id="a" state="ready"><name>Alpha</name></item>
  <item id="b" state="draft"><name>Beta</name></item>
  <item id="c"><name>Gamma</name></item>
</catalog>
"""


def test_attribute_and_text_predicates_filter_the_supported_xpath_subset():
    root = ET.fromstring(XML_TEXT_436)

    assert [node.get("id") for node in root.findall("item[@state]")] == ["a", "b"]
    assert [node.get("id") for node in root.findall("item[@state='ready']")] == ["a"]
    assert [node.get("id") for node in root.findall("item[@state!='ready']")] == ["b"]
    assert [node.get("id") for node in root.findall("item[.='Beta']")] == ["b"]
    assert [node.get("id") for node in root.findall("item[.!='Beta']")] == ["a", "c"]
    assert [node.get("id") for node in root.findall("item[name='Gamma']")] == ["c"]


def test_position_predicates_are_one_based_and_relative_to_same_tag_siblings():
    root = ET.fromstring(XML_TEXT_436)

    assert root.find("item[1]").get("id") == "a"
    assert root.find("item[2]").get("id") == "b"
    assert root.find("item[last()]").get("id") == "c"
    assert root.find("item[last()-1]").get("id") == "b"


def test_element_paths_are_relative_and_unsupported_absolute_form_raises():
    root = ET.fromstring(XML_TEXT_436)
    with pytest.raises(SyntaxError):
        root.findall("/catalog/item")


# 437｜ElementTree 节点移除、根替换与 ``indent()`` 的可变语义。
#
# ``Element.remove()`` 按对象身份寻找子节点，不会按 tag、属性或序列化内容做值比较。遍历时
# 直接改变 children 会令遍历结果未定义，稳妥做法是先保存快照。``_setroot()`` 会整体替换树根；
# ``indent()`` 通过改写 ``text``/``tail`` 加入空白，适合输出副本，不是无副作用的格式化视图。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.etree.ElementTree.Element.remove
# polyglot-covers: python.xml.etree.ElementTree.remove-compares-child-identity
# polyglot-covers: python.xml.etree.ElementTree.remove-missing-valueerror
# polyglot-covers: python.xml.etree.ElementTree.mutation-during-iteration-undefined
# polyglot-covers: python.xml.etree.ElementTree.snapshot-before-child-removal
# polyglot-covers: python.xml.etree.ElementTree.ElementTree._setroot
# polyglot-covers: python.xml.etree.ElementTree.indent
# polyglot-covers: python.xml.etree.ElementTree.indent-mutates-text-and-tail




def test_remove_matches_the_exact_child_object_not_an_equal_looking_node():
    root = ET.Element("root")
    first = ET.SubElement(root, "item", id="same")
    second = ET.SubElement(root, "item", id="same")

    root.remove(second)

    assert list(root) == [first]
    with pytest.raises(ValueError):
        root.remove(ET.Element("item", {"id": "same"}))


def test_filtering_children_uses_a_snapshot_before_mutating_the_tree():
    root = ET.fromstring(
        "<root><item keep='yes'/><item/><item keep='yes'/><item/></root>"
    )

    # Element.iter() 期间改变树结构的结果没有定义；list(root) 固定本轮候选集合。
    for child in list(root):
        if child.get("keep") != "yes":
            root.remove(child)

    assert [child.get("keep") for child in root] == ["yes", "yes"]


def test_setroot_replaces_the_entire_document_root():
    old_root = ET.fromstring("<old><child/></old>")
    tree = ET.ElementTree(old_root)
    new_root = ET.Element("new")

    tree._setroot(new_root)

    assert tree.getroot() is new_root
    assert tree.getroot() is not old_root
    assert len(tree.getroot()) == 0


def test_indent_pretty_prints_by_mutating_text_and_tail_whitespace():
    root = ET.fromstring("<root><first/><second/></root>")

    ET.indent(root, space="  ")

    assert root.text == "\n  "
    assert root[0].tail == "\n  "
    assert root[1].tail == "\n"
    assert ET.tostring(root, encoding="unicode") == (
        "<root>\n  <first />\n  <second />\n</root>"
    )


# 438｜``tostring``、``tostringlist`` 与 ``ElementTree.write`` 的输出契约。
#
# 序列化默认返回字节；只有 ``encoding='unicode'`` 返回 ``str``。XML、HTML、text 三种 method
# 表达的是不同输出模型，空元素和 XML 声明也可独立控制。``write()`` 不替调用者适配二进制/文本
# 流：编码为字节时写入 binary stream，编码为 unicode 时写入 text stream，否则在写入处报错。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.etree.ElementTree.tostring
# polyglot-covers: python.xml.etree.ElementTree.tostring.encoding
# polyglot-covers: python.xml.etree.ElementTree.tostring.xml_declaration
# polyglot-covers: python.xml.etree.ElementTree.tostring.short_empty_elements
# polyglot-covers: python.xml.etree.ElementTree.tostring.method-xml-html-text
# polyglot-covers: python.xml.etree.ElementTree.tostringlist
# polyglot-covers: python.xml.etree.ElementTree.tostringlist-chunk-boundaries-unspecified
# polyglot-covers: python.xml.etree.ElementTree.ElementTree.write
# polyglot-covers: python.xml.etree.ElementTree.ElementTree.write-stream-type-matches-encoding




def test_tostring_selects_bytes_or_text_and_controls_xml_surface_syntax():
    root = ET.Element("root", {"label": "中文"})
    ET.SubElement(root, "empty")

    default_wire = ET.tostring(root)
    unicode_wire = ET.tostring(root, encoding="unicode", short_empty_elements=False)
    declared_wire = ET.tostring(root, encoding="utf-8", xml_declaration=True)

    assert isinstance(default_wire, bytes)
    assert isinstance(unicode_wire, str)
    assert unicode_wire == '<root label="中文"><empty></empty></root>'
    assert declared_wire.startswith(b"<?xml version='1.0' encoding='utf-8'?>")


def test_serialization_methods_choose_xml_html_or_only_text_content():
    root = ET.Element("div")
    root.text = "before"
    br = ET.SubElement(root, "br")
    br.tail = "after"

    assert ET.tostring(root, encoding="unicode", method="xml") == (
        "<div>before<br />after</div>"
    )
    assert ET.tostring(root, encoding="unicode", method="html") == (
        "<div>before<br>after</div>"
    )
    assert ET.tostring(root, encoding="unicode", method="text") == "beforeafter"


def test_tostringlist_is_a_chunked_form_whose_join_matches_tostring():
    root = ET.fromstring("<root><item>one</item><item>two</item></root>")

    chunks = ET.tostringlist(root, encoding="utf-8")

    assert all(isinstance(chunk, bytes) for chunk in chunks)
    assert b"".join(chunks) == ET.tostring(root, encoding="utf-8")
    # 文档不保证 chunk 数量和边界；消费者只能依赖拼接后的结果。


def test_write_requires_a_stream_matching_the_selected_encoding():
    tree = ET.ElementTree(ET.fromstring("<root>中文</root>"))
    binary = io.BytesIO()
    text = io.StringIO()

    tree.write(binary, encoding="utf-8", xml_declaration=True)
    tree.write(text, encoding="unicode")

    assert b"\xe4\xb8\xad\xe6\x96\x87" in binary.getvalue()
    assert text.getvalue() == "<root>中文</root>"

    with pytest.raises(TypeError):
        tree.write(io.StringIO(), encoding="utf-8")
    with pytest.raises(TypeError):
        tree.write(io.BytesIO(), encoding="unicode")


# 439｜ElementTree 序列化时的前缀注册、默认命名空间与 QName 值。
#
# 树内名称保存为 ``{uri}local``，前缀只是序列化选择。``register_namespace()`` 修改进程级映射，
# 相同前缀或 URI 的旧映射会被移除；测试必须隔离这种全局状态。``default_namespace`` 只能用于
# 完全限定的名称，混入未限定 tag/属性会报错，不能把它当作自动补命名空间的开关。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.etree.ElementTree.register_namespace
# polyglot-covers: python.xml.etree.ElementTree.register_namespace-global-state
# polyglot-covers: python.xml.etree.ElementTree.register_namespace-replaces-prefix-or-uri
# polyglot-covers: python.xml.etree.ElementTree.tostring.default_namespace
# polyglot-covers: python.xml.etree.ElementTree.default_namespace-requires-qualified-names
# polyglot-covers: python.xml.etree.ElementTree.QName-attribute-value




def test_registered_prefix_controls_serialization_without_changing_expanded_names(
    monkeypatch,
):
    # 公共 API 没有 unregister；替换模块映射副本，让 pytest 在用例结束时恢复原对象。
    monkeypatch.setattr(ET, "_namespace_map", ET._namespace_map.copy())
    ET.register_namespace("demo", "urn:demo")
    root = ET.Element("{urn:demo}root")
    child = ET.SubElement(root, "{urn:demo}item")
    child.set("kind", ET.QName("urn:demo", "special"))

    wire = ET.tostring(root, encoding="unicode")

    assert wire.startswith('<demo:root xmlns:demo="urn:demo">')
    assert '<demo:item kind="demo:special"' in wire
    assert root.tag == "{urn:demo}root"


def test_registering_the_same_prefix_or_uri_replaces_the_previous_mapping(monkeypatch):
    monkeypatch.setattr(ET, "_namespace_map", ET._namespace_map.copy())

    ET.register_namespace("first", "urn:one")
    ET.register_namespace("first", "urn:two")
    old_uri_wire = ET.tostring(ET.Element("{urn:one}item"), encoding="unicode")
    assert "first:item" not in old_uri_wire

    ET.register_namespace("second", "urn:two")
    new_uri_wire = ET.tostring(ET.Element("{urn:two}item"), encoding="unicode")
    assert "second:item" in new_uri_wire
    assert "first:item" not in new_uri_wire


def test_default_namespace_removes_prefix_only_for_fully_qualified_names():
    root = ET.Element("{urn:catalog}catalog")
    ET.SubElement(root, "{urn:catalog}item")

    wire = ET.tostring(root, encoding="unicode", default_namespace="urn:catalog")

    assert wire == '<catalog xmlns="urn:catalog"><item /></catalog>'

    root.set("plain", "not-qualified")
    with pytest.raises(ValueError, match="non-qualified names"):
        ET.tostring(root, encoding="unicode", default_namespace="urn:catalog")


# 440｜``iterparse()`` 的事件流、命名空间事件与增量清理工作流。
#
# ``iterparse()`` 增量构树但会执行阻塞读取；需要完全非阻塞输入时应选 ``XMLPullParser``。start
# 事件只保证已读完 ``>``，属性可用，但 text、tail 和 children 尚无完成保证；读取完整节点应处理
# end 事件。迭代器耗尽后 ``root`` 才是完整根节点，大文件可在消费 end 事件后 ``clear()``。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.etree.ElementTree.iterparse
# polyglot-covers: python.xml.etree.ElementTree.iterparse-default-end-event
# polyglot-covers: python.xml.etree.ElementTree.iterparse-start-end-events
# polyglot-covers: python.xml.etree.ElementTree.iterparse-comment-pi-events-3.8
# polyglot-covers: python.xml.etree.ElementTree.iterparse-start-ns-end-ns-events
# polyglot-covers: python.xml.etree.ElementTree.iterparse.root-after-exhaustion
# polyglot-covers: python.xml.etree.ElementTree.iterparse-start-event-incomplete-node
# polyglot-covers: python.xml.etree.ElementTree.iterparse-blocking-read
# polyglot-covers: python.xml.etree.ElementTree.iterparse-clear-after-end-memory-workflow



XML_BYTES = b"""\
<root xmlns:p="urn:parts">
  <!--note--><?build fast?>
  <p:item id="one">alpha</p:item>
  <p:item id="two">beta</p:item>
</root>
"""


def test_default_iterparse_yields_only_end_events_and_exposes_root_at_exhaustion():
    iterator = ET.iterparse(io.BytesIO(XML_BYTES))
    events = list(iterator)

    assert {event for event, _ in events} == {"end"}
    assert [node.tag for _, node in events] == [
        "{urn:parts}item",
        "{urn:parts}item",
        "root",
    ]
    assert iterator.root.tag == "root"


def test_iterparse_reports_markup_and_namespace_events_without_inserting_them():
    requested = ("start", "end", "comment", "pi", "start-ns", "end-ns")
    iterator = ET.iterparse(io.BytesIO(XML_BYTES), events=requested)
    events = list(iterator)

    assert ("start-ns", ("p", "urn:parts")) in events
    assert any(event == "end-ns" and value is None for event, value in events)
    assert any(event == "comment" and node.text == "note" for event, node in events)
    assert any(event == "pi" and node.text == "build fast" for event, node in events)
    # comment/pi 事件可观察这些节点，但默认 TreeBuilder 不把它们插入结果树。
    assert [child.tag for child in iterator.root] == [
        "{urn:parts}item",
        "{urn:parts}item",
    ]


def test_large_document_workflow_reads_complete_end_nodes_then_clears_them():
    iterator = ET.iterparse(io.BytesIO(XML_BYTES), events=("start", "end"))
    rows = []

    for event, node in iterator:
        if event == "end" and node.tag == "{urn:parts}item":
            rows.append((node.get("id"), node.text))
            node.clear()

    assert rows == [("one", "alpha"), ("two", "beta")]
    assert all(child.attrib == {} and child.text is None for child in iterator.root)


# 441｜``XMLPullParser`` 的 feed/read_events 队列与非阻塞解析模式。
#
# 调用者自行取得网络或设备数据，再用 ``feed()`` 投递小块，因此解析器本身不执行阻塞读取。
# ``read_events()`` 只消费当前已排队事件，同一事件不会在下次调用中重复出现。start 事件仍只
# 代表开始标签闭合；应在 end 事件读取完整内容。部分 3.10 修订版回移了 ``flush()``，需做能力检测。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.etree.ElementTree.XMLPullParser
# polyglot-covers: python.xml.etree.ElementTree.XMLPullParser.feed
# polyglot-covers: python.xml.etree.ElementTree.XMLPullParser.read_events
# polyglot-covers: python.xml.etree.ElementTree.XMLPullParser.close
# polyglot-covers: python.xml.etree.ElementTree.XMLPullParser-nonblocking-input-pattern
# polyglot-covers: python.xml.etree.ElementTree.XMLPullParser-event-consumed-once
# polyglot-covers: python.xml.etree.ElementTree.XMLPullParser-start-node-incomplete
# polyglot-covers: python.xml.etree.ElementTree.XMLPullParser.flush-version-guard
# polyglot-covers: python.xml.etree.ElementTree.flush-reparse-deferral-security-note



def test_pull_parser_exposes_only_events_available_after_each_feed():
    parser = ET.XMLPullParser(events=("start", "end"))

    parser.feed("<root><item id='one'>")
    first_batch = list(parser.read_events())
    assert [(event, node.tag) for event, node in first_batch] == [
        ("start", "root"),
        ("start", "item"),
    ]
    assert list(parser.read_events()) == []

    parser.feed("value</item><item id='two'/></root>")
    second_batch = list(parser.read_events())
    parser.close()

    assert [(event, node.tag) for event, node in second_batch] == [
        ("end", "item"),
        ("start", "item"),
        ("end", "item"),
        ("end", "root"),
    ]
    assert second_batch[0][1].text == "value"
    assert list(parser.read_events()) == []


def test_pull_parser_reports_namespace_comment_and_pi_events():
    parser = ET.XMLPullParser(
        events=("start-ns", "end-ns", "comment", "pi", "end")
    )
    parser.feed(
        '<root xmlns:p="urn:p"><!--note--><?build fast?><p:item/></root>'
    )
    parser.close()
    events = list(parser.read_events())

    assert ("start-ns", ("p", "urn:p")) in events
    assert any(event == "end-ns" and value is None for event, value in events)
    assert any(event == "comment" and node.text == "note" for event, node in events)
    assert any(event == "pi" and node.text == "build fast" for event, node in events)


def test_flush_is_used_only_when_the_running_310_patch_release_provides_it():
    parser = ET.XMLPullParser(events=("end",))
    parser.feed("<root><item/>")

    flush = getattr(parser, "flush", None)
    if flush is not None:
        # flush 会临时关闭 Expat reparse deferral；不可信输入下要权衡即时性与安全影响。
        flush()

    parser.feed("</root>")
    parser.close()
    assert [node.tag for event, node in parser.read_events() if event == "end"] == [
        "item",
        "root",
    ]


# 442｜``XMLParser`` target 协议与 ``TreeBuilder`` 的注释、PI 插入选项。
#
# ``XMLParser`` 把 start/end/data 事件交给 target，并把 ``target.close()`` 的值作为解析结果，
# 所以 target 不一定构造 Element。默认 ``TreeBuilder`` 会跳过源文档中的注释和处理指令；显式
# 开启 ``insert_comments``/``insert_pis`` 才把它们作为特殊节点保留，factory 可定制节点创建。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.etree.ElementTree.XMLParser
# polyglot-covers: python.xml.etree.ElementTree.XMLParser.feed
# polyglot-covers: python.xml.etree.ElementTree.XMLParser.close
# polyglot-covers: python.xml.etree.ElementTree.XMLParser-custom-target-protocol
# polyglot-covers: python.xml.etree.ElementTree.XMLParser-target-close-result
# polyglot-covers: python.xml.etree.ElementTree.TreeBuilder
# polyglot-covers: python.xml.etree.ElementTree.TreeBuilder.insert_comments
# polyglot-covers: python.xml.etree.ElementTree.TreeBuilder.insert_pis
# polyglot-covers: python.xml.etree.ElementTree.TreeBuilder.element_factory
# polyglot-covers: python.xml.etree.ElementTree.TreeBuilder.comment_factory
# polyglot-covers: python.xml.etree.ElementTree.TreeBuilder.pi_factory



class EventTarget:
    def __init__(self):
        self.events = []

    def start(self, tag, attrs):
        self.events.append(("start", tag, dict(attrs)))

    def end(self, tag):
        self.events.append(("end", tag))

    def data(self, text):
        if text.strip():
            self.events.append(("data", text))

    def close(self):
        return tuple(self.events)


def test_custom_target_receives_parser_events_and_controls_close_result():
    target = EventTarget()
    parser = ET.XMLParser(target=target)

    parser.feed("<root id='one'>")
    parser.feed("value<child/></root>")
    result = parser.close()

    assert result == (
        ("start", "root", {"id": "one"}),
        ("data", "value"),
        ("start", "child", {}),
        ("end", "child"),
        ("end", "root"),
    )


def test_treebuilder_must_opt_in_to_retain_parsed_comments_and_pis():
    xml = "<root><!--note--><?build fast?><child/></root>"
    default_root = ET.fromstring(xml)
    parser = ET.XMLParser(
        target=ET.TreeBuilder(insert_comments=True, insert_pis=True)
    )
    retained_root = ET.fromstring(xml, parser=parser)

    assert [child.tag for child in default_root] == ["child"]
    assert [child.tag for child in retained_root] == [
        ET.Comment,
        ET.ProcessingInstruction,
        "child",
    ]
    assert retained_root[0].text == "note"
    assert retained_root[1].text == "build fast"


def test_treebuilder_factories_customize_created_elements_comments_and_pis():
    calls = []

    class MarkerElement(ET.Element):
        pass

    def element_factory(tag, attrs):
        calls.append(("element", tag))
        # factory 返回的节点仍须保留原 tag，否则 TreeBuilder 无法匹配对应的结束标签。
        return MarkerElement(tag, attrs)

    def comment_factory(text):
        calls.append(("comment", text))
        return ET.Comment(text.upper())

    def pi_factory(target, text):
        calls.append(("pi", target, text))
        return ET.ProcessingInstruction(target.upper(), text)

    builder = ET.TreeBuilder(
        element_factory=element_factory,
        comment_factory=comment_factory,
        pi_factory=pi_factory,
        insert_comments=True,
        insert_pis=True,
    )
    parser = ET.XMLParser(target=builder)
    root = ET.fromstring("<root><!--note--><?build fast?></root>", parser=parser)

    assert isinstance(root, MarkerElement)
    assert root.tag == "root"
    assert root[0].text == "NOTE"
    assert root[1].text == "BUILD fast"
    assert calls == [
        ("element", "root"),
        ("comment", "note"),
        ("pi", "build", "fast"),
    ]


# 443｜ElementTree 的 C14N 2.0 规范化输出与 ``C14NWriterTarget``。
#
# ``canonicalize()`` 生成文本而非字节，统一属性顺序、命名空间声明和空元素形式，适合签名或
# 逐字节比较前的稳定表示；它不是普通 pretty printer。输入可来自字符串或文件，输出可返回
# ``str`` 或写入 text stream。``C14NWriterTarget`` 则把解析事件直接流式写成相同规范形式。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.etree.ElementTree.canonicalize
# polyglot-covers: python.xml.etree.ElementTree.canonicalize-text-output
# polyglot-covers: python.xml.etree.ElementTree.canonicalize.xml_data
# polyglot-covers: python.xml.etree.ElementTree.canonicalize.from_file
# polyglot-covers: python.xml.etree.ElementTree.canonicalize.out-text-stream
# polyglot-covers: python.xml.etree.ElementTree.canonicalize-attribute-order
# polyglot-covers: python.xml.etree.ElementTree.canonicalize-expands-empty-elements
# polyglot-covers: python.xml.etree.ElementTree.C14NWriterTarget



XML_TEXT_443 = '<root z="2" a="1"><empty/><!--note--></root>'


def test_canonicalize_returns_stable_text_and_omits_comments_by_default():
    canonical = ET.canonicalize(XML_TEXT_443)

    assert isinstance(canonical, str)
    assert canonical == '<root a="1" z="2"><empty></empty></root>'


def test_canonicalize_accepts_a_file_and_writes_to_a_text_stream(tmp_path):
    source = tmp_path / "source.xml"
    source.write_text(XML_TEXT_443, encoding="utf-8")
    output = io.StringIO()

    result = ET.canonicalize(from_file=source, out=output, with_comments=True)

    assert result is None
    assert output.getvalue() == (
        '<root a="1" z="2"><empty></empty><!--note--></root>'
    )


def test_c14n_writer_target_streams_canonical_text_from_parser_events():
    chunks = []
    target = ET.C14NWriterTarget(chunks.append, with_comments=True)
    parser = ET.XMLParser(target=target)

    parser.feed('<root z="2"')
    parser.feed(' a="1"><empty/><!--note--></root>')
    result = parser.close()

    assert result is None
    assert "".join(chunks) == (
        '<root a="1" z="2"><empty></empty><!--note--></root>'
    )


# 444｜C14N 的空白、排除项、前缀重写与 QName 感知选项。
#
# 规范化默认保留文本空白；``strip_text`` 会改变字符数据，不能为追求“整齐”随意开启。过滤
# tag/属性会改变文档含义，只适合调用方明确排除的元数据。``rewrite_prefixes`` 可消除原前缀选择
# 差异；若 QName 写在文本或属性值中，必须声明 qname-aware 集合才能同步重写其词法前缀。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.etree.ElementTree.C14NWriterTarget.with_comments
# polyglot-covers: python.xml.etree.ElementTree.C14NWriterTarget.strip_text
# polyglot-covers: python.xml.etree.ElementTree.C14NWriterTarget.rewrite_prefixes
# polyglot-covers: python.xml.etree.ElementTree.C14NWriterTarget.qname_aware_tags
# polyglot-covers: python.xml.etree.ElementTree.C14NWriterTarget.qname_aware_attrs
# polyglot-covers: python.xml.etree.ElementTree.C14NWriterTarget.exclude_attrs
# polyglot-covers: python.xml.etree.ElementTree.C14NWriterTarget.exclude_tags
# polyglot-covers: python.xml.etree.ElementTree.canonicalize-semantic-options-trap



def test_strip_and_exclude_options_make_explicit_semantic_changes():
    xml = '<root keep="yes" secret="x">  value  <skip>hidden</skip></root>'

    canonical = ET.canonicalize(
        xml,
        strip_text=True,
        exclude_attrs={"secret"},
        exclude_tags={"skip"},
    )

    assert canonical == '<root keep="yes">value</root>'


def test_rewrite_prefixes_also_rewrites_declared_qname_text_and_attributes():
    xml = (
        '<root xmlns:p="urn:parts">'
        '<kind>p:item</kind><node type="p:special"/>'
        "</root>"
    )

    canonical = ET.canonicalize(
        xml,
        rewrite_prefixes=True,
        qname_aware_tags={"kind"},
        qname_aware_attrs={"type"},
    )

    assert "p:item" not in canonical
    assert "p:special" not in canonical
    assert "urn:parts" in canonical
    assert ":item" in canonical
    assert ":special" in canonical


def test_comments_are_retained_only_when_requested():
    xml = "<root><!--audit--><item/></root>"

    assert "<!--audit-->" not in ET.canonicalize(xml)
    assert "<!--audit-->" in ET.canonicalize(xml, with_comments=True)


# 445｜``ElementInclude`` 的 XML/text 替换、自定义 loader 与递归限制。
#
# ``include()`` 就地替换 XInclude 节点：parse=xml 要求 loader 返回 Element，parse=text 返回 str，
# 并把原 include 的 tail 正确接回树。默认 loader 会访问文件系统；可复现测试和受控资源通常应
# 传自定义 loader。``base_url`` 负责解析相对 href，``max_depth`` 与循环检测限制递归包含。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.etree.ElementInclude.include
# polyglot-covers: python.xml.etree.ElementInclude.default_loader
# polyglot-covers: python.xml.etree.ElementInclude.custom-loader-protocol
# polyglot-covers: python.xml.etree.ElementInclude.parse-xml-replacement
# polyglot-covers: python.xml.etree.ElementInclude.parse-text-merge
# polyglot-covers: python.xml.etree.ElementInclude.include-preserves-tail
# polyglot-covers: python.xml.etree.ElementInclude.include.base_url
# polyglot-covers: python.xml.etree.ElementInclude.include.max_depth
# polyglot-covers: python.xml.etree.ElementInclude.LimitedRecursiveIncludeError
# polyglot-covers: python.xml.etree.ElementInclude.FatalIncludeError




XI = "http://www.w3.org/2001/XInclude"


def test_custom_loader_replaces_xml_and_preserves_the_include_tail():
    root = ET.fromstring(
        f'<root xmlns:xi="{XI}"><xi:include href="part.xml"/>after</root>'
    )
    calls = []

    def loader(href, parse, encoding=None):
        calls.append((href, parse, encoding))
        return ET.fromstring("<part><value>42</value></part>")

    result = ElementInclude.include(root, loader=loader)

    assert result is None
    assert calls == [("part.xml", "xml", None)]
    assert root[0].tag == "part"
    assert root[0].findtext("value") == "42"
    assert root[0].tail == "after"


def test_text_include_merges_content_into_parent_text_or_previous_tail():
    first = ET.fromstring(
        f'<root xmlns:xi="{XI}">before<xi:include href="note.txt"/>after</root>'
    )
    second = ET.fromstring(
        f'<root xmlns:xi="{XI}"><lead/>before<xi:include href="note.txt"/>'
        "after</root>"
    )

    def text_loader(href, parse, encoding=None):
        assert (href, parse, encoding) == ("note.txt", "text", "utf-8")
        return "INCLUDED"

    first[0].set("parse", "text")
    first[0].set("encoding", "utf-8")
    second[1].set("parse", "text")
    second[1].set("encoding", "utf-8")
    ElementInclude.include(first, loader=text_loader)
    ElementInclude.include(second, loader=text_loader)

    assert first.text == "beforeINCLUDEDafter"
    assert len(first) == 0
    assert second[0].tail == "beforeINCLUDEDafter"
    assert len(second) == 1


def test_default_loader_reads_controlled_temp_files_and_base_url_resolves_href(
    tmp_path,
):
    pieces = tmp_path / "pieces"
    pieces.mkdir()
    xml_path = pieces / "part.xml"
    text_path = pieces / "note.txt"
    xml_path.write_text("<part>value</part>", encoding="utf-8")
    text_path.write_text("中文", encoding="utf-8")

    assert ElementInclude.default_loader(str(xml_path), "xml").tag == "part"
    assert ElementInclude.default_loader(str(text_path), "text", "utf-8") == "中文"

    root = ET.fromstring(
        f'<root xmlns:xi="{XI}"><xi:include href="pieces/part.xml"/></root>'
    )
    ElementInclude.include(root, base_url=str(tmp_path / "document.xml"))
    assert root[0].tag == "part"


def test_depth_limit_and_circular_href_detection_stop_recursive_includes():
    def nested_loader(href, parse, encoding=None):
        if href == "a.xml":
            return ET.fromstring(
                f'<a xmlns:xi="{XI}"><xi:include href="b.xml"/></a>'
            )
        return ET.Element("b")

    limited = ET.fromstring(
        f'<root xmlns:xi="{XI}"><xi:include href="a.xml"/></root>'
    )
    with pytest.raises(ElementInclude.LimitedRecursiveIncludeError):
        ElementInclude.include(limited, loader=nested_loader, max_depth=1)

    def circular_loader(href, parse, encoding=None):
        return ET.fromstring(
            f'<part xmlns:xi="{XI}"><xi:include href="same.xml"/></part>'
        )

    circular = ET.fromstring(
        f'<root xmlns:xi="{XI}"><xi:include href="same.xml"/></root>'
    )
    with pytest.raises(ElementInclude.FatalIncludeError, match="recursive include"):
        ElementInclude.include(circular, loader=circular_loader)


# 446｜``ParseError`` 诊断信息与 XML 不可信输入的安全边界。
#
# ``ParseError`` 附带 Expat 错误码和 ``(line, column)`` 位置，适合向调用者报告结构错误。标准库
# XML 解析器不是处理恶意 XML 的安全边界：实体会展开，巨量实体、深层嵌套和大 token 的防护还
# 依赖当前链接的 Expat 修订版。这里只用一个微小实体说明机制，绝不构造资源耗尽载荷。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.etree.ElementTree.ParseError
# polyglot-covers: python.xml.etree.ElementTree.ParseError.code
# polyglot-covers: python.xml.etree.ElementTree.ParseError.position
# polyglot-covers: python.xml.etree.ElementTree.mismatched-tag-error
# polyglot-covers: python.xml.etree.ElementTree.undefined-entity-error
# polyglot-covers: python.xml-security-untrusted-data-warning
# polyglot-covers: python.xml-security-entity-expansion-mechanism
# polyglot-covers: python.xml-security-expat-patch-level-dependency




def test_parse_error_exposes_machine_readable_code_and_source_position():
    with pytest.raises(ET.ParseError) as caught:
        ET.fromstring("<root>\n  <item>value</root>")

    error = caught.value
    assert isinstance(error.code, int)
    assert error.position[0] == 2
    assert error.position[1] > 0
    assert "mismatched tag" in str(error)


def test_undefined_entity_is_a_parse_error_instead_of_literal_text():
    with pytest.raises(ET.ParseError, match="undefined entity"):
        ET.fromstring("<root>&missing;</root>")


def test_tiny_internal_entity_demonstrates_why_untrusted_xml_needs_limits():
    xml = '<!DOCTYPE root [<!ENTITY word "safe">]><root>&word;</root>'

    root = ET.fromstring(xml)

    assert root.text == "safe"
    # 这里仅证明解析器会做替换；切勿把“能解析”误当作可安全接收恶意 XML。
