"""049｜可继承容器包装器 ``UserDict``、``UserList`` 与 ``UserString``。

三者都把真实内置容器放在公开的 ``data`` 属性中，再用 Python 方法实现相应协议。
这让 subclass hook 比直接继承 C 实现的内置容器更容易控制，但 ``data`` 不是只读
或自动受保护的存储。直接修改它，以及少数直接委托给它的复合操作，
仍可能绕开 hook。

本文件锁定 CPython/Python 3.10 的返回类型与构造器约定，尚未经过 pytest 验证。
"""

# polyglot-covers: python.collections.UserDict python.userdict.data
# polyglot-covers: python.userdict.copy python.userdict.missing
# polyglot-covers: python.userdict.update-hooks python.userdict.fromkeys
# polyglot-covers: python.userdict.merge python.userdict.builtin-subclass-contrast
# polyglot-covers: python.collections.UserList python.userlist.data
# polyglot-covers: python.userlist.sequence-protocol python.userlist.mutation
# polyglot-covers: python.userlist.result-type python.userlist.constructor-contract
# polyglot-covers: python.userlist.validation-hooks python.userlist.direct-data-bypass
# polyglot-covers: python.collections.UserString python.userstring.data
# polyglot-covers: python.userstring.sequence-protocol python.userstring.operations
# polyglot-covers: python.userstring.method-result-types python.userstring.rebinding
# polyglot-covers: python.userstring.subclass python.userstring.str-subclass-contrast

import copy
from collections import UserDict
from collections import UserList
from collections import UserString

import pytest


def test_userdict_copies_the_outer_mapping_but_keeps_nested_values_shallow():
    """initialdata 不按引用保存；这只是浅复制，嵌套可变值仍由两边共享。"""

    shared_tags = ["stable"]
    source = {"theme": "dark", "tags": shared_tags}
    settings = UserDict(source, retries=3)

    assert type(settings.data) is dict
    assert settings.data == {
        "theme": "dark",
        "tags": ["stable"],
        "retries": 3,
    }
    assert settings["tags"] is shared_tags

    source["theme"] = "light"
    source["new"] = True
    settings["timeout"] = 10

    assert settings["theme"] == "dark"
    assert "new" not in settings
    assert "timeout" not in source

    shared_tags.append("shared")
    assert settings["tags"] == ["stable", "shared"]


def test_userdict_exposes_the_normal_mapping_protocol_and_plain_dict_equality():
    """包装器不是 dict subclass，但 len/iter/items/equality 等 Mapping 协议照常工作。"""

    record = UserDict([("name", "Ada"), ("language", "Python")])

    assert not isinstance(record, dict)
    assert len(record) == 2
    assert list(record) == ["name", "language"]
    assert list(record.items()) == [
        ("name", "Ada"),
        ("language", "Python"),
    ]
    assert record == {"name": "Ada", "language": "Python"}
    assert dict(record) == {"name": "Ada", "language": "Python"}


def test_userdict_missing_hook_affects_lookup_but_not_membership_or_storage():
    """__getitem__ 会找 __missing__；__contains__ 故意只看 data，避免 fallback 假装存在。"""

    class TemplateVariables(UserDict):
        def __missing__(self, key):
            return f"<{key}:unset>"

    variables = TemplateVariables({"name": "Ada"})

    assert variables["name"] == "Ada"
    assert variables["region"] == "<region:unset>"
    # Mapping.get() 也通过 __getitem__，所以能观察到同一个 fallback。
    assert variables.get("region") == "<region:unset>"
    assert "region" not in variables
    assert "region" not in variables.data


def test_userdict_initialization_update_and_fromkeys_use_setitem_hook():
    """MutableMapping 提供的写入算法逐项调用 self[key]，因此 subclass 可集中审计。"""

    class AuditedMapping(UserDict):
        def __init__(self, *args, **kwargs):
            self.writes = []
            super().__init__(*args, **kwargs)

        def __setitem__(self, key, value):
            self.writes.append((key, value))
            super().__setitem__(key, value)

    audited = AuditedMapping({"first": 1}, second=2)
    audited.update([("third", 3)])

    assert audited.writes == [
        ("first", 1),
        ("second", 2),
        ("third", 3),
    ]
    assert audited.data == {"first": 1, "second": 2, "third": 3}

    defaults = AuditedMapping.fromkeys(["foreground", "background"], "auto")
    assert isinstance(defaults, AuditedMapping)
    assert defaults.writes == [
        ("foreground", "auto"),
        ("background", "auto"),
    ]


