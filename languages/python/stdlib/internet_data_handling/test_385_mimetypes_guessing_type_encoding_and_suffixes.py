"""385｜从文件名/URL 猜 MIME type 与 Content-Encoding。

guess_type 只看名称后缀，不读取文件内容；返回的 encoding 是 gzip/compress 等
Content-Encoding，不是 MIME Content-Transfer-Encoding。encoding suffix 大小写敏感，type suffix
才会回退到不区分大小写。suffix_map 可先把 .tgz 这类复合简写展开，再分别识别 type 与 encoding。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mimetypes.guess_type
# polyglot-covers: python.mimetypes.guess-type-pathlike
# polyglot-covers: python.mimetypes.guess-type-url
# polyglot-covers: python.mimetypes.guess-type-unknown-none
# polyglot-covers: python.mimetypes.guess-type-does-not-inspect-content
# polyglot-covers: python.mimetypes.guess-type-type-and-encoding-tuple
# polyglot-covers: python.mimetypes.encoding-is-content-encoding
# polyglot-covers: python.mimetypes.encoding-suffix-case-sensitive
# polyglot-covers: python.mimetypes.type-suffix-case-insensitive-fallback
# polyglot-covers: python.mimetypes.suffix_map
# polyglot-covers: python.mimetypes.encodings_map
# polyglot-covers: python.mimetypes.compound-suffix-expansion

import mimetypes
from pathlib import Path


def test_common_filename_path_and_url_suffixes_are_recognized_without_file_io():
    assert mimetypes.guess_type("document.txt") == ("text/plain", None)
    assert mimetypes.guess_type(Path("missing.json")) == ("application/json", None)
    assert mimetypes.guess_type("https://example.invalid/image.png") == (
        "image/png",
        None,
    )
    assert mimetypes.guess_type("no-known-suffix.polyglot-unknown") == (None, None)


def test_isolated_database_separates_type_suffix_from_case_sensitive_encoding():
    database = mimetypes.MimeTypes()
    database.add_type("application/x-package", ".pkg")
    database.encodings_map[".zz"] = "demo-compression"
    database.suffix_map[".bundle"] = ".pkg.zz"

    assert database.guess_type("artifact.pkg.zz") == (
        "application/x-package",
        "demo-compression",
    )
    assert database.guess_type("artifact.PKG.zz") == (
        "application/x-package",
        "demo-compression",
    )
    assert database.guess_type("artifact.pkg.ZZ") == (None, None)
    assert database.guess_type("artifact.bundle") == (
        "application/x-package",
        "demo-compression",
    )


def test_builtin_tgz_mapping_reports_archive_type_and_transport_encoding():
    database = mimetypes.MimeTypes()
    assert database.suffix_map[".tgz"] == ".tar.gz"
    assert database.encodings_map[".gz"] == "gzip"
    assert database.guess_type("backup.tgz") == ("application/x-tar", "gzip")
