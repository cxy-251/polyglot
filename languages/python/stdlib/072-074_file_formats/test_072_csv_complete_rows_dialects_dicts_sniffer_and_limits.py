"""072｜``csv`` 行读写、quoting、newline、Dialect registry 与格式参数。

CSV 没有唯一标准；reader/writer 依靠 Dialect 组合 delimiter、quote、escape 等规则。
文件应以 ``newline=''`` 打开，让 csv 自己处理 record newline。writer 会把非字符串
交给
``str``，并把 ``None`` 写为空字段，这对 DB-API 方便但不可逆。

这些案例面向 Python 3.10 当前补丁系列。
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


# ``DictReader``/``DictWriter``、``Sniffer``、strict parsing 与 field limit。
#
# 字典 API 处理 schema 不齐的 rows，Sniffer 只提供启发式猜测，不能当作格式
# 验证。``field_size_limit`` 和 dialect registry 一样是 process-global 设置，
# 临时修改必须恢复。strict 模式能报告未闭合 quote；reader 的输入 iterator
# 必须返回 str 而非 bytes。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.csv.DictReader python.csv.DictReader.fieldnames
# polyglot-covers: python.csv.dict-row-order python.csv.DictReader.restkey
# polyglot-covers: python.csv.DictReader.restval python.csv.DictReader-row-type
# polyglot-covers: python.csv.DictWriter python.csv.DictWriter.writeheader
# polyglot-covers: python.csv.DictWriter.restval python.csv.extrasaction-raise
# polyglot-covers: python.csv.extrasaction-ignore python.csv.Sniffer
# polyglot-covers: python.csv.Sniffer.sniff python.csv.Sniffer.delimiters
# polyglot-covers: python.csv.Sniffer.has-header python.csv.sniffer-heuristic
# polyglot-covers: python.csv.field-size-limit python.csv.field-too-large
# polyglot-covers: python.csv.strict python.csv.malformed-quote
# polyglot-covers: python.csv.reader-requires-str python.csv.bytes-input-error




def test_dictreader_uses_first_row_as_ordered_fieldnames():
    """未传 fieldnames 时首次访问会消费 header；3.8+ row 是保序普通 dict。"""

    reader = csv.DictReader(["name,age,city", "Alice,30,Paris"])

    assert reader.fieldnames == ["name", "age", "city"]
    row = next(reader)
    assert type(row) is dict
    assert list(row) == ["name", "age", "city"]
    assert row == {"name": "Alice", "age": "30", "city": "Paris"}


def test_dictreader_routes_extra_and_missing_values():
    """多余字段形成 restkey list；缺失字段以 restval 补齐，而不是省略 key。"""

    reader = csv.DictReader(
        ["Alice,30,Paris", "Bob,40"],
        fieldnames=["name", "age"],
        restkey="extra",
        restval="MISSING",
    )

    assert next(reader) == {"name": "Alice", "age": "30", "extra": ["Paris"]}
    assert next(reader) == {"name": "Bob", "age": "40"}

    missing = csv.DictReader(
        ["Alice"],
        fieldnames=["name", "age"],
        restval="MISSING",
    )
    assert next(missing) == {"name": "Alice", "age": "MISSING"}


def test_dictwriter_writes_header_and_fills_missing_keys():
    """writeheader 返回底层 writerow 的字符数；missing key 使用 restval。"""

    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=["name", "age"],
        restval="unknown",
        lineterminator="\n",
    )

    header_size = writer.writeheader()
    writer.writerow({"name": "Alice"})

    assert header_size == len("name,age\n")
    assert output.getvalue() == "name,age\nAlice,unknown\n"


def test_dictwriter_extra_keys_raise_by_default_or_can_be_ignored():
    """extrasaction 默认阻止 schema 漂移；ignore 必须显式选择。"""

    strict_output = io.StringIO()
    strict_writer = csv.DictWriter(strict_output, fieldnames=["name"])
    with pytest.raises(ValueError, match="fields not in fieldnames"):
        strict_writer.writerow({"name": "Alice", "age": 30})

    ignored_output = io.StringIO(newline="")
    ignored_writer = csv.DictWriter(
        ignored_output,
        fieldnames=["name"],
        extrasaction="ignore",
        lineterminator="\n",
    )
    ignored_writer.writerow({"name": "Alice", "age": 30})
    assert ignored_output.getvalue() == "Alice\n"


def test_sniffer_detects_delimiter_from_an_allowed_candidate_set():
    """delimiters 限制候选字符，可避免 sample 中其他标点被误判为分隔符。"""

    sample = "name;score\nAlice;10\nBob;20\n"
    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")

    assert dialect.delimiter == ";"
    assert list(csv.reader(sample.splitlines(), dialect)) == [
        ["name", "score"],
        ["Alice", "10"],
        ["Bob", "20"],
    ]


def test_has_header_is_only_a_heuristic():
    """numeric data 常使首行被判为 header；结果是猜测，不能替代显式 schema。"""

    with_header = "name,score\nAlice,10\nBob,20\n"
    without_header = "Alice,10\nBob,20\nCarol,30\n"

    assert csv.Sniffer().has_header(with_header) is True
    assert csv.Sniffer().has_header(without_header) is False


def test_sniffer_raises_csv_error_when_sample_has_no_detectable_format():
    """空或无一致 delimiter 的 sample 不能保证有 dialect，调用方需 fallback。"""

    with pytest.raises(csv.Error, match="Could not determine delimiter"):
        csv.Sniffer().sniff("")


def test_field_size_limit_is_process_global_and_must_be_restored():
    """降低 limit 可提前拒绝大字段；setter 返回旧值，便于 finally 恢复。"""

    original = csv.field_size_limit()
    previous = csv.field_size_limit(5)
    try:
        assert previous == original
        assert csv.field_size_limit() == 5
        with pytest.raises(csv.Error, match="field larger than field limit"):
            next(csv.reader(["123456"]))
    finally:
        csv.field_size_limit(original)

    assert csv.field_size_limit() == original


def test_strict_mode_rejects_an_unterminated_quoted_field():
    """默认宽松 reader 会把 EOF 当结束；strict=True 报 unexpected end of data。"""

    malformed = ['name,"unterminated\n']
    assert next(csv.reader(malformed, strict=False)) == ["name", "unterminated\n"]
    with pytest.raises(csv.Error, match="unexpected end of data"):
        next(csv.reader(malformed, strict=True))


def test_reader_iterator_must_yield_text_not_bytes():
    """csv 在 text 层工作；binary file 应先用正确 encoding 包 TextIOWrapper。"""

    with pytest.raises(csv.Error, match="iterator should return strings"):
        next(csv.reader([b"a,b"]))