def test_userdict_copy_is_shallow_and_preserves_subclass_instance_state():
    """copy() 创建独立 data dict；其他属性和嵌套 value 仍遵循普通浅复制语义。"""

    class TaggedMapping(UserDict):
        def __init__(self, *args, tag="default", **kwargs):
            self.tag = tag
            super().__init__(*args, **kwargs)

    nested = []
    original = TaggedMapping({"items": nested}, tag="request")
    method_copy = original.copy()
    protocol_copy = copy.copy(original)

    for copied in (method_copy, protocol_copy):
        assert isinstance(copied, TaggedMapping)
        assert copied is not original
        assert copied.data is not original.data
        assert copied["items"] is nested
        assert copied.tag == "request"

    method_copy["new"] = True
    assert "new" not in original


def test_userdict_merge_result_and_inplace_merge_have_different_hook_paths():
    """``|`` 构造新对象，``|=`` 则在 3.10 直接合并 data，可能绕过 __setitem__。"""

    class AuditedMapping(UserDict):
        def __init__(self, *args, **kwargs):
            self.writes = []
            super().__init__(*args, **kwargs)

        def __setitem__(self, key, value):
            self.writes.append((key, value))
            super().__setitem__(key, value)

    left = AuditedMapping({"left": 1})
    merged = left | {"right": 2}
    reverse_merged = {"zero": 0} | left

    assert isinstance(merged, AuditedMapping)
    assert merged.data == {"left": 1, "right": 2}
    assert merged.writes == [("left", 1), ("right", 2)]
    assert isinstance(reverse_merged, AuditedMapping)
    assert reverse_merged.data == {"zero": 0, "left": 1}

    left.writes.clear()
    identity = id(left)
    left |= {"inplace": 3}

    assert id(left) == identity
    assert left["inplace"] == 3
    # UserDict.__ior__ 使用 self.data |= other，并不逐项走 override。
    assert left.writes == []


def test_userdict_data_and_builtin_dict_methods_can_bypass_python_hooks():
    """包装器让常规 update 可拦截；直接 data 和 C 实现 dict.update 都不是该路径。"""

    class RecordingUserDict(UserDict):
        def __init__(self):
            self.writes = []
            super().__init__()

        def __setitem__(self, key, value):
            self.writes.append((key, value))
            super().__setitem__(key, value)

    class RecordingDict(dict):
        def __init__(self):
            self.writes = []
            super().__init__()

        def __setitem__(self, key, value):
            self.writes.append((key, value))
            super().__setitem__(key, value)

    wrapped = RecordingUserDict()
    wrapped.update({"through-wrapper": 1})
    wrapped.data["direct"] = 2

    builtin_subclass = RecordingDict()
    builtin_subclass["explicit"] = 1
    builtin_subclass.update({"through-c-update": 2})

    assert wrapped.writes == [("through-wrapper", 1)]
    assert wrapped.data == {"through-wrapper": 1, "direct": 2}
    assert builtin_subclass.writes == [("explicit", 1)]
    assert builtin_subclass == {"explicit": 1, "through-c-update": 2}


def test_userdict_subclass_can_normalize_a_real_mapping_workflow():
    """大小写无关 header 同时规范化读写入口，底层 data 始终保存统一 key。"""

    class Headers(UserDict):
        @staticmethod
        def _key(value):
            if not isinstance(value, str):
                raise TypeError("header name must be str")
            return value.casefold()

        def __getitem__(self, key):
            return super().__getitem__(self._key(key))

        def __setitem__(self, key, value):
            super().__setitem__(self._key(key), str(value))

        def __delitem__(self, key):
            super().__delitem__(self._key(key))

        def __contains__(self, key):
            return super().__contains__(self._key(key))

    headers = Headers({"Content-Type": "text/plain"})
    headers.update({"ACCEPT": "application/json"})

    assert headers.data == {
        "content-type": "text/plain",
        "accept": "application/json",
    }
    assert headers["CONTENT-TYPE"] == "text/plain"
    assert "Accept" in headers

    del headers["aCcEpT"]
    assert "accept" not in headers.data

    with pytest.raises(TypeError, match="header name"):
        headers[42] = "invalid"


