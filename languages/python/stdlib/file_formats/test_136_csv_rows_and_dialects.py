"""136｜``csv`` 行读写、quoting、newline、Dialect registry 与格式参数。

CSV 没有唯一标准；reader/writer 依靠 Dialect 组合 delimiter、quote、escape 等规则。
文件应以 ``newline=''`` 打开，让 csv 自己处理 record newline。writer 会把非字符串
交给
``str``，并把 ``None`` 写为空字段，这对 DB-API 方便但不可逆。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.csv.reader python.csv.writer python.csv.newline-empty
# polyglot-covers: python.csv.quoted-delimiter python.csv.multiline-field
# polyglot-covers: python.csv.reader-line-num python.csv.writerow-return
# polyglot-covers: python.csv.writerows python.csv.arbitrary-row-iterable
# polyglot-covers: python.csv.none-empty-field python.csv.non-string-str
# polyglot-covers: python.csv.QUOTE_MINIMAL python.csv.QUOTE_ALL
# polyglot-covers: python.csv.QUOTE_NONNUMERIC python.csv.QUOTE_NONE
# polyglot-covers: python.csv.escapechar python.csv.doublequote
# polyglot-covers: python.csv.skipinitialspace python.csv.lineterminator-writer-only
# polyglot-covers: python.csv.Dialect python.csv.register-dialect
# polyglot-covers: python.csv.get-dialect python.csv.list-dialects
# polyglot-covers: python.csv.unregister-dialect python.csv.immutable-dialect
# polyglot-covers: python.csv.fmtparams-override python.csv.Error

import csv
import io

import pytest


def test_reader_handles_quoted_delimiters_and_multiline_fields():
    """logical record 可跨多个输入行；line_num 统计物理行而非 row 数。"""

    source = io.StringIO('name,note\r\nAlice,"first line\nsecond,line"\r\n')
    reader = csv.reader(source)

    assert next(reader) == ["name", "note"]
    assert reader.line_num == 1
    assert next(reader) == ["Alice", "first line\nsecond,line"]
    assert reader.line_num == 3


def test_file_workflow_uses_newline_empty_and_explicit_encoding(tmp_path):
    """newline='' 避免 TextIOWrapper 先改写 newline，统一各平台行为。"""

    path = tmp_path / "records.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["名称", "备注"])
        writer.writerow(["甲", "包含\n换行"])

    with path.open("r", encoding="utf-8", newline="") as stream:
        assert list(csv.reader(stream)) == [["名称", "备注"], ["甲", "包含\n换行"]]


def test_writer_stringifies_values_and_maps_none_to_empty_irreversibly():
    """None 与空字符串都写为空字段；读取后不能区分 NULL 与 empty string。"""

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")

    characters_written = writer.writerow([None, "", 42, 3 + 4j])

    assert output.getvalue() == ",,42,(3+4j)\n"
    assert characters_written == len(output.getvalue())
    assert next(csv.reader([output.getvalue()])) == ["", "", "42", "(3+4j)"]


def test_writerows_accepts_generators_for_rows_and_cells():
    """3.5+ row 可是任意 iterable；writerows 也可消费惰性 rows。"""

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    rows = ((str(value) for value in range(start, start + 2)) for start in (0, 2))

    assert writer.writerows(rows) is None
    assert output.getvalue() == "0,1\n2,3\n"


def test_quote_minimal_and_quote_all_choose_different_output():
    """MINIMAL 只 quote 特殊字段；ALL 对每个字段 quote，reader 结果相同。"""

    minimal = io.StringIO(newline="")
    csv.writer(minimal, quoting=csv.QUOTE_MINIMAL, lineterminator="\n").writerow(
        ["plain", "contains,comma"]
    )
    quoted = io.StringIO(newline="")
    csv.writer(quoted, quoting=csv.QUOTE_ALL, lineterminator="\n").writerow(
        ["plain", "contains,comma"]
    )

    assert minimal.getvalue() == 'plain,"contains,comma"\n'
    assert quoted.getvalue() == '"plain","contains,comma"\n'
    assert next(csv.reader([minimal.getvalue()])) == next(csv.reader([quoted.getvalue()]))


def test_quote_nonnumeric_converts_only_unquoted_input_to_float():
    """quoted number 保持 str；未 quote 字段统一转 float，而不是 int。"""

    row = next(csv.reader(['1,"2",3.5'], quoting=csv.QUOTE_NONNUMERIC))

    assert row == [1.0, "2", 3.5]
    assert [type(value) for value in row] == [float, str, float]


def test_quote_none_requires_escapechar_for_delimiter_data():
    """禁用 quoting 后特殊字符必须 escape；没有 escapechar 会抛 csv.Error。"""

    with pytest.raises(csv.Error, match="need to escape"):
        csv.writer(io.StringIO(), quoting=csv.QUOTE_NONE).writerow(["a,b"])

    output = io.StringIO(newline="")
    csv.writer(
        output,
        quoting=csv.QUOTE_NONE,
        escapechar="\\",
        lineterminator="\n",
    ).writerow(["a,b", "plain"])
    assert output.getvalue() == "a\\,b,plain\n"
    assert next(
        csv.reader(
            [output.getvalue()],
            quoting=csv.QUOTE_NONE,
            escapechar="\\",
        )
    ) == ["a,b", "plain"]


def test_doublequote_false_uses_escapechar_for_quote_inside_field():
    """doublequote=True 生成两个 quote；False 改用 escapechar。"""

    output = io.StringIO(newline="")
    csv.writer(
        output,
        doublequote=False,
        escapechar="\\",
        lineterminator="\n",
    ).writerow(['say "hello"'])

    assert output.getvalue() == 'say \\"hello\\"\n'


def test_skipinitialspace_only_removes_space_after_delimiter():
    """它不做通用 strip：字段尾部和 quoted field 内的空格仍保留。"""

    row = next(csv.reader([" left,  middle ,\" quoted \""], skipinitialspace=True))

    assert row == ["left", "middle ", " quoted "]


def test_writer_lineterminator_does_not_reconfigure_reader_record_rules():
    """lineterminator 只用于 writer；reader 仍硬编码识别 CR 或 LF。"""

    output = io.StringIO(newline="")
    csv.writer(output, delimiter=";", lineterminator="<END>").writerow(["a", "b"])

    assert output.getvalue() == "a;b<END>"
    source = io.StringIO("a;b\rb;c\n", newline="")
    assert list(csv.reader(source, delimiter=";")) == [["a", "b"], ["b", "c"]]


def test_registry_returns_an_immutable_dialect_and_can_unregister():
    """registry 是 process-global 状态，测试和应用插件使用后应显式清理。"""

    name = "polyglot-semicolon"
    csv.register_dialect(
        name,
        delimiter=";",
        quotechar="'",
        lineterminator="\n",
    )
    try:
        assert name in csv.list_dialects()
        dialect = csv.get_dialect(name)
        assert dialect.delimiter == ";"
        with pytest.raises(AttributeError):
            dialect.delimiter = ","

        assert next(csv.reader(["a;b"], dialect=name)) == ["a", "b"]
        # fmtparams 的优先级高于已注册 dialect。
        assert next(csv.reader(["a|b"], dialect=name, delimiter="|")) == ["a", "b"]
    finally:
        csv.unregister_dialect(name)

    with pytest.raises(csv.Error, match="unknown dialect"):
        csv.get_dialect(name)
