"""166｜源码词法工具：token、keyword、tokenize、tabnanny 与 pyclbr。

这些模块位于“源文本”和 AST 之间：token/keyword 给词法类别命名，tokenize
保留注释、编码声明和物理位置，tabnanny 在 token 流上查找制表符歧义，pyclbr
则只解析定义轮廓而不导入执行模块。本套把它们连成可复用的
源码检查工作流，
并区分词法正确、缩进无歧义和语法/语义正确这几个经常被混淆的层次。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.stdlib.token python.token.constants python.token.tok-name
# polyglot-covers: python.token.exact-token-types python.token.category-predicates
# polyglot-covers: python.stdlib.keyword python.keyword.kwlist python.keyword.iskeyword
# polyglot-covers: python.keyword.softkwlist python.keyword.issoftkeyword
# polyglot-covers: python.stdlib.tokenize python.tokenize.tokenize
# polyglot-covers: python.tokenize.generate-tokens python.tokenize.token-info
# polyglot-covers: python.tokenize.positions python.tokenize.exact-type
# polyglot-covers: python.tokenize.encoding-token python.tokenize.comments
# polyglot-covers: python.tokenize.physical-vs-logical-lines
# polyglot-covers: python.tokenize.indent-dedent python.tokenize.nl-vs-newline
# polyglot-covers: python.tokenize.detect-encoding python.tokenize.utf8-bom
# polyglot-covers: python.tokenize.encoding-cookie python.tokenize.encoding-conflict
# polyglot-covers: python.tokenize.open python.tokenize.untokenize
# polyglot-covers: python.tokenize.roundtrip-guarantee python.tokenize.token-error
# polyglot-covers: python.tokenize.errortoken python.tokenize.not-a-parser
# polyglot-covers: python.stdlib.tabnanny python.tabnanny.process-tokens
# polyglot-covers: python.tabnanny.nanny-nag python.tabnanny.check-recursive
# polyglot-covers: python.tabnanny.tab-width-ambiguity
# polyglot-covers: python.stdlib.pyclbr python.pyclbr.readmodule
# polyglot-covers: python.pyclbr.readmodule-ex python.pyclbr.class-descriptor
# polyglot-covers: python.pyclbr.function-descriptor python.pyclbr.nested-children
# polyglot-covers: python.pyclbr.async-function python.pyclbr.superclasses
# polyglot-covers: python.pyclbr.package-path python.pyclbr.imported-definitions
# polyglot-covers: python.pyclbr.static-no-execution python.pyclbr.errors

import io
import keyword
import pyclbr
import tabnanny
import token
import tokenize

import pytest


def token_pairs(items):
    """只保留 untokenize 官方承诺能够往返的 token 类型与文本。"""

    return [(item.type, item.string) for item in items]


def test_token_constants_map_numbers_names_and_exact_operators():
    assert token.tok_name[token.NAME] == "NAME"
    assert token.tok_name[token.STRING] == "STRING"
    assert token.tok_name[token.ENDMARKER] == "ENDMARKER"

    assert token.EXACT_TOKEN_TYPES["+"] == token.PLUS
    assert token.EXACT_TOKEN_TYPES["**"] == token.DOUBLESTAR
    assert token.EXACT_TOKEN_TYPES[":="] == token.COLONEQUAL

    assert token.ISTERMINAL(token.NAME) is True
    assert token.ISNONTERMINAL(token.NT_OFFSET) is True
    assert token.ISEOF(token.ENDMARKER) is True
    assert token.ISEOF(token.NAME) is False
    # 数值常量是实现词法工具时的协议；持久数据应保存名字，
    # 不要假定编号永远不变。


def test_keyword_distinguishes_hard_soft_and_ordinary_identifiers():
    assert keyword.iskeyword("def") is True
    assert keyword.iskeyword("True") is True
    assert "def" in keyword.kwlist

    assert keyword.iskeyword("match") is False
    assert keyword.issoftkeyword("match") is True
    assert keyword.issoftkeyword("case") is True
    assert {"match", "case"}.issubset(keyword.softkwlist)

    assert keyword.iskeyword("result") is False
    assert keyword.issoftkeyword("result") is False
    # 软关键字只在特定语法位置有含义，因此 match 仍可作为普通变量名。


def test_tokenize_bytes_exposes_encoding_comments_positions_and_token_info():
    source = b"# coding: utf-8\nvalue = 1 + 2  # note\n"
    items = list(tokenize.tokenize(io.BytesIO(source).readline))

    assert items[0].type == token.ENCODING
    assert items[0].string == "utf-8"
    comments = [item for item in items if item.type == token.COMMENT]
    assert [item.string for item in comments] == [
        "# coding: utf-8",
        "# note",
    ]

    name = next(item for item in items if item.string == "value")
    assert isinstance(name, tokenize.TokenInfo)
    assert tuple(name) == (
        token.NAME,
        "value",
        (2, 0),
        (2, 5),
        "value = 1 + 2  # note\n",
    )


def test_exact_type_refines_the_generic_operator_token():
    source = b"value **= 2; sliced = items[1:3]\n"
    items = list(tokenize.tokenize(io.BytesIO(source).readline))
    operators = {item.string: item for item in items if item.type == token.OP}

    assert operators["**="].type == token.OP
    assert operators["**="].exact_type == token.DOUBLESTAREQUAL
    assert operators["["].exact_type == token.LSQB
    assert operators[":"].exact_type == token.COLON
    # 解析器可先按 OP 统一处理，也可通过 exact_type 精确分派每一种标点。


def test_generate_tokens_is_the_text_readline_compatibility_entry_point():
    items = list(tokenize.generate_tokens(io.StringIO("answer = 42\n").readline))

    assert items[0].type == token.NAME
    assert all(item.type != token.ENCODING for item in items)
    assert items[-1].type == token.ENDMARKER
    # generate_tokens 接收 str，因而不会产生 ENCODING；
    # 新字节流工具优先用 tokenize。


def test_nl_and_newline_distinguish_physical_from_logical_lines():
    source = (
        "values = (\n"
        "    1,  # first\n"
        "    2,\n"
        ")\n"
        "\n"
        "total = sum(values)\n"
    )
    items = list(tokenize.generate_tokens(io.StringIO(source).readline))

    nl_lines = [item.start[0] for item in items if item.type == token.NL]
    newline_lines = [
        item.start[0] for item in items if item.type == token.NEWLINE
    ]
    assert nl_lines == [1, 2, 3, 5]
    assert newline_lines == [4, 6]
    assert any(item.type == token.COMMENT for item in items)
    # 括号内换行和空白行是 NL；真正结束一条逻辑语句的才是 NEWLINE。


def test_indent_and_dedent_describe_block_structure_without_building_an_ast():
    source = (
        "if ready:\n"
        "    first = 1\n"
        "    if nested:\n"
        "        second = 2\n"
        "third = 3\n"
    )
    items = list(tokenize.generate_tokens(io.StringIO(source).readline))

    indents = [item.string for item in items if item.type == token.INDENT]
    dedents = [item for item in items if item.type == token.DEDENT]
    assert indents == ["    ", "        "]
    assert len(dedents) == 2
    assert all(item.string == "" for item in dedents)
    assert dedents[-1].start == (5, 0)


def test_detect_encoding_obeys_cookie_and_bom_rules():
    latin_lines = iter([b"# coding: latin-1\n", b"name = 'caf\xe9'\n"])
    encoding, consumed = tokenize.detect_encoding(latin_lines.__next__)
    assert encoding == "iso-8859-1"
    assert consumed == [b"# coding: latin-1\n"]

    bom_lines = iter([tokenize.BOM_UTF8 + b"value = 1\n"])
    encoding, consumed = tokenize.detect_encoding(bom_lines.__next__)
    assert encoding == "utf-8-sig"
    assert consumed == [b"value = 1\n"]

    conflict = iter(
        [tokenize.BOM_UTF8 + b"# coding: latin-1\n"]
    )
    with pytest.raises(SyntaxError, match="encoding problem"):
        tokenize.detect_encoding(conflict.__next__)


def test_detect_encoding_reads_at_most_two_lines_and_rejects_unknown_codecs():
    calls = []
    lines = iter([b"#!/usr/bin/env python\n", b"value = 1\n", b"ignored\n"])

    def readline():
        calls.append(None)
        return next(lines)

    encoding, consumed = tokenize.detect_encoding(readline)
    assert encoding == "utf-8"
    assert consumed == [b"#!/usr/bin/env python\n", b"value = 1\n"]
    assert len(calls) == 2

    unknown = iter([b"# coding: definitely-not-a-codec\n"])
    with pytest.raises(SyntaxError, match="unknown encoding"):
        tokenize.detect_encoding(unknown.__next__)


def test_tokenize_open_uses_the_source_encoding_cookie(tmp_path):
    path = tmp_path / "latin1_source.py"
    path.write_bytes(b"# coding: latin-1\nlabel = 'caf\xe9'\n")

    with tokenize.open(path) as source_file:
        text = source_file.read()
        assert source_file.encoding == "iso-8859-1"

    assert "label = 'café'" in text
    # 普通 open() 若猜 UTF-8 会失败；tokenize.open 实现的是
    # Python 源文件编码规则。


def test_untokenize_guarantees_token_pairs_but_not_original_spacing():
    source = b"answer=6*7  # compact\n"
    original = list(tokenize.tokenize(io.BytesIO(source).readline))
    rebuilt = tokenize.untokenize(original)
    reparsed = list(tokenize.tokenize(io.BytesIO(rebuilt).readline))

    assert isinstance(rebuilt, bytes)
    assert token_pairs(reparsed) == token_pairs(original)
    # 精确空格位置不是保证的一部分；格式化器不能把 untokenize
    # 当作无损文本存储。


def test_untokenize_without_encoding_returns_text_and_accepts_token_pairs():
    pairs = [
        (token.NAME, "total"),
        (token.OP, "="),
        (token.NUMBER, "40"),
        (token.OP, "+"),
        (token.NUMBER, "2"),
        (token.NEWLINE, "\n"),
        (token.ENDMARKER, ""),
    ]

    rebuilt = tokenize.untokenize(pairs)
    assert isinstance(rebuilt, str)
    assert "total" in rebuilt
    assert "40" in rebuilt


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ('text = """unfinished\n', "multi-line string"),
        ("values = [1, 2\n", "multi-line statement"),
    ],
)
def test_incomplete_multiline_constructs_raise_token_error(source, message):
    with pytest.raises(tokenize.TokenError, match=message):
        list(tokenize.generate_tokens(io.StringIO(source).readline))


