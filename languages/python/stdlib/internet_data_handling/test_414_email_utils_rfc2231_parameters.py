"""414｜RFC 2231 参数的编码、分段解码与最终 Unicode 折叠。

邮件参数用 charset'language'percent-encoded 形式承载非 ASCII filename。decode_rfc2231 只拆
charset/language/value，不负责 percent decoding；decode_params 会合并带 * 的连续参数，最后
由 collapse_rfc2231_value 按声明字符集生成 str。不要把任一中间元组直接展示给用户。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.utils.encode_rfc2231
# polyglot-covers: python.email.utils.encode-rfc2231-charset-language
# polyglot-covers: python.email.utils.decode_rfc2231
# polyglot-covers: python.email.utils.decode-rfc2231-does-not-percent-decode
# polyglot-covers: python.email.utils.decode_params
# polyglot-covers: python.email.utils.decode-params-star-parameter
# polyglot-covers: python.email.utils.collapse_rfc2231_value
# polyglot-covers: python.email.utils.collapse-rfc2231-nontuple-unquotes

from email.utils import (
    collapse_rfc2231_value,
    decode_params,
    decode_rfc2231,
    encode_rfc2231,
)


def test_rfc2231_encoder_and_low_level_decoder_keep_declared_metadata():
    encoded = encode_rfc2231("résumé.pdf", charset="utf-8", language="fr")
    assert encoded == "utf-8'fr'r%C3%A9sum%C3%A9.pdf"

    # 这里第三项仍是 percent-encoded；decode_rfc2231 的职责只是拆三段。
    assert decode_rfc2231(encoded) == (
        "utf-8",
        "fr",
        "r%C3%A9sum%C3%A9.pdf",
    )


def test_decode_params_and_collapse_form_the_complete_unicode_pipeline():
    decoded = decode_params(
        [
            ("attachment", ""),
            ("filename*", "utf-8''r%C3%A9sum%C3%A9.pdf"),
        ]
    )

    assert decoded[0] == ("attachment", "")
    name, structured_value = decoded[1]
    assert name == "filename"
    assert collapse_rfc2231_value(structured_value) == "résumé.pdf"
    assert collapse_rfc2231_value('"plain.txt"') == "plain.txt"