def test_userlist_copies_the_outer_iterable_and_keeps_nested_values_shallow():
    """与 list() 一样产生独立外层存储；其中已有的对象不会递归复制。"""

    nested = ["shared"]
    source = [nested, "tail"]
    values = UserList(source)

    assert type(values.data) is list
    assert values.data is not source
    assert values[0] is nested

    source.append("source-only")
    values.append("wrapper-only")
    nested.append("changed")

    assert values == [["shared", "changed"], "tail", "wrapper-only"]
    assert source == [["shared", "changed"], "tail", "source-only"]

    generated = UserList(number * 2 for number in range(3))
    assert generated.data == [0, 2, 4]


def test_userlist_scalar_index_returns_value_but_slice_returns_actual_class():
    """单元素索引透出原值；slice 用 self.__class__(sequence) 构造同类新对象。"""

    class Tokens(UserList):
        pass

    tokens = Tokens(["zero", "one", "two", "three"])
    middle = tokens[1:3]
    reversed_tokens = tokens[::-1]

    assert tokens[0] == "zero"
    assert type(tokens[0]) is str
    assert isinstance(middle, Tokens)
    assert middle == ["one", "two"]
    assert isinstance(reversed_tokens, Tokens)
    assert reversed_tokens == ["three", "two", "one", "zero"]
    assert middle.data is not tokens.data


def test_userlist_mutation_methods_follow_list_return_value_conventions():
    """append/insert/extend/reverse/sort 原地返回 None；pop 返回被移除的元素。"""

    values = UserList([3, 1, 2])

    assert values.append(4) is None
    assert values.insert(0, 0) is None
    assert values.extend(UserList([5, 6])) is None
    assert values == [0, 3, 1, 2, 4, 5, 6]

    assert values.pop() == 6
    assert values.remove(3) is None
    assert values.reverse() is None
    assert values == [5, 4, 2, 1, 0]
    assert values.sort() is None
    assert values == [0, 1, 2, 4, 5]


def test_userlist_arithmetic_preserves_class_and_inplace_identity():
    """``+``/``*`` 返回实际 class；``+=``/``*=`` 改 data 并返回原包装器。"""

    class Tokens(UserList):
        pass

    tokens = Tokens(["a", "b"])

    added = tokens + ("c",)
    reverse_added = ["start"] + tokens
    repeated = tokens * 2

    assert isinstance(added, Tokens)
    assert added == ["a", "b", "c"]
    assert isinstance(reverse_added, Tokens)
    assert reverse_added == ["start", "a", "b"]
    assert isinstance(repeated, Tokens)
    assert repeated == ["a", "b", "a", "b"]

    identity = id(tokens)
    tokens += UserList(["c"])
    tokens *= 2

    assert id(tokens) == identity
    assert tokens == ["a", "b", "c", "a", "b", "c"]


def test_userlist_copy_is_shallow_and_preserves_actual_class():
    """copy() 与 copy.copy() 都复制外层 list，并保留 subclass 和嵌套对象引用。"""

    class Rows(UserList):
        pass

    row = {"id": 1}
    original = Rows([row])
    method_copy = original.copy()
    protocol_copy = copy.copy(original)

    for copied in (method_copy, protocol_copy):
        assert isinstance(copied, Rows)
        assert copied.data is not original.data
        assert copied[0] is row

    method_copy.append({"id": 2})
    assert original == [{"id": 1}]


