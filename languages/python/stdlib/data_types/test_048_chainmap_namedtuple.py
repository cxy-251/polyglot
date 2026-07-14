"""048｜``ChainMap`` 多层映射视图与 ``namedtuple`` 轻量记录示例。

``ChainMap`` 保留底层 mapping 引用，查询跨层、默认写入只到第一层；它不是合并后的
dict 副本。``namedtuple`` 则生成真正的 tuple subclass，用字段名补充位置协议而不为
每个实例增加 ``__dict__``。

动态生成类的 pickle 依赖 ``module + typename`` 能在模块 globals 中重新找到同一类。
该边界在子进程验证，避免依赖 pytest 的测试模块导入名。当前文件尚未经过 pytest
验证。
"""

# polyglot-covers: python.collections.ChainMap python.chainmap.maps
# polyglot-covers: python.chainmap.lookup-precedence python.chainmap.first-map-writes
# polyglot-covers: python.chainmap.reference-view python.chainmap.iteration-order
# polyglot-covers: python.chainmap.new_child python.chainmap.parents
# polyglot-covers: python.chainmap.flatten-snapshot python.chainmap.merge
# polyglot-covers: python.chainmap.configuration-layers python.chainmap.deep-write
# polyglot-covers: python.collections.namedtuple python.namedtuple.factory
# polyglot-covers: python.namedtuple.tuple-protocol python.namedtuple.immutability
# polyglot-covers: python.namedtuple._make python.namedtuple._asdict
# polyglot-covers: python.namedtuple._replace python.namedtuple._fields
# polyglot-covers: python.namedtuple.defaults python.namedtuple.rename
# polyglot-covers: python.namedtuple.module-pickle python.namedtuple.subclass

import subprocess
import sys
from collections import ChainMap
from collections import namedtuple

import pytest


def test_empty_chainmap_still_contains_one_writable_mapping():
    """无参数时不会得到无层对象；自动创建的 root dict 可直接接收写入。"""

    scope = ChainMap()

    assert scope.maps == [{}]
    assert len(scope.maps) == 1

    scope["name"] = "root"
    assert scope.maps[0] == {"name": "root"}


def test_chainmap_lookup_uses_front_to_back_precedence():
    """命令行覆盖环境，环境覆盖默认值；未遮蔽 key 继续向后查找。"""

    command_line = {"color": "blue"}
    environment = {"user": "alice", "color": "green"}
    defaults = {"user": "guest", "color": "red", "debug": False}
    settings = ChainMap(command_line, environment, defaults)

    assert settings["color"] == "blue"
    assert settings["user"] == "alice"
    assert settings["debug"] is False
    assert "debug" in settings
    assert settings.maps == [command_line, environment, defaults]


def test_underlying_mapping_changes_are_visible_because_chainmap_keeps_references():
    """ChainMap 是 live view；外部更新不会像预先 dict.update 的 snapshot 那样隔离。"""

    local = {}
    defaults = {"timeout": 30}
    settings = ChainMap(local, defaults)

    defaults["timeout"] = 60
    defaults["retries"] = 3

    assert settings["timeout"] == 60
    assert settings["retries"] == 3

    local["timeout"] = 5
    assert settings["timeout"] == 5


def test_assignment_update_and_missing_setdefault_write_only_the_first_map():
    """查到父层不意味着写回父层；所有新赋值集中在最前 scope。"""

    local = {}
    parent = {"color": "red"}
    settings = ChainMap(local, parent)

    settings["color"] = "blue"
    settings.update(timeout=10)
    inserted = settings.setdefault("retries", 3)

    assert inserted == 3
    assert local == {"color": "blue", "timeout": 10, "retries": 3}
    assert parent == {"color": "red"}

    # 已在父层找到时，setdefault 返回现有值，不额外制造遮蔽 entry。
    second = ChainMap({}, {"language": "zh"})
    assert second.setdefault("language", "en") == "zh"
    assert second.maps[0] == {}