def test_unterminated_single_quote_is_an_error_token_not_token_error():
    source = "value = 'unfinished\n"
    items = list(tokenize.generate_tokens(io.StringIO(source).readline))
    errors = [item.string for item in items if item.type == token.ERRORTOKEN]

    assert "'" in errors
    # 单行字符串错误会以 ERRORTOKEN 暴露；只捕获 TokenError 会漏掉这类输入。


def test_tokenization_does_not_validate_parser_context():
    source = "return 42\n"
    items = list(tokenize.generate_tokens(io.StringIO(source).readline))

    assert [item.string for item in items[:2]] == ["return", "42"]
    with pytest.raises(SyntaxError, match="outside function"):
        compile(source, "context.py", "exec")
    # tokenize 只识别词法结构，不判断 return 是否处在函数体等语法上下文。


def test_tabnanny_process_tokens_reports_tab_width_ambiguity():
    source = (
        "if True:\n"
        "\tvalue = 1\n"
        "        value = 2\n"
    )
    items = tokenize.generate_tokens(io.StringIO(source).readline)

    with pytest.raises(tabnanny.NannyNag) as caught:
        tabnanny.process_tokens(items)

    nag = caught.value
    assert nag.get_lineno() == 3
    assert nag.get_line() == "        value = 2\n"
    assert "indent not equal" in nag.get_msg()
    assert "tab size" in nag.get_msg()
    # 两行在 tabsize=8 时同列，但换一个制表宽度便不同，
    # 所以属于可移植性陷阱。


