"""384｜Python 3.10 已弃用 BinHex4 的文件迁移工作流。

binhex 只保留 Macintosh 文件的 data fork，不保存 resource fork；文本还沿用旧 Mac CR 换行。
模块自 3.9 弃用，适合读取历史归档后迁往现代格式，不应成为新协议。binhex/hexbin 接受路径，
hexbin(output=None) 则信任归档内文件名并写到当前目录，调用前必须选定隔离目录。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.binhex.deprecated-since-3.9
# polyglot-covers: python.binhex.binhex
# polyglot-covers: python.binhex.hexbin
# polyglot-covers: python.binhex.file-path-roundtrip
# polyglot-covers: python.binhex.data-fork-only
# polyglot-covers: python.binhex.hexbin-output-none-embedded-filename
# polyglot-covers: python.binhex.output-none-current-directory-trap
# polyglot-covers: python.binhex.Error

import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    import binhex

import pytest


def test_explicit_input_encoded_and_output_paths_round_trip_data_fork(tmp_path):
    source = tmp_path / "source.bin"
    archive = tmp_path / "archive.hqx"
    decoded = tmp_path / "decoded.bin"
    payload = bytes(range(256))
    source.write_bytes(payload)

    assert binhex.binhex(str(source), str(archive)) is None
    assert archive.read_bytes().startswith(b"(This file must be converted with BinHex")
    assert binhex.hexbin(str(archive), str(decoded)) is None
    assert decoded.read_bytes() == payload


def test_output_none_uses_embedded_name_inside_an_isolated_directory(tmp_path, monkeypatch):
    source = tmp_path / "embedded-name.bin"
    archive = tmp_path / "archive.hqx"
    source.write_bytes(b"legacy")
    binhex.binhex(str(source), str(archive))
    source.unlink()

    monkeypatch.chdir(tmp_path)
    binhex.hexbin(str(archive), None)
    assert source.read_bytes() == b"legacy"


def test_invalid_binhex_document_raises_module_specific_error(tmp_path):
    invalid = tmp_path / "invalid.hqx"
    invalid.write_bytes(b"not binhex")
    with pytest.raises(binhex.Error):
        binhex.hexbin(str(invalid), str(tmp_path / "ignored.bin"))