def test_userlist_result_operations_require_a_zero_or_one_argument_constructor():
    """slice/add/multiply 只传一个 sequence；额外必需参数会使结果构造失败。"""

    class LabeledValues(UserList):
        def __init__(self, label, values):
            self.label = label
            super().__init__(values)

    values = LabeledValues("scores", [10, 20, 30])
    assert values[0] == 10

    with pytest.raises(TypeError):
        values[1:]
    with pytest.raises(TypeError):
        values + [40]
    with pytest.raises(TypeError):
        values * 2


def test_userlist_validation_must_cover_each_inherited_mutation_surface():
    """只重写 __setitem__ 不够；append/extend/insert/+= 在 UserList 中直接操作 data。"""

    class Scores(UserList):
        @staticmethod
        def _validate(value):
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError("score must be an integer")
            if not 0 <= value <= 100:
                raise ValueError("score must be between 0 and 100")

        @classmethod
        def _materialize(cls, values):
            materialized = list(values)
            for value in materialized:
                cls._validate(value)
            return materialized

        def __init__(self, values=None):
            checked = [] if values is None else self._materialize(values)
            super().__init__(checked)

        def __setitem__(self, index, value):
            if isinstance(index, slice):
                value = self._materialize(value)
            else:
                self._validate(value)
            super().__setitem__(index, value)

        def append(self, value):
            self._validate(value)
            super().append(value)

        def insert(self, index, value):
            self._validate(value)
            super().insert(index, value)

        def extend(self, values):
            super().extend(self._materialize(values))

        def __iadd__(self, values):
            self.extend(values)
            return self

    scores = Scores([80, 90])
    scores.append(100)
    scores.insert(0, 70)
    scores[1:2] = [75, 85]
    scores += (95,)

    assert scores == [70, 75, 85, 90, 100, 95]

    with pytest.raises(TypeError, match="integer"):
        scores.extend([88, "invalid"])
    with pytest.raises(ValueError, match="between"):
        scores[0] = 101
    # extend 先完整校验临时 list，失败不会留下半写入结果。
    assert scores == [70, 75, 85, 90, 100, 95]

    # data 是逃生口，不会自动执行上面的领域校验。
    scores.data.append("unchecked")
    assert scores[-1] == "unchecked"


def test_userstring_wraps_a_real_str_and_accepts_any_str_convertible_input():
    """UserString 不是 str subclass；构造时把 seq 转成普通 str 存入公开 data。"""

    text = UserString("Python")
    number = UserString(310)
    copied = UserString(text)

    assert not isinstance(text, str)
    assert type(text.data) is str
    assert str(text) == "Python"
    assert repr(text) == "'Python'"
    assert number.data == "310"
    assert copied.data == "Python"
    assert copied is not text


def test_userstring_sequence_protocol_preserves_wrapper_for_index_and_slice():
    """与 str 不同，单字符索引也调用 self.__class__，iteration 因而产生 wrapper。"""

    class Label(UserString):
        pass

    label = Label("atlas")
    first = label[0]
    tail = label[1:]
    iterated = list(label)

    assert isinstance(first, Label)
    assert first == "a"
    assert isinstance(tail, Label)
    assert tail == "tlas"
    assert all(isinstance(character, Label) for character in iterated)
    assert iterated == ["a", "t", "l", "a", "s"]
    assert len(label) == 5
    assert UserString("tla") in label


def test_userstring_comparison_hash_and_numeric_conversion_delegate_to_data():
    """比较可跨 raw str；hash 与当前 data 一致，数字转换复用 str 的解析规则。"""

    key = UserString("python")

    assert key == "python"
    assert key == UserString("python")
    assert key < "rust"
    assert hash(key) == hash("python")
    assert {key: "language"}[UserString("python")] == "language"

    assert int(UserString("42")) == 42
    assert float(UserString("3.5")) == 3.5
    assert complex(UserString("2+3j")) == 2 + 3j


def test_userstring_arithmetic_and_percent_formatting_return_actual_class():
    """连接、反向连接、重复和旧式 % 格式化都通过 self.__class__ 包装新文本。"""

    class Message(UserString):
        pass

    base = Message("hello")
    results = [
        base + UserString(" world"),
        "> " + base,
        base * 2,
        Message("item=%03d") % 7,
    ]

    assert all(isinstance(result, Message) for result in results)
    assert [str(result) for result in results] == [
        "hello world",
        "> hello",
        "hellohello",
        "item=007",
    ]

    identity = id(base)
    base += "!"
    # UserString 没有 __iadd__；增强赋值退回 __add__，再重新绑定名称。
    assert id(base) != identity
    assert isinstance(base, Message)
    assert base == "hello!"


