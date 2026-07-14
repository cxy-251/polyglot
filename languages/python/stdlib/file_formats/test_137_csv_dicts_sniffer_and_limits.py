"""137｜``DictReader``/``DictWriter``、``Sniffer``、strict parsing 与 field limit。

字典 API 处理 schema 不齐的 rows，Sniffer 只提供启发式猜测，不能当作格式
验证。``field_size_limit`` 和 dialect registry 一样是 process-global 设置，
临时修改必须恢复。strict 模式能报告未闭合 quote；reader 的输入 iterator
必须返回 str 而非 bytes。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import csv
import io

import pytest


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
