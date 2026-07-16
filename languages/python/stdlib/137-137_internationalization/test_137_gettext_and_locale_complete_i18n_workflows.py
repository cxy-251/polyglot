"""137｜gettext 消息目录与 locale 文化约定的完整国际化工作流。

gettext 负责应用消息翻译，locale 负责进程级文化约定。
案例自行构造 GNU MO；除短暂进入 C locale 外不依赖系统语言包。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.stdlib.gettext python.gettext.NullTranslations
# polyglot-covers: python.gettext.NullTranslations-fallback-chain
# polyglot-covers: python.gettext.GNUTranslations-little-and-big-endian
# polyglot-covers: python.gettext.mo-metadata python.gettext.mo-corruption-errors
# polyglot-covers: python.gettext.gettext python.gettext.ngettext-plural-rule
# polyglot-covers: python.gettext.pgettext python.gettext.npgettext
# polyglot-covers: python.gettext.find-language-expansion python.gettext.find-all
# polyglot-covers: python.gettext.find-environment-precedence
# polyglot-covers: python.gettext.translation python.gettext.translation-fallback
# polyglot-covers: python.gettext.translation-cache-copy python.gettext.class-parameter
# polyglot-covers: python.gettext.Catalog-alias python.gettext.install-builtins
# polyglot-covers: python.gettext.bindtextdomain python.gettext.textdomain
# polyglot-covers: python.gettext.dgettext-dngettext python.gettext.context-global-api
# polyglot-covers: python.gettext.deprecated-byte-api python.gettext.codeset-deprecation
# polyglot-covers: python.stdlib.locale python.locale.setlocale-query-and-restore
# polyglot-covers: python.locale.process-global-thread-safety python.locale.Error
# polyglot-covers: python.locale.localeconv python.locale.CHAR_MAX
# polyglot-covers: python.locale.nl_langinfo python.locale.DAY_1-sunday
# polyglot-covers: python.locale.strcoll python.locale.strxfrm
# polyglot-covers: python.locale.normalize python.locale.setlocale-iterable
# polyglot-covers: python.locale.getlocale python.locale.getdefaultlocale
# polyglot-covers: python.locale.getpreferredencoding python.locale.resetlocale
# polyglot-covers: python.locale.format_string python.locale.format-deprecated
# polyglot-covers: python.locale.localize python.locale.delocalize
# polyglot-covers: python.locale.atof python.locale.atoi python.locale.str
# polyglot-covers: python.locale.currency python.locale.monetary-conventions

import builtins
from contextlib import contextmanager
from decimal import Decimal
from io import BytesIO
import struct

import gettext
import locale
import pytest


CATALOG_METADATA = (
    "Project-Id-Version: polyglot 1\n"
    "Content-Type: text/plain; charset=UTF-8\n"
    "Plural-Forms: nplurals=3; "
    "plural=(n == 1 ? 0 : n == 2 ? 1 : 2);\n"
)


def teaching_messages(**extra):
    messages = {
        "": CATALOG_METADATA,
        "Hello": "你好",
        "apple\x00apples": "一个苹果\x00两个苹果\x00多个苹果",
        "menu\x04Open": "打开菜单",
        "cart\x04item\x00items": "一个项目\x00两个项目\x00多个项目",
    }
    messages.update(extra)
    return messages


def build_mo(messages, *, byteorder="<", version=0):
    """把 msgid/msgstr 映射编成 GNU MO；不依赖外部 msgfmt。"""

    encoded = sorted(
        (msgid.encode("utf-8"), msgstr.encode("utf-8"))
        for msgid, msgstr in messages.items()
    )
    count = len(encoded)
    original_table_offset = 7 * 4
    translated_table_offset = original_table_offset + count * 8
    original_data_offset = translated_table_offset + count * 8

    original_blob = b"".join(msgid + b"\x00" for msgid, _ in encoded)
    translated_data_offset = original_data_offset + len(original_blob)
    translated_blob = b"".join(msgstr + b"\x00" for _, msgstr in encoded)

    original_entries = []
    translated_entries = []
    original_cursor = original_data_offset
    translated_cursor = translated_data_offset
    for msgid, msgstr in encoded:
        original_entries.append(
            struct.pack(f"{byteorder}2I", len(msgid), original_cursor)
        )
        translated_entries.append(
            struct.pack(f"{byteorder}2I", len(msgstr), translated_cursor)
        )
        original_cursor += len(msgid) + 1
        translated_cursor += len(msgstr) + 1

    header = struct.pack(
        f"{byteorder}7I",
        0x950412DE,
        version,
        count,
        original_table_offset,
        translated_table_offset,
        0,
        0,
    )
    return (
        header
        + b"".join(original_entries)
        + b"".join(translated_entries)
        + original_blob
        + translated_blob
    )


def write_catalog(localedir, language, domain, messages):
    path = localedir / language / "LC_MESSAGES" / f"{domain}.mo"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build_mo(messages))
    return path


@contextmanager
def temporary_c_locale(category=locale.LC_ALL):
    """保存并恢复进程级 locale；切换期间其他线程也会看到 C。"""

    previous = locale.setlocale(category)
    try:
        locale.setlocale(category, "C")
        yield
    finally:
        locale.setlocale(category, previous)


def test_null_translations_is_identity_for_text_plural_and_context():
    translation = gettext.NullTranslations()

    assert translation.info() == {}
    assert translation.charset() is None
    assert translation.gettext("Hello") == "Hello"
    assert translation.ngettext("file", "files", 1) == "file"
    assert translation.ngettext("file", "files", 0) == "files"
    assert translation.pgettext("menu", "Open") == "Open"
    assert translation.npgettext("cart", "item", "items", 2) == "items"


def test_null_translation_forwards_missing_lookups_through_fallback():
    primary = gettext.NullTranslations()
    fallback = gettext.GNUTranslations(
        BytesIO(build_mo(teaching_messages()))
    )
    primary.add_fallback(fallback)

    assert primary.gettext("Hello") == "你好"
    assert primary.ngettext("apple", "apples", 2) == "两个苹果"
    assert primary.pgettext("menu", "Open") == "打开菜单"


@pytest.mark.parametrize("byteorder", ["<", ">"])
def test_gnu_translations_reads_both_mo_byte_orders(byteorder):
    translation = gettext.GNUTranslations(
        BytesIO(build_mo(teaching_messages(), byteorder=byteorder))
    )

    assert translation.gettext("Hello") == "你好"
    assert translation.gettext("Unknown") == "Unknown"


def test_gnu_translation_exposes_metadata_charset_and_three_plural_forms():
    translation = gettext.GNUTranslations(
        BytesIO(build_mo(teaching_messages()))
    )

    assert translation.info()["project-id-version"] == "polyglot 1"
    assert translation.charset() == "UTF-8"
    assert translation.ngettext("apple", "apples", 1) == "一个苹果"
    assert translation.ngettext("apple", "apples", 2) == "两个苹果"
    assert translation.ngettext("apple", "apples", 9) == "多个苹果"

    # 没有目录项时退回源语言的二分规则，不套用目录的三分规则。
    assert translation.ngettext("file", "files", 1) == "file"
    assert translation.ngettext("file", "files", 2) == "files"


def test_gnu_context_keys_distinguish_same_surface_message():
    translation = gettext.GNUTranslations(
        BytesIO(build_mo(teaching_messages()))
    )

    assert translation.pgettext("menu", "Open") == "打开菜单"
    assert translation.pgettext("door", "Open") == "Open"
    assert translation.npgettext("cart", "item", "items", 1) == "一个项目"
    assert translation.npgettext("cart", "item", "items", 2) == "两个项目"
    assert translation.npgettext("cart", "item", "items", 7) == "多个项目"


def test_gnu_translation_rejects_bad_magic_and_unsupported_major_version():
    with pytest.raises(OSError, match="Bad magic number"):
        gettext.GNUTranslations(BytesIO(b"not a message catalog"))

    unsupported = build_mo(
        {"": CATALOG_METADATA},
        version=2 << 16,
    )
    with pytest.raises(OSError, match="Bad version number"):
        gettext.GNUTranslations(BytesIO(unsupported))


def test_find_expands_specific_language_to_available_base_catalog(tmp_path):
    localedir = tmp_path / "locale"
    french = write_catalog(localedir, "fr", "app", teaching_messages())

    found = gettext.find(
        "app",
        str(localedir),
        languages=["fr_FR.UTF-8"],
    )

    assert found == str(french)
    assert gettext.find("missing", str(localedir), languages=["fr"]) is None


def test_find_all_preserves_language_priority_and_environment_search(tmp_path, monkeypatch):
    localedir = tmp_path / "locale"
    french = write_catalog(localedir, "fr", "app", teaching_messages())
    german = write_catalog(localedir, "de", "app", teaching_messages())

    assert gettext.find(
        "app",
        str(localedir),
        languages=["fr", "de"],
        all=True,
    ) == [str(french), str(german)]

    monkeypatch.setenv("LANGUAGE", "de:fr")
    monkeypatch.setenv("LC_ALL", "fr")
    assert gettext.find("app", str(localedir)) == str(german)


def test_translation_builds_ordered_fallbacks_from_multiple_catalogs(tmp_path):
    localedir = tmp_path / "locale"
    write_catalog(
        localedir,
        "fr",
        "app",
        {"": CATALOG_METADATA, "Hello": "Bonjour"},
    )
    write_catalog(
        localedir,
        "de",
        "app",
        {"": CATALOG_METADATA, "Only fallback": "Nur Ersatz"},
    )

    translation = gettext.translation(
        "app",
        str(localedir),
        languages=["fr", "de"],
    )

    assert translation.gettext("Hello") == "Bonjour"
    assert translation.gettext("Only fallback") == "Nur Ersatz"
    assert translation.gettext("Missing") == "Missing"


def test_translation_fallback_flag_and_catalog_alias(tmp_path):
    localedir = tmp_path / "empty-locale"

    fallback = gettext.translation(
        "missing",
        str(localedir),
        languages=["zz"],
        fallback=True,
    )
    assert isinstance(fallback, gettext.NullTranslations)

    with pytest.raises(FileNotFoundError):
        gettext.translation(
            "missing",
            str(localedir),
            languages=["zz"],
        )
    assert gettext.Catalog is gettext.translation


def test_translation_cache_returns_copies_with_shared_catalog_data(
    tmp_path,
    monkeypatch,
):
    localedir = tmp_path / "locale"
    write_catalog(localedir, "fr", "app", teaching_messages())
    monkeypatch.setattr(gettext, "_translations", {})

    first = gettext.translation("app", str(localedir), languages=["fr"])
    second = gettext.translation("app", str(localedir), languages=["fr"])

    assert first is not second
    assert first._catalog is second._catalog
    first.add_fallback(gettext.NullTranslations())
    assert second._fallback is None


def test_translation_accepts_a_custom_catalog_class(tmp_path, monkeypatch):
    class TeachingTranslations(gettext.GNUTranslations):
        parse_count = 0

        def _parse(self, fp):
            type(self).parse_count += 1
            super()._parse(fp)

    localedir = tmp_path / "locale"
    write_catalog(localedir, "fr", "app", teaching_messages())
    monkeypatch.setattr(gettext, "_translations", {})

    translation = gettext.translation(
        "app",
        str(localedir),
        languages=["fr"],
        class_=TeachingTranslations,
    )

    assert isinstance(translation, TeachingTranslations)
    assert translation.gettext("Hello") == "你好"
    assert TeachingTranslations.parse_count == 1


def test_translation_install_can_expose_selected_builtins(monkeypatch):
    translation = gettext.GNUTranslations(
        BytesIO(build_mo(teaching_messages()))
    )
    installed_names = ["_", "gettext", "ngettext", "pgettext", "npgettext"]
    for name in installed_names:
        monkeypatch.delattr(builtins, name, raising=False)

    translation.install(names=installed_names[1:])

    assert builtins._("Hello") == "你好"
    assert builtins.gettext("Hello") == "你好"
    assert builtins.ngettext("apple", "apples", 2) == "两个苹果"
    assert builtins.pgettext("menu", "Open") == "打开菜单"


def test_module_install_loads_domain_then_installs_global_aliases(
    tmp_path,
    monkeypatch,
):
    localedir = tmp_path / "locale"
    write_catalog(localedir, "zh", "app", teaching_messages())
    monkeypatch.setenv("LANGUAGE", "zh")
    monkeypatch.setattr(gettext, "_translations", {})
    monkeypatch.delattr(builtins, "_", raising=False)
    monkeypatch.delattr(builtins, "ngettext", raising=False)

    gettext.install("app", str(localedir), names=["ngettext"])

    assert builtins._("Hello") == "你好"
    assert builtins.ngettext("apple", "apples", 2) == "两个苹果"


def test_module_local_alias_avoids_mutating_builtins(monkeypatch):
    monkeypatch.delattr(builtins, "_", raising=False)
    translation = gettext.GNUTranslations(
        BytesIO(build_mo(teaching_messages()))
    )

    local_gettext = translation.gettext

    assert local_gettext("Hello") == "你好"
    assert not hasattr(builtins, "_")


def test_global_gettext_api_uses_bound_domain_and_environment_language(
    tmp_path,
    monkeypatch,
):
    localedir = tmp_path / "locale"
    write_catalog(localedir, "zh", "app", teaching_messages())
    monkeypatch.setenv("LANGUAGE", "zh")
    monkeypatch.setattr(gettext, "_localedirs", {})
    monkeypatch.setattr(gettext, "_translations", {})
    monkeypatch.setattr(gettext, "_current_domain", "messages")

    assert gettext.bindtextdomain("app", str(localedir)) == str(localedir)
    assert gettext.bindtextdomain("app") == str(localedir)
    assert gettext.textdomain("app") == "app"
    assert gettext.textdomain() == "app"

    assert gettext.gettext("Hello") == "你好"
    assert gettext.ngettext("apple", "apples", 2) == "两个苹果"
    assert gettext.pgettext("menu", "Open") == "打开菜单"
    assert gettext.npgettext("cart", "item", "items", 9) == "多个项目"
    assert gettext.dpgettext("app", "menu", "Open") == "打开菜单"
    assert gettext.dnpgettext("app", "cart", "item", "items", 2) == "两个项目"

    # 指定域找不到目录时，GNU 风格全局 API 返回源消息而不是抛错。
    assert gettext.dgettext("missing", "Same") == "Same"
    assert gettext.dngettext("missing", "one", "many", 3) == "many"


def test_deprecated_gettext_byte_api_remains_visible_in_python_310(tmp_path):
    localedir = tmp_path / "locale"
    write_catalog(localedir, "zh", "app", teaching_messages())

    with pytest.warns(DeprecationWarning, match="codeset"):
        translation = gettext.translation(
            "app",
            str(localedir),
            languages=["zh"],
            codeset="utf-8",
        )
    with pytest.warns(DeprecationWarning, match="lgettext"):
        translated = translation.lgettext("Hello")

    assert translated == "你好".encode("utf-8")


def test_bind_textdomain_codeset_is_deprecated_global_state(monkeypatch):
    monkeypatch.setattr(gettext, "_localecodesets", {})

    with pytest.warns(DeprecationWarning):
        assert gettext.bind_textdomain_codeset("app", "utf-8") == "utf-8"
    with pytest.warns(DeprecationWarning):
        assert gettext.bind_textdomain_codeset("app") == "utf-8"


def test_c_locale_is_portable_and_querying_does_not_change_it():
    with temporary_c_locale():
        before = locale.setlocale(locale.LC_ALL)
        assert locale.setlocale(locale.LC_ALL) == before
        assert locale.getlocale(locale.LC_NUMERIC) == (None, None)

        conventions = locale.localeconv()
        assert conventions["decimal_point"] == "."
        assert conventions["thousands_sep"] == ""
        assert isinstance(conventions["grouping"], list)
        assert conventions["frac_digits"] == locale.CHAR_MAX

        # 3.10.12 不拒绝 C locale 的 CHAR_MAX frac_digits，而会生成极长、没有货币符号的
        # 不可用字符串；这比抛错更隐蔽。C locale 适合协议数字，不适合 currency() 展示。
        formatted_currency = locale.currency(12.5)
        assert conventions["currency_symbol"] == ""
        assert len(formatted_currency) > 100
        assert locale.format_string("%.2f", 12.5) == "12.50"


def test_locale_switch_failure_leaves_current_setting_unchanged():
    before = locale.setlocale(locale.LC_ALL)

    with pytest.raises(locale.Error):
        locale.setlocale(locale.LC_ALL, "xx_YY.this-does-not-exist")

    assert locale.setlocale(locale.LC_ALL) == before


def test_setlocale_iterable_is_normalized_before_low_level_call(monkeypatch):
    calls = []

    def fake_setlocale(category, value=None):
        calls.append((category, value))
        return value or "C"

    monkeypatch.setattr(locale, "_setlocale", fake_setlocale)
    normalized = locale.normalize("de_DE.UTF-8")

    assert locale.setlocale(locale.LC_NUMERIC, ("de_DE", "UTF-8")) == normalized
    assert calls == [(locale.LC_NUMERIC, normalized)]

    with pytest.raises(TypeError, match="iterable of two strings"):
        locale.setlocale(locale.LC_NUMERIC, ("too", "many", "parts"))


def test_getlocale_parses_names_and_rejects_composite_lc_all(monkeypatch):
    monkeypatch.setattr(locale, "_setlocale", lambda category: "de_DE.UTF-8")
    assert locale.getlocale(locale.LC_NUMERIC) == ("de_DE", "UTF-8")

    composite = "LC_CTYPE=C;LC_NUMERIC=de_DE.UTF-8"
    monkeypatch.setattr(locale, "_setlocale", lambda category: composite)
    with pytest.raises(TypeError, match="LC_ALL is not supported"):
        locale.getlocale(locale.LC_ALL)


def test_normalize_known_alias_and_preserve_unknown_name():
    normalized = locale.normalize("de_DE.utf8")

    assert normalized.lower().startswith("de_de.")
    assert normalized.upper().endswith("UTF-8")
    unknown = "xx_YY.no-such-codec"
    assert locale.normalize(unknown) == unknown


def test_getdefaultlocale_reads_first_configured_environment(monkeypatch):
    monkeypatch.setenv("TEACH_LOCALE", "fr_FR.UTF-8")
    monkeypatch.setenv("LANG", "C")

    assert locale.getdefaultlocale(("TEACH_LOCALE", "LANG")) == (
        "fr_FR",
        "UTF-8",
    )
    assert isinstance(locale.getpreferredencoding(False), str)
    assert locale.getpreferredencoding(False)


def test_resetlocale_uses_default_tuple_and_selected_category(monkeypatch):
    calls = []
    monkeypatch.setattr(
        locale,
        "getdefaultlocale",
        lambda: ("fr_FR", "UTF-8"),
    )
    monkeypatch.setattr(
        locale,
        "_setlocale",
        lambda category, value: calls.append((category, value)),
    )

    locale.resetlocale(locale.LC_TIME)

    assert calls == [(locale.LC_TIME, "fr_FR.UTF-8")]


def test_nl_langinfo_exposes_c_locale_codeset_date_and_sunday_index():
    if not hasattr(locale, "nl_langinfo"):
        pytest.skip("platform does not expose nl_langinfo")

    with temporary_c_locale():
        assert isinstance(locale.nl_langinfo(locale.CODESET), str)
        assert "%" in locale.nl_langinfo(locale.D_FMT)
        # POSIX DAY_1 是星期日，不是 ISO 8601 的星期一。
        assert locale.nl_langinfo(locale.DAY_1) == "Sunday"


def test_c_locale_collation_and_transform_keys_agree():
    with temporary_c_locale(locale.LC_COLLATE):
        assert locale.strcoll("alpha", "beta") < 0
        assert locale.strcoll("same", "same") == 0

        values = ["beta", "alpha", "gamma"]
        assert sorted(values, key=locale.strxfrm) == [
            "alpha",
            "beta",
            "gamma",
        ]


def numeric_conventions():
    return {
        "decimal_point": ",",
        "thousands_sep": ".",
        "grouping": [3, 0],
        "mon_decimal_point": ",",
        "mon_thousands_sep": ".",
        "mon_grouping": [3, 0],
    }


def test_locale_numeric_format_localize_delocalize_and_parse(monkeypatch):
    monkeypatch.setattr(locale, "_override_localeconv", numeric_conventions())

    assert locale.format_string("%d", 1234567, grouping=True) == "1.234.567"
    assert locale.format_string("%.2f", 1234.5, grouping=True) == "1.234,50"
    assert locale.localize("-1234.50", grouping=True) == "-1.234,50"
    assert locale.delocalize("1.234,50") == "1234.50"
    assert locale.atof("1.234,50") == 1234.5
    assert locale.atof("1.234,50", Decimal) == Decimal("1234.50")
    assert locale.atoi("1.234") == 1234
    assert locale.str(3.5) == "3,5"


def test_format_string_handles_mappings_percent_and_deprecated_single_spec(monkeypatch):
    monkeypatch.setattr(locale, "_override_localeconv", numeric_conventions())

    formatted = locale.format_string(
        "%(amount).2f %%",
        {"amount": 1234.5},
        grouping=True,
    )
    assert formatted == "1.234,50 %"

    with pytest.warns(DeprecationWarning):
        assert locale.format("%.1f", 1234.5, grouping=True) == "1.234,5"
    with pytest.warns(DeprecationWarning):
        with pytest.raises(ValueError, match="exactly one"):
            locale.format("%.1f KiB", 1234.5)


def monetary_conventions():
    return {
        **numeric_conventions(),
        "currency_symbol": "€",
        "int_curr_symbol": "EUR",
        "frac_digits": 2,
        "int_frac_digits": 2,
        "positive_sign": "",
        "negative_sign": "-",
        "p_cs_precedes": 1,
        "n_cs_precedes": 1,
        "p_sep_by_space": 1,
        "n_sep_by_space": 1,
        "p_sign_posn": 1,
        "n_sign_posn": 1,
    }


def test_locale_currency_respects_symbol_grouping_sign_and_international(monkeypatch):
    monkeypatch.setattr(locale, "_override_localeconv", monetary_conventions())

    assert locale.currency(1234.5, grouping=True) == "€ 1.234,50"
    assert locale.currency(-1234.5, grouping=True) == "-€ 1.234,50"
    assert locale.currency(
        1234.5,
        grouping=True,
        international=True,
    ) == "EUR 1.234,50"
    assert locale.currency(-1234.5, symbol=False, grouping=True) == "-1.234,50"


def test_locale_monetary_flag_uses_monetary_separators(monkeypatch):
    conventions = numeric_conventions()
    conventions.update(
        {
            "decimal_point": ".",
            "thousands_sep": ",",
            "grouping": [3, 0],
        }
    )
    monkeypatch.setattr(locale, "_override_localeconv", conventions)

    assert locale.format_string(
        "%.2f",
        1234.5,
        grouping=True,
        monetary=False,
    ) == "1,234.50"
    assert locale.format_string(
        "%.2f",
        1234.5,
        grouping=True,
        monetary=True,
    ) == "1.234,50"