def test_delete_and_pop_do_not_reach_into_parent_maps():
    """默认 mutation 边界是第一层；父层同名 key 不会被深删。"""

    local = {"temporary": 1}
    parent = {"persistent": 2}
    settings = ChainMap(local, parent)

    del settings["temporary"]
    assert "temporary" not in local

    with pytest.raises(KeyError):
        del settings["persistent"]
    with pytest.raises(KeyError):
        settings.pop("persistent")

    assert parent == {"persistent": 2}
    assert settings["persistent"] == 2


def test_iteration_order_matches_updates_from_last_map_to_first_map():
    """lookup 从前向后，但 key iteration 模拟先复制最后层、再逐层 update。"""

    baseline = {"music": "bach", "art": "rembrandt"}
    adjustments = {"art": "van gogh", "opera": "carmen"}
    combined = ChainMap(adjustments, baseline)

    assert list(combined) == ["music", "art", "opera"]
    assert list(combined.items()) == [
        ("music", "bach"),
        ("art", "van gogh"),
        ("opera", "carmen"),
    ]

    expected = baseline.copy()
    expected.update(adjustments)
    assert dict(combined) == expected


def test_new_child_creates_an_independent_front_scope_over_shared_parents():
    """child 写入自己的 local map，查询仍复用 parent 的底层 mapping 引用。"""

    root = ChainMap({"name": "root", "theme": "light"})
    child = root.new_child()

    assert child.maps[1:] == root.maps
    assert child.maps[0] == {}
    assert child["theme"] == "light"

    child["theme"] = "dark"
    child["local_only"] = True

    assert child["theme"] == "dark"
    assert root["theme"] == "light"
    assert "local_only" not in root


def test_new_child_accepts_explicit_map_and_python_310_keyword_initializers():
    """3.10 kwargs 会更新传入的新 front map；该 mapping 仍按引用暴露。"""

    root = ChainMap({"root": True})
    local = {"request_id": "abc"}
    child = root.new_child(local, debug=True, retries=2)

    assert child.maps[0] is local
    assert local == {"request_id": "abc", "debug": True, "retries": 2}
    assert child["root"] is True

    keyword_only_child = root.new_child(user="ada")
    assert keyword_only_child.maps[0] == {"user": "ada"}


def test_parents_skips_the_first_scope_without_copying_remaining_maps():
    """parents 类似 nonlocal view；新 ChainMap 复用原链的第二层及以后。"""

    local = {"value": "local"}
    enclosing = {"value": "enclosing", "shared": 1}
    global_scope = {"value": "global", "fallback": 2}
    scope = ChainMap(local, enclosing, global_scope)
    parents = scope.parents

    assert parents.maps == [enclosing, global_scope]
    assert parents.maps[0] is enclosing
    assert parents["value"] == "enclosing"

    enclosing["shared"] = 10
    assert parents["shared"] == 10


def test_public_maps_list_can_reorder_lookup_precedence_explicitly():
    """maps 是唯一状态且可修改；调用方也因此要自行维护至少一层等不变量。"""

    first = {"mode": "first"}
    second = {"mode": "second"}
    scope = ChainMap(first, second)

    assert scope["mode"] == "first"

    scope.maps.reverse()
    assert scope["mode"] == "second"
    assert scope.maps == [second, first]


def test_flattening_to_dict_creates_a_snapshot_instead_of_a_live_view():
    """dict(chain) 固化当时的有效键值；后续底层变化只反映在 ChainMap。"""

    overrides = {"color": "blue"}
    defaults = {"color": "red", "size": "medium"}
    view = ChainMap(overrides, defaults)
    snapshot = dict(view)

    overrides["color"] = "green"
    defaults["size"] = "large"
    defaults["new"] = True

    assert view["color"] == "green"
    assert view["size"] == "large"
    assert view["new"] is True
    assert snapshot == {"color": "blue", "size": "medium"}


