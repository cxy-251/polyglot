"""467｜XMLFilterBase 在 XMLReader 与下游 handler 之间转换事件。

filter 的配置请求向上转发给 parent reader，parent 产生的事件再经 filter 向下游转发。基类默认
透明透传；子类只覆盖关心的回调即可实现重命名、内容清洗或审计。filter 仍是流式模型，不能在
startElement 中向后查看尚未出现的内容；需要随机访问时应改用 DOM/ElementTree。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.sax.saxutils.XMLFilterBase
# polyglot-covers: python.xml.sax.saxutils.XMLFilterBase.parse
# polyglot-covers: python.xml.sax.saxutils.XMLFilterBase-handler-forwarding
# polyglot-covers: python.xml.sax.saxutils.XMLFilterBase-feature-forwarding
# polyglot-covers: python.xml.sax.saxutils.XMLFilterBase-transform-event-stream

import io
import xml.sax
from xml.sax import handler
from xml.sax import saxutils


class RenamingUppercaseFilter(saxutils.XMLFilterBase):
    def startElement(self, name, attrs):
        renamed = "entry" if name == "item" else name
        super().startElement(renamed, attrs)

    def endElement(self, name):
        renamed = "entry" if name == "item" else name
        super().endElement(renamed)

    def characters(self, content):
        super().characters(content.upper())


def test_filter_forwards_configuration_and_transforms_events_before_generation():
    reader = xml.sax.make_parser()
    filter_ = RenamingUppercaseFilter(reader)
    output = io.StringIO()
    generator = saxutils.XMLGenerator(output, encoding="utf-8")
    filter_.setContentHandler(generator)
    filter_.setFeature(handler.feature_namespaces, False)

    assert filter_.getContentHandler() is generator
    assert not filter_.getFeature(handler.feature_namespaces)

    filter_.parse(io.StringIO("<root><item>value</item></root>"))

    assert "<root><entry>VALUE</entry></root>" in output.getvalue()