def test_userstring_transforming_and_query_methods_have_distinct_result_types():
    """文本转换多保留 wrapper；查询返回 int/bool，encode 返回 bytes。"""

    class Message(UserString):
        pass

    text = Message("  Python atlas  ")
    normalized = text.strip().replace("Python", "Polyglot").upper()

    assert isinstance(normalized, Message)
    assert normalized == "POLYGLOT ATLAS"
    assert type(text.count("a")) is int
    assert text.count("a") == 2
    assert type(text.isprintable()) is bool
    assert text.isprintable() is True
    assert text.encode("utf-8") == b"  Python atlas  "


def test_userstring_structured_text_methods_return_native_str_containers():
    """format/join 不包装结果；split/partition 返回由原生 str 构成的容器。"""

    formatted = UserString("{language} {version}").format(
        language="Python",
        version="3.10",
    )
    joined = UserString(",").join(["red", "green", "blue"])
    fields = UserString("name=Ada").partition("=")
    words = UserString("one two three").split()

    assert type(formatted) is str
    assert formatted == "Python 3.10"
    assert type(joined) is str
    assert joined == "red,green,blue"
    assert fields == ("name", "=", "Ada")
    assert all(type(field) is str for field in fields)
    assert words == ["one", "two", "three"]
    assert all(type(word) is str for word in words)


def test_userstring_accepts_wrapped_needles_only_in_methods_that_cast_them():
    """contains/find/replace 显式拆 data；startswith 在 3.10 直接委托 str，不接收 wrapper。"""

    text = UserString("prefix-body")
    needle = UserString("body")

    assert needle in text
    assert text.find(needle) == 7
    replaced = text.replace(needle, UserString("value"))
    assert isinstance(replaced, UserString)
    assert replaced == "prefix-value"

    with pytest.raises(TypeError, match="startswith"):
        text.startswith(UserString("prefix"))


def test_userstring_data_can_be_rebound_and_changes_equality_and_hash_source():
    """包装的是不可变 str，但包装器属性可变；作为 hash key 后不要再重绑 data。"""

    text = UserString("stable")
    assert text == "stable"
    assert hash(text) == hash("stable")

    text.data = "changed"

    assert str(text) == "changed"
    assert text == "changed"
    assert text != "stable"
    assert hash(text) == hash("changed")


def test_userstring_subclass_constructor_is_reused_by_wrapper_returning_methods():
    """结果经实际 class 构造，可持续维护不变量；直接写 data 仍能绕过它。"""

    class Slug(UserString):
        def __init__(self, value):
            normalized = "-".join(str(value).strip().casefold().split())
            super().__init__(normalized)

    slug = Slug("  Python Atlas  ")
    extended = slug + " Version 3.10 "
    upper_attempt = slug.upper()

    assert slug == "python-atlas"
    assert isinstance(extended, Slug)
    assert extended == "python-atlas-version-3.10"
    assert isinstance(upper_attempt, Slug)
    # upper() 先产生大写 str，再由 Slug 构造器重新 casefold。
    assert upper_attempt == "python-atlas"

    slug.data = "NOT normalized"
    assert str(slug) == "NOT normalized"


def test_userstring_init_can_replace_storage_where_str_subclass_init_cannot():
    """str 值在 __new__ 已确定；只写 __init__ 无法改变它，UserString 则控制 data。"""

    class MisleadingLowerStr(str):
        def __init__(self, value):
            self.normalized = value.casefold()

    class LowerUserString(UserString):
        def __init__(self, value):
            super().__init__(str(value).casefold())

    direct_subclass = MisleadingLowerStr("LOUD")
    wrapper_subclass = LowerUserString("LOUD")

    assert str(direct_subclass) == "LOUD"
    assert direct_subclass.normalized == "loud"
    assert str(wrapper_subclass) == "loud"
