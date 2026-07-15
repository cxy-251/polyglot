"""387｜模块全局表的 init/add_type，以及测试隔离。

模块 convenience functions 共用可变全局数据库：首次查询会惰性 init，add_type 会影响后续所有
调用。init(files=[]) 只装载内建 well-known 表，避免宿主系统 mime.types；init(None) 则完全重建
并读取 knownfiles。库代码若不想产生跨测试/租户状态泄漏，应优先持有独立 MimeTypes 实例。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mimetypes.init
# polyglot-covers: python.mimetypes.init-empty-files-builtins-only
# polyglot-covers: python.mimetypes.init-none-rebuilds-defaults
# polyglot-covers: python.mimetypes.repeated-init-allowed
# polyglot-covers: python.mimetypes.inited
# polyglot-covers: python.mimetypes.knownfiles
# polyglot-covers: python.mimetypes.types_map
# polyglot-covers: python.mimetypes.common_types
# polyglot-covers: python.mimetypes.add_type
# polyglot-covers: python.mimetypes.global-add-type-process-wide-state
# polyglot-covers: python.mimetypes.prefer-instance-for-state-isolation

import mimetypes


def _preserve_global_database_for_monkeypatch(monkeypatch):
    # 先让 monkeypatch 记录原对象；即使 init 随后替换模块属性，teardown 仍会恢复原引用。
    for name in (
        "_db",
        "inited",
        "suffix_map",
        "encodings_map",
        "types_map",
        "common_types",
    ):
        monkeypatch.setattr(mimetypes, name, getattr(mimetypes, name))


def test_init_with_empty_file_list_is_repeatable_and_uses_builtin_tables(monkeypatch):
    _preserve_global_database_for_monkeypatch(monkeypatch)
    monkeypatch.setattr(mimetypes, "knownfiles", [])

    mimetypes.init(files=[])
    first = mimetypes.guess_type("lesson.html")
    first_size = len(mimetypes.types_map)
    # files=None 完全重建默认状态；knownfiles 已隔离为空，所以不会读取宿主机配置。
    mimetypes.init(files=None)
    assert mimetypes.inited is True
    assert mimetypes.guess_type("lesson.html") == first == ("text/html", None)
    assert len(mimetypes.types_map) == first_size
    assert isinstance(mimetypes.knownfiles, list)
    assert isinstance(mimetypes.common_types, dict)


def test_module_add_type_mutates_the_shared_database_but_is_isolated_here(monkeypatch):
    isolated = mimetypes.MimeTypes()
    monkeypatch.setattr(mimetypes, "_db", isolated)
    monkeypatch.setattr(mimetypes, "inited", True)
    monkeypatch.setattr(mimetypes, "suffix_map", isolated.suffix_map)
    monkeypatch.setattr(mimetypes, "encodings_map", isolated.encodings_map)
    monkeypatch.setattr(mimetypes, "types_map", isolated.types_map[1])
    monkeypatch.setattr(mimetypes, "common_types", isolated.types_map[0])

    assert mimetypes.guess_type("lesson.pglobal") == (None, None)
    assert mimetypes.add_type("application/x-global-demo", ".pglobal") is None
    assert mimetypes.guess_type("lesson.pglobal")[0] == "application/x-global-demo"
    assert mimetypes.guess_extension("application/x-global-demo") == ".pglobal"
