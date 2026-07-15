"""472｜ExpatError 的错误码/行列、parser 错误属性与 errors 双向表。

ExpatError 同时给出 ``code``、1-based ``lineno`` 和 0-based ``offset``。parser 上 ErrorCode/
ErrorLineNumber/ErrorColumnNumber/ErrorByteIndex 只在 Parse/ParseFile 抛错后有意义。errors 常量
的值是消息字符串，不是数字；应经 ``errors.codes[constant]`` 比较，再用 messages/ErrorString 展示。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.parsers.expat.ExpatError
# polyglot-covers: python.xml.parsers.expat.error
# polyglot-covers: python.xml.parsers.expat.ExpatError.code
# polyglot-covers: python.xml.parsers.expat.ExpatError.lineno
# polyglot-covers: python.xml.parsers.expat.ExpatError.offset
# polyglot-covers: python.xml.parsers.expat.xmlparser.ErrorCode
# polyglot-covers: python.xml.parsers.expat.xmlparser.ErrorLineNumber
# polyglot-covers: python.xml.parsers.expat.xmlparser.ErrorColumnNumber
# polyglot-covers: python.xml.parsers.expat.xmlparser.ErrorByteIndex
# polyglot-covers: python.xml.parsers.expat.ErrorString
# polyglot-covers: python.xml.parsers.expat.errors.codes
# polyglot-covers: python.xml.parsers.expat.errors.messages

from xml.parsers import expat

import pytest


def test_parse_error_matches_symbolic_code_and_all_location_views():
    parser = expat.ParserCreate()

    with pytest.raises(expat.ExpatError) as caught:
        parser.Parse("<root>\n<item></root>", True)

    error = caught.value
    expected_code = expat.errors.codes[expat.errors.XML_ERROR_TAG_MISMATCH]
    assert expat.error is expat.ExpatError
    assert error.code == parser.ErrorCode == expected_code
    assert error.lineno == parser.ErrorLineNumber == 2
    assert error.offset == parser.ErrorColumnNumber >= 0
    assert parser.ErrorByteIndex >= 0
    assert expat.ErrorString(error.code) == expat.errors.messages[error.code]
    assert expat.errors.XML_ERROR_TAG_MISMATCH == "mismatched tag"
