"""126｜xmlrpc.client.dumps/loads 的请求包、核心类型映射、自定义对象与格式限制。

XML-RPC 只支持一小组类型：tuple/list 在线路上都成为 array，返回时统一为 list；对象仅
发送 __dict__。整数限定 32 位，dict 键必须是字符串，内置类型的子类也不会自动降级。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.xmlrpc.client.dumps
# polyglot-covers: python.xmlrpc.client.loads
# polyglot-covers: python.xmlrpc.client.dumps-methodname
# polyglot-covers: python.xmlrpc.client.loads-params-methodname-pair
# polyglot-covers: python.xmlrpc.client.boolean-int-double-string
# polyglot-covers: python.xmlrpc.client.array-tuple-marshals-list-unmarshals
# polyglot-covers: python.xmlrpc.client.struct-string-keys
# polyglot-covers: python.xmlrpc.client.user-object-transmits-dunder-dict
# polyglot-covers: python.xmlrpc.client.xml-special-character-escaping
# polyglot-covers: python.xmlrpc.client.xml-forbidden-control-character-trap
# polyglot-covers: python.xmlrpc.client.integer-32-bit-range
# polyglot-covers: python.xmlrpc.client.builtin-subclass-not-marshaled

import base64
from datetime import datetime
from decimal import Decimal
from io import StringIO
from xml.parsers.expat import ExpatError
from xmlrpc.client import (
    Binary,
    DateTime,
    Error,
    Fault,
    MultiCall,
    ProtocolError,
    SafeTransport,
    Server,
    ServerProxy,
    Transport,
    dumps,
    loads,
)

import pytest


class LessonRecord:
    def __init__(self):
        self.topic = "XML-RPC"
        self.level = 3


class TextSubclass(str):
    pass


def test_request_round_trip_exposes_method_and_normalizes_arrays_to_lists():
    xml = dumps(
        (
            True,
            42,
            2.5,
            "<tag> & text",
            (1, 2),
            {"name": "lesson"},
        ),
        methodname="study.echo",
    )

    params, method = loads(xml)

    assert method == "study.echo"
    assert params == (
        True,
        42,
        2.5,
        "<tag> & text",
        [1, 2],
        {"name": "lesson"},
    )
    assert "&lt;tag&gt; &amp; text" in xml
    assert "<boolean>1</boolean>" in xml


def test_user_object_is_marshaled_as_its_instance_dictionary():
    xml = dumps((LessonRecord(),), methodname="lesson.save")

    params, _ = loads(xml)

    assert params == ({"topic": "XML-RPC", "level": 3},)


def test_type_boundaries_raise_before_a_request_can_be_sent():
    with pytest.raises(OverflowError):
        dumps((2**31,))

    with pytest.raises(TypeError):
        dumps(({1: "non-string key"},))

    with pytest.raises(TypeError):
        dumps((TextSubclass("looks like text"),))


def test_forbidden_xml_control_character_is_not_made_safe_by_xml_escaping():
    xml = dumps(("bad\x01value",), methodname="study.echo")

    # 转义器处理 <、>、&，但 XML 规范禁止的控制字符仍会生成无法解析的文档。
    with pytest.raises(ExpatError):
        loads(xml)


# XML-RPC 的 nil 扩展、base64、日期时间、use_builtin_types 与 Decimal 解码。
#
# 默认解码返回 Binary/DateTime 包装器；use_builtin_types=True 才返回 bytes/datetime。
# None 不是基础规范的一部分，发送端必须显式 allow_none。bigdecimal 只支持从响应解码。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.xmlrpc.client.dumps-allow_none
# polyglot-covers: python.xmlrpc.client.nil-extension
# polyglot-covers: python.xmlrpc.client.none-default-typeerror
# polyglot-covers: python.xmlrpc.client.bytes-base64-marshalling
# polyglot-covers: python.xmlrpc.client.bytearray-base64-marshalling
# polyglot-covers: python.xmlrpc.client.datetime-marshalling
# polyglot-covers: python.xmlrpc.client.loads-use_builtin_types-3.3
# polyglot-covers: python.xmlrpc.client.loads-default-Binary-DateTime
# polyglot-covers: python.xmlrpc.client.loads-builtin-bytes-datetime
# polyglot-covers: python.xmlrpc.client.bigdecimal-decimal-unmarshal
# polyglot-covers: python.xmlrpc.client.prefixed-nil-tag-3.6


def test_none_requires_opt_in_but_round_trips_when_extension_is_enabled():
    with pytest.raises(TypeError):
        dumps((None,))

    xml = dumps((None,), allow_none=True)

    assert "<nil/>" in xml
    assert loads(xml) == ((None,), None)


def test_default_and_builtin_decoders_choose_wrapper_or_native_types():
    moment = datetime(2024, 1, 2, 3, 4, 5)
    xml = dumps((b"\x00binary\xff", bytearray(b"mutable"), moment))

    wrapped, _ = loads(xml)
    native, _ = loads(xml, use_builtin_types=True)

    assert isinstance(wrapped[0], Binary)
    assert isinstance(wrapped[1], Binary)
    assert isinstance(wrapped[2], DateTime)
    assert wrapped[0].data == b"\x00binary\xff"
    assert native == (b"\x00binary\xff", b"mutable", moment)


def test_additional_numeric_and_prefixed_nil_tags_are_unmarshaled():
    response = """<?xml version='1.0'?>
    <methodResponse><params>
      <param><value><bigdecimal>12.50</bigdecimal></value></param>
      <param><value><ex:nil xmlns:ex='urn:xmlrpc'/></value></param>
    </params></methodResponse>
    """

    params, method = loads(response)

    assert params == (Decimal("12.50"), None)
    assert method is None


# DateTime/Binary 包装器的构造、编码钩子、解码、比较与原始数据访问。
#
# 包装器是默认反序列化结果，也可显式传给 dumps。DateTime 保存无时区 ISO 字符串；
# Binary.data 始终是 bytes，并用带换行的 MIME base64 写入 XML，不能用普通字符串代替。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.xmlrpc.client.DateTime
# polyglot-covers: python.xmlrpc.client.DateTime-from-datetime
# polyglot-covers: python.xmlrpc.client.DateTime.value
# polyglot-covers: python.xmlrpc.client.DateTime.decode
# polyglot-covers: python.xmlrpc.client.DateTime.encode
# polyglot-covers: python.xmlrpc.client.DateTime-rich-comparison
# polyglot-covers: python.xmlrpc.client.Binary
# polyglot-covers: python.xmlrpc.client.Binary.data
# polyglot-covers: python.xmlrpc.client.Binary.decode
# polyglot-covers: python.xmlrpc.client.Binary.encode
# polyglot-covers: python.xmlrpc.client.Binary-base64-line-wrapping
# polyglot-covers: python.xmlrpc.client.Binary-equality


def test_datetime_accepts_datetime_and_supports_iso_order_comparison():
    earlier_native = datetime(2024, 1, 2, 3, 4, 5)
    earlier = DateTime(earlier_native)
    later = DateTime("20240102T03:04:06")

    assert earlier.value == "20240102T03:04:05"
    assert str(earlier) == earlier.value
    assert earlier < later
    assert earlier == earlier_native

    later.decode("20240102T03:04:07")
    output = StringIO()
    later.encode(output)

    assert later.value == "20240102T03:04:07"
    assert "<dateTime.iso8601>20240102T03:04:07" in output.getvalue()


def test_binary_decode_and_encode_preserve_null_bytes_and_wrap_base64_lines():
    data = bytes(range(64)) + b"\x00\xff" + bytes(range(64))
    binary = Binary(data)
    output = StringIO()

    binary.encode(output)

    encoded = output.getvalue()
    payload_lines = [
        line
        for line in encoded.splitlines()
        if line and not line.startswith("<")
    ]
    assert binary.data == data
    assert binary == Binary(data)
    assert binary == data
    assert all(len(line) <= 76 for line in payload_lines)

    replacement = Binary()
    replacement.decode(b"cmVwbGFjZW1lbnQ=\n")
    assert replacement.data == b"replacement"


# XML-RPC Fault 与 HTTP ProtocolError 的分层、字段、字符串和故障包往返。
#
# Fault 表示 HTTP 成功响应内的远程调用失败，loads 会直接抛出它；ProtocolError 表示
# HTTP 传输层状态失败。二者都继承 Error，但恢复策略和可观察字段完全不同。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.xmlrpc.client.Error
# polyglot-covers: python.xmlrpc.client.Fault
# polyglot-covers: python.xmlrpc.client.Fault.faultCode
# polyglot-covers: python.xmlrpc.client.Fault.faultString
# polyglot-covers: python.xmlrpc.client.dumps-Fault-response
# polyglot-covers: python.xmlrpc.client.loads-raises-Fault
# polyglot-covers: python.xmlrpc.client.ProtocolError
# polyglot-covers: python.xmlrpc.client.ProtocolError.url
# polyglot-covers: python.xmlrpc.client.ProtocolError.errcode
# polyglot-covers: python.xmlrpc.client.ProtocolError.errmsg
# polyglot-covers: python.xmlrpc.client.ProtocolError.headers


def test_fault_marshals_as_method_response_and_loads_raises_it():
    fault = Fault(42, "calculation failed")

    xml = dumps(fault)

    assert isinstance(fault, Error)
    assert isinstance(fault, Exception)
    assert fault.faultCode == 42
    assert fault.faultString == "calculation failed"
    assert "<fault>" in xml
    assert "calculation failed" in xml

    with pytest.raises(Fault) as raised:
        loads(xml)

    assert raised.value.faultCode == 42
    assert raised.value.faultString == "calculation failed"


def test_protocol_error_keeps_transport_metadata_separate_from_rpc_fault():
    headers = {"Retry-After": "30", "Content-Type": "text/plain"}
    error = ProtocolError(
        "https://example.test/RPC2",
        503,
        "Service Unavailable",
        headers,
    )

    assert isinstance(error, Error)
    assert not isinstance(error, Fault)
    assert error.url == "https://example.test/RPC2"
    assert error.errcode == 503
    assert error.errmsg == "Service Unavailable"
    assert error.headers is headers
    assert "503 Service Unavailable" in str(error)


# ServerProxy 的动态点分方法、单值解包、自定义 Transport、认证与上下文关闭。
#
# 属性访问只构造远程方法名，调用时才由 transport.request 发送 XML。响应仅含一个值时代理
# 自动解包。URI userinfo 会生成 Basic 头；with 退出关闭复用连接，而不是关闭远程服务。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.xmlrpc.client.ServerProxy
# polyglot-covers: python.xmlrpc.client.Server-alias
# polyglot-covers: python.xmlrpc.client.ServerProxy-dynamic-method
# polyglot-covers: python.xmlrpc.client.ServerProxy-dotted-method-name
# polyglot-covers: python.xmlrpc.client.ServerProxy-single-result-unwrapping
# polyglot-covers: python.xmlrpc.client.ServerProxy-custom-transport
# polyglot-covers: python.xmlrpc.client.ServerProxy-context-manager-3.5
# polyglot-covers: python.xmlrpc.client.ServerProxy-unsupported-scheme
# polyglot-covers: python.xmlrpc.client.Transport.get_host_info-basic-auth
# polyglot-covers: python.xmlrpc.client.Transport-percent-decoded-userinfo
# polyglot-covers: python.xmlrpc.client.ServerProxy-http-vs-https-transport


class MemoryTransport:
    def __init__(self):
        self.calls = []
        self.closed = False

    def request(self, host, handler, request_body, verbose=False):
        params, method = loads(request_body)
        self.calls.append((host, handler, method, params, verbose))
        return (sum(params),)

    def close(self):
        self.closed = True


def test_dynamic_dotted_call_uses_transport_and_unwraps_one_response_value():
    transport = MemoryTransport()

    with ServerProxy(
        "http://example.test/RPC2",
        transport=transport,
    ) as proxy:
        result = proxy.math.add(2, 3)

    assert result == 5
    assert transport.calls == [
        ("example.test", "/RPC2", "math.add", (2, 3), False),
    ]
    assert transport.closed
    assert Server is ServerProxy


def test_proxy_selects_transport_by_scheme_and_rejects_unrelated_protocols():
    http_proxy = ServerProxy("http://example.test/RPC2")
    https_proxy = ServerProxy("https://example.test/RPC2")

    assert isinstance(http_proxy("transport"), Transport)
    assert isinstance(https_proxy("transport"), SafeTransport)

    with pytest.raises(OSError):
        ServerProxy("ftp://example.test/RPC2")


def test_transport_extracts_and_decodes_basic_auth_userinfo_from_host():
    transport = Transport()

    host, headers, x509 = transport.get_host_info(
        "user%40example:p%20ass@example.test:8080",
    )

    expected = base64.encodebytes(b"user@example:p ass").decode().strip()
    assert host == "example.test:8080"
    assert dict(headers)["Authorization"] == f"Basic {expected}"
    assert x509 == {}


# MultiCall 的延迟收集、点分方法、system.multicall 批量包与逐项 Fault。
#
# 调用 multicall.foo(...) 只记录描述并返回 None；真正调用 MultiCall 对象才发送一个请求。
# 结果项必须是单元素列表或 fault dict，Fault 在访问对应项时抛出，不会抹掉之前的成功值。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.xmlrpc.client.MultiCall
# polyglot-covers: python.xmlrpc.client.MultiCall-delayed-recording
# polyglot-covers: python.xmlrpc.client.MultiCall-dotted-method-name
# polyglot-covers: python.xmlrpc.client.MultiCall-system.multicall
# polyglot-covers: python.xmlrpc.client.MultiCallIterator
# polyglot-covers: python.xmlrpc.client.multicall-singleton-list-unwrapping
# polyglot-covers: python.xmlrpc.client.multicall-per-item-fault
# polyglot-covers: python.xmlrpc.client.multicall-invalid-result-valueerror


class MemorySystem:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def multicall(self, calls):
        self.calls.append(calls)
        return self.results


class MemoryServer:
    def __init__(self, results):
        self.system = MemorySystem(results)


def test_calls_are_recorded_then_sent_together_with_dotted_names():
    server = MemoryServer(
        [
            [5],
            [12],
            {"faultCode": 17, "faultString": "division failed"},
        ],
    )
    batch = MultiCall(server)

    assert batch.math.add(2, 3) is None
    assert batch.math.multiply(3, 4) is None
    assert batch.math.divide(1, 0) is None
    assert server.system.calls == []

    results = batch()

    assert server.system.calls == [
        [
            {"methodName": "math.add", "params": (2, 3)},
            {"methodName": "math.multiply", "params": (3, 4)},
            {"methodName": "math.divide", "params": (1, 0)},
        ],
    ]
    assert results[0] == 5
    assert results[1] == 12
    with pytest.raises(Fault) as raised:
        results[2]
    assert raised.value.faultCode == 17


def test_non_list_non_fault_result_is_rejected_when_accessed():
    batch = MultiCall(MemoryServer(["invalid shape"]))
    batch.anything()

    results = batch()

    with pytest.raises(ValueError):
        results[0]
