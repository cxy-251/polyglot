"""447｜DOM implementation 发现、注册、特性选择与 Document/DOCTYPE 创建。

``getDOMImplementation()`` 把调用方与具体 DOM 实现解耦，可按名字或 feature/version 对选择。
``registerDOMImplementation()`` 修改进程级注册表，因此测试应隔离。实现对象可先创建 doctype，
再一次创建带命名空间根节点的 Document；传入两个 ``None`` 也可创建暂时没有根元素的空文档。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.dom.getDOMImplementation
# polyglot-covers: python.xml.dom.registerDOMImplementation
# polyglot-covers: python.xml.dom.DOMImplementation.hasFeature
# polyglot-covers: python.xml.dom.DOMImplementation.createDocument
# polyglot-covers: python.xml.dom.DOMImplementation.createDocumentType
# polyglot-covers: python.xml.dom.Document.documentElement
# polyglot-covers: python.xml.dom.Document.doctype
# polyglot-covers: python.xml.dom.EMPTY_NAMESPACE
# polyglot-covers: python.xml.dom.XML_NAMESPACE
# polyglot-covers: python.xml.dom.XMLNS_NAMESPACE
# polyglot-covers: python.xml.dom.XHTML_NAMESPACE

import xml.dom.domreg as domreg
from xml.dom import EMPTY_NAMESPACE
from xml.dom import XHTML_NAMESPACE
from xml.dom import XMLNS_NAMESPACE
from xml.dom import XML_NAMESPACE
from xml.dom import getDOMImplementation
from xml.dom import registerDOMImplementation


def test_default_implementation_can_be_selected_by_supported_features():
    implementation = getDOMImplementation(features=(("core", "1.0"),))

    assert implementation.hasFeature("core", "1.0")
    assert implementation.hasFeature("xml", "1.0")


def test_named_registration_is_isolated_from_the_process_global_registry(monkeypatch):
    monkeypatch.setattr(domreg, "registered", domreg.registered.copy())
    implementation = getDOMImplementation()

    registerDOMImplementation("polyglot-demo", lambda: implementation)

    assert getDOMImplementation("polyglot-demo") is implementation


def test_implementation_builds_doctype_namespaced_root_and_empty_document():
    implementation = getDOMImplementation()
    doctype = implementation.createDocumentType(
        "c:catalog",
        "-//POLYGLOT//DTD CATALOG 1.0//EN",
        "catalog.dtd",
    )
    document = implementation.createDocument(
        "urn:catalog",
        "c:catalog",
        doctype,
    )

    assert document.documentElement.tagName == "c:catalog"
    assert document.documentElement.namespaceURI == "urn:catalog"
    assert document.documentElement.prefix == "c"
    assert document.documentElement.localName == "catalog"
    assert document.doctype is doctype
    assert doctype.name == "c:catalog"
    assert doctype.publicId == "-//POLYGLOT//DTD CATALOG 1.0//EN"
    assert doctype.systemId == "catalog.dtd"

    empty = implementation.createDocument(None, None, None)
    assert empty.documentElement is None


def test_dom_namespace_constants_distinguish_reserved_namespaces():
    assert EMPTY_NAMESPACE is None
    assert XML_NAMESPACE == "http://www.w3.org/XML/1998/namespace"
    assert XMLNS_NAMESPACE == "http://www.w3.org/2000/xmlns/"
    assert XHTML_NAMESPACE == "http://www.w3.org/1999/xhtml"