def test_chainmap_merge_returns_a_new_chain_and_inplace_merge_updates_front():
    """``|`` copy 第一层后更新，父 mappings 继续共享；``|=`` 直接写当前第一层。"""

    local = {"color": "blue"}
    defaults = {"color": "red", "size": "medium"}
    settings = ChainMap(local, defaults)
    merged = settings | {"color": "green", "debug": True}

    assert isinstance(merged, ChainMap)
    assert merged["color"] == "green"
    assert merged["debug"] is True
    assert settings["color"] == "blue"
    assert "debug" not in settings
    assert merged.maps[0] is not local
    assert merged.maps[1] is defaults

    settings |= {"color": "purple", "timeout": 5}
    assert local == {"color": "purple", "timeout": 5}
    assert settings["size"] == "medium"


def test_configuration_precedence_ignores_unspecified_command_line_values():
    """先过滤 None，避免“未提供的 CLI 值”错误遮蔽环境和默认配置。"""

    parsed_arguments = {"user": None, "color": "blue"}
    command_line = {
        key: value
        for key, value in parsed_arguments.items()
        if value is not None
    }
    environment = {"user": "from-env"}
    defaults = {"user": "guest", "color": "red", "debug": False}
    settings = ChainMap(command_line, environment, defaults)

    assert dict(settings) == {
        "user": "from-env",
        "color": "blue",
        "debug": False,
    }


def test_deep_chainmap_subclass_can_route_updates_to_the_first_existing_layer():
    """需要 deep-write 时必须显式改协议；新 key 仍放第一层。"""

    class DeepChainMap(ChainMap):
        def __setitem__(self, key, value):
            for mapping in self.maps:
                if key in mapping:
                    mapping[key] = value
                    return
            self.maps[0][key] = value

        def __delitem__(self, key):
            for mapping in self.maps:
                if key in mapping:
                    del mapping[key]
                    return
            raise KeyError(key)

    local = {"local": 1}
    parent = {"shared": 2, "remove": 3}
    scope = DeepChainMap(local, parent)

    scope["shared"] = 20
    scope["new"] = 4
    del scope["remove"]

    assert local == {"local": 1, "new": 4}
    assert parent == {"shared": 20}

    with pytest.raises(KeyError):
        del scope["missing"]


def test_namedtuple_accepts_string_or_iterable_fields_and_is_a_tuple_subclass():
    """字段串可用空白/逗号分隔；实例仍完整实现 tuple 位置协议。"""

    Point = namedtuple("Point", "x, y")
    Color = namedtuple("Color", ["red", "green", "blue"])
    point = Point(11, y=22)
    color = Color(128, 255, 0)

    assert issubclass(Point, tuple)
    assert isinstance(point, tuple)
    assert point == (11, 22)
    assert point[0] == point.x == 11
    assert point[1] == point.y == 22
    assert tuple(point) == (11, 22)
    assert color.green == 255

    x, y = point
    assert (x, y) == (11, 22)
    assert {point: "coordinate"}[Point(11, 22)] == "coordinate"


def test_namedtuple_repr_fields_and_instances_are_immutable_and_slot_based():
    """repr 用 name=value；字段和 tuple item 均不可赋值，实例没有 __dict__。"""

    Point = namedtuple("Point", "x y")
    point = Point(3, 4)

    assert repr(point) == "Point(x=3, y=4)"
    assert Point._fields == ("x", "y")
    assert not hasattr(point, "__dict__")

    with pytest.raises(AttributeError):
        point.x = 10
    with pytest.raises(TypeError):
        point[0] = 10


def test_make_constructs_from_iterable_and_validates_exact_arity():
    """_make 适合 CSV/数据库 row；字段数不匹配不会静默截断或补齐。"""

    Point = namedtuple("Point", "x y")

    assert Point._make(iter([5, 6])) == Point(5, 6)

    with pytest.raises(TypeError):
        Point._make([5])
    with pytest.raises(TypeError):
        Point._make([5, 6, 7])


