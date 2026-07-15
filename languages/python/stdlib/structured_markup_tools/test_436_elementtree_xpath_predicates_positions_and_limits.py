"""436｜ElementTree 支持的 XPath 属性/文本谓词、位置函数与边界。

ElementTree 只实现 XPath 子集：属性存在/相等、3.10 新增不等，完整文本相等/不等，以及
``[n]``、``[last()]``、``[last()-n]``。谓词必须跟在 tag、``*`` 或另一谓词后；绝对路径不能
直接用于 Element。它不提供任意 XPath 函数、布尔运算或完整 XPath 1.0 引擎。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

from xml.etree import ElementTree as ET

import pytest


XML_TEXT = """\
<catalog>
  <item id="a" state="ready"><name>Alpha</name></item>
  <item id="b" state="draft"><name>Beta</name></item>
  <item id="c"><name>Gamma</name></item>
</catalog>
"""


def test_attribute_and_text_predicates_filter_the_supported_xpath_subset():
    root = ET.fromstring(XML_TEXT)

    assert [node.get("id") for node in root.findall("item[@state]")] == ["a", "b"]
    assert [node.get("id") for node in root.findall("item[@state='ready']")] == ["a"]
    assert [node.get("id") for node in root.findall("item[@state!='ready']")] == ["b"]
    assert [node.get("id") for node in root.findall("item[.='Beta']")] == ["b"]
    assert [node.get("id") for node in root.findall("item[.!='Beta']")] == ["a", "c"]
    assert [node.get("id") for node in root.findall("item[name='Gamma']")] == ["c"]


def test_position_predicates_are_one_based_and_relative_to_same_tag_siblings():
    root = ET.fromstring(XML_TEXT)

    assert root.find("item[1]").get("id") == "a"
    assert root.find("item[2]").get("id") == "b"
    assert root.find("item[last()]").get("id") == "c"
    assert root.find("item[last()-1]").get("id") == "b"


def test_element_paths_are_relative_and_unsupported_absolute_form_raises():
    root = ET.fromstring(XML_TEXT)
    with pytest.raises(SyntaxError):
        root.findall("/catalog/item")