def test_tabnanny_accepts_consistent_indentation():
    source = (
        "if True:\n"
        "    value = 1\n"
        "    if value:\n"
        "        value += 1\n"
    )
    items = tokenize.generate_tokens(io.StringIO(source).readline)

    assert tabnanny.process_tokens(items) is None


def test_tabnanny_check_recurses_into_directories_and_reports_python_files(
    tmp_path,
    capsys,
):
    package = tmp_path / "package"
    package.mkdir()
    bad_file = package / "ambiguous.py"
    bad_file.write_text(
        "if True:\n\tvalue = 1\n        value = 2\n",
        encoding="utf-8",
    )
    (package / "ignored.txt").write_text("not python", encoding="utf-8")

    old_verbose = tabnanny.verbose
    old_filename_only = tabnanny.filename_only
    try:
        tabnanny.verbose = 0
        tabnanny.filename_only = 1
        assert tabnanny.check(str(package)) is None
    finally:
        tabnanny.verbose = old_verbose
        tabnanny.filename_only = old_filename_only

    captured = capsys.readouterr()
    assert captured.out.strip() == str(bad_file)
    assert captured.err == ""
    # check 是面向脚本的 API：发现问题时打印诊断并返回 None，
    # 而不是把 NannyNag 传出。


def test_pyclbr_reads_top_level_and_nested_definitions_without_execution(tmp_path):
    module_path = tmp_path / "outline_lesson.py"
    module_path.write_text(
        "raise RuntimeError('must not execute')\n"
        "def top_level():\n"
        "    def nested():\n"
        "        return 1\n"
        "    return nested\n"
        "async def fetch():\n"
        "    return 2\n"
        "class Base:\n"
        "    pass\n"
        "class Child(Base, external.Mixin):\n"
        "    def method(self):\n"
        "        return None\n"
        "    async def async_method(self):\n"
        "        return None\n"
        "    class Nested:\n"
        "        pass\n",
        encoding="utf-8",
    )

    tree = pyclbr.readmodule_ex("outline_lesson", [str(tmp_path)])
    assert set(tree) == {"top_level", "fetch", "Base", "Child"}

    top_level = tree["top_level"]
    assert isinstance(top_level, pyclbr.Function)
    assert top_level.module == "outline_lesson"
    assert top_level.file == str(module_path)
    assert top_level.lineno == 2
    assert top_level.end_lineno == 5
    assert top_level.parent is None
    assert isinstance(top_level.children["nested"], pyclbr.Function)
    assert top_level.children["nested"].parent is top_level

    fetch = tree["fetch"]
    assert fetch.is_async is True
    assert fetch.lineno == 6

    base = tree["Base"]
    child = tree["Child"]
    assert isinstance(child, pyclbr.Class)
    assert child.super == [base]
    # 3.10 的 pyclbr 能链接同一分析树里已解析的 Base，但会忽略无法解析的
    # external.Mixin；它提供源码轮廓，不是完整、保真的 AST。
    assert child.methods == {"method": 11, "async_method": 13}
    assert child.children["method"].is_async is False
    assert child.children["async_method"].is_async is True
    assert isinstance(child.children["Nested"], pyclbr.Class)