def test_asdict_returns_a_regular_ordered_dict_in_python_310():
    """3.8+ _asdict 返回普通 dict；语言层 insertion order 已保存字段顺序。"""

    Point = namedtuple("Point", "x y")
    mapping = Point(7, 8)._asdict()

    assert type(mapping) is dict
    assert mapping == {"x": 7, "y": 8}
    assert list(mapping) == ["x", "y"]


def test_replace_returns_a_new_record_and_rejects_unknown_fields():
    """_replace 不修改原 tuple；Python 3.10 对未知字段抛 ValueError。"""

    Account = namedtuple("Account", "owner balance")
    original = Account("Ada", 10)
    updated = original._replace(balance=25)

    assert original == Account("Ada", 10)
    assert updated == Account("Ada", 25)
    assert updated is not original

    with pytest.raises(ValueError):
        original._replace(currency="USD")


def test_fields_can_compose_larger_record_types():
    """_fields 是稳定 introspection tuple，可复用而不手抄字段名。"""

    Point = namedtuple("Point", "x y")
    Color = namedtuple("Color", "red green blue")
    Pixel = namedtuple("Pixel", Point._fields + Color._fields)

    pixel = Pixel(11, 22, 128, 255, 0)

    assert Pixel._fields == ("x", "y", "red", "green", "blue")
    assert pixel.x == 11
    assert pixel.blue == 0


def test_defaults_apply_only_to_rightmost_fields_and_are_introspectable():
    """defaults 与函数 positional defaults 一样从最右字段对齐。"""

    Account = namedtuple(
        "Account",
        "kind balance currency",
        defaults=[0, "USD"],
    )

    assert Account._field_defaults == {"balance": 0, "currency": "USD"}
    assert Account("premium") == Account("premium", 0, "USD")
    assert Account("premium", 100) == Account("premium", 100, "USD")

    with pytest.raises(TypeError):
        Account()


def test_rename_replaces_keywords_duplicates_and_leading_underscore_fields():
    """rename=False 严格失败；rename=True 用 _位置 生成可用且唯一的字段。"""

    invalid_fields = ["class", "value", "value", "_hidden"]

    with pytest.raises(ValueError):
        namedtuple("Invalid", invalid_fields)

    Renamed = namedtuple("Renamed", invalid_fields, rename=True)
    value = Renamed(1, 2, 3, 4)

    assert Renamed._fields == ("_0", "value", "_2", "_3")
    assert (value._0, value.value, value._2, value._3) == (1, 2, 3, 4)


def test_module_parameter_and_global_typename_binding_control_pickle_lookup():
    """pickle 按 module.typename 找类；只改 __module__ 而没有同名全局绑定仍不够。"""

    program = r'''
import pickle
from collections import namedtuple

Record = namedtuple("Record", "identifier", module=__name__)
value = Record(7)
restored = pickle.loads(pickle.dumps(value))
assert restored == value
assert type(restored) is Record

Unbound = namedtuple("OtherRecord", "identifier", module=__name__)
try:
    pickle.dumps(Unbound(8))
except pickle.PicklingError:
    pass
else:
    raise AssertionError("OtherRecord is not bound in module globals")

print("isolated-namedtuple-pickle-ok")
'''
    completed = subprocess.run(
        [sys.executable, "-c", program],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == "isolated-namedtuple-pickle-ok"


def test_namedtuple_subclass_adds_computed_behavior_without_instance_dict():
    """subclass 设 __slots__=() 可增加 property/docstring，同时维持 tuple 存储模型。"""

    PointBase = namedtuple("PointBase", "x y")

    class Point(PointBase):
        __slots__ = ()

        @property
        def squared_distance(self):
            return self.x ** 2 + self.y ** 2

    Point.__doc__ = "二维不可变坐标"
    Point.x.__doc__ = "横坐标"
    point = Point(3, 4)

    assert point.squared_distance == 25
    assert Point.__doc__ == "二维不可变坐标"
    assert Point.x.__doc__ == "横坐标"
    assert not hasattr(point, "__dict__")
