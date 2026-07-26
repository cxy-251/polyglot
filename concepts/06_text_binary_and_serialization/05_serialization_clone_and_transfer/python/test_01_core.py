"""序列化、克隆与所有权转移。

共同问题：哪些值可以跨边界编码；对象图复制是否保留别名和循环；
自定义类型如何参与；反序列化是否安全。
"""

# polyglot-family: text_binary_and_serialization
# polyglot-concept: serialization_clone_and_transfer
# polyglot-related: languages/python/builtins/test_024_mapping_dict.py

import copy
import json

import pytest


def test_json_round_trip_preserves_data_model_not_python_types():
    value = {"items": [1, True, None]}
    encoded = json.dumps(value, sort_keys=True)

    assert json.loads(encoded) == value
    assert isinstance(encoded, str)


def test_json_rejects_cycles_and_unsupported_objects():
    cyclic = []
    cyclic.append(cyclic)

    with pytest.raises(ValueError):
        json.dumps(cyclic)
    with pytest.raises(TypeError):
        json.dumps({1, 2})


def test_default_and_object_hook_define_an_explicit_extension_boundary():
    class Point:
        def __init__(self, x):
            self.x = x

    encoded = json.dumps(Point(3), default=lambda point: {"type": "Point", "x": point.x})
    decoded = json.loads(encoded, object_hook=lambda value: Point(value["x"]))

    assert isinstance(decoded, Point)
    assert decoded.x == 3


def test_deepcopy_preserves_shared_graph_topology_and_cycles():
    child = []
    original = [child, child]
    child.append(original)

    cloned = copy.deepcopy(original)

    assert cloned[0] is cloned[1]
    assert cloned[0][0] is cloned

    # pickle 能恢复更丰富对象但可能执行代码；不可信数据应使用受限数据格式。