def test_pyclbr_readmodule_keeps_only_top_level_classes(tmp_path):
    module_path = tmp_path / "classes_only_lesson.py"
    module_path.write_text(
        "def helper():\n"
        "    return None\n"
        "class Public:\n"
        "    class Nested:\n"
        "        pass\n",
        encoding="utf-8",
    )

    extended = pyclbr.readmodule_ex("classes_only_lesson", [str(tmp_path)])
    classes_only = pyclbr.readmodule("classes_only_lesson", [str(tmp_path)])

    assert set(extended) == {"helper", "Public"}
    assert set(classes_only) == {"Public"}
    assert "Nested" in classes_only["Public"].children
    # readmodule 的“只返回类”只过滤顶层映射，
    # 类内部的 children 仍保留嵌套轮廓。


def test_pyclbr_reports_package_search_path_and_reads_dotted_modules(tmp_path):
    package = tmp_path / "browser_package"
    package.mkdir()
    (package / "__init__.py").write_text(
        "class PackageMarker:\n    pass\n",
        encoding="utf-8",
    )
    model_path = package / "models.py"
    model_path.write_text(
        "class Model:\n    pass\n",
        encoding="utf-8",
    )

    package_tree = pyclbr.readmodule_ex("browser_package", [str(tmp_path)])
    model_tree = pyclbr.readmodule_ex(
        "browser_package.models",
        [str(tmp_path)],
    )

    assert list(package_tree["__path__"]) == [str(package)]
    assert isinstance(package_tree["PackageMarker"], pyclbr.Class)
    assert model_tree["Model"].module == "browser_package.models"
    assert model_tree["Model"].file == str(model_path)


def test_pyclbr_follows_from_imports_to_resolve_superclasses(tmp_path):
    (tmp_path / "browser_base.py").write_text(
        "class Parent:\n    pass\n",
        encoding="utf-8",
    )
    child_path = tmp_path / "browser_child.py"
    child_path.write_text(
        "from browser_base import Parent\n"
        "class Child(Parent):\n"
        "    pass\n",
        encoding="utf-8",
    )

    tree = pyclbr.readmodule_ex("browser_child", [str(tmp_path)])

    assert set(tree) == {"Parent", "Child"}
    assert tree["Parent"].module == "browser_base"
    assert tree["Child"].module == "browser_child"
    assert tree["Child"].super == [tree["Parent"]]
    # 导入进来的描述符保留原 module/file，
    # 当前模块的类可直接引用它解析基类。


def test_pyclbr_surfaces_missing_modules_and_source_syntax_errors(tmp_path):
    with pytest.raises(ModuleNotFoundError) as missing:
        pyclbr.readmodule_ex("module_that_does_not_exist_166", [str(tmp_path)])
    assert missing.value.name == "module_that_does_not_exist_166"

    (tmp_path / "broken_outline.py").write_text(
        "def broken(:\n    pass\n",
        encoding="utf-8",
    )
    with pytest.raises(SyntaxError):
        pyclbr.readmodule_ex("broken_outline", [str(tmp_path)])
    # pyclbr 不执行源码，但仍依赖 ast.parse，
    # 所以语法错误不会被当作空轮廓吞掉。
