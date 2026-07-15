"""405｜MIMEApplication、MIMEImage、MIMEAudio、MIMEMessage 等便捷类。

专用 MIME 类设置 maintype/subtype，并默认以 base64 编码二进制数据。图片和音频可尝试
从内容猜 subtype，但不认识的字节必须显式给出 subtype；MIMEMessage 的 payload 必须是
Message。_encoder 是扩展点，负责同时改 payload 和 Content-Transfer-Encoding header。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.mime.MIMEApplication
# polyglot-covers: python.email.mime.MIMEApplication-default-subtype
# polyglot-covers: python.email.mime.specialized-default-base64
# polyglot-covers: python.email.mime.MIMEImage
# polyglot-covers: python.email.mime.MIMEImage-explicit-subtype
# polyglot-covers: python.email.mime.MIMEImage-undetectable-type-error
# polyglot-covers: python.email.mime.MIMEAudio
# polyglot-covers: python.email.mime.MIMEAudio-explicit-subtype
# polyglot-covers: python.email.mime.MIMEAudio-undetectable-type-error
# polyglot-covers: python.email.mime.MIMEMessage
# polyglot-covers: python.email.mime.MIMEMessage-message-only
# polyglot-covers: python.email.mime.custom-encoder-protocol

from email.message import Message
from email.mime.application import MIMEApplication
from email.mime.audio import MIMEAudio
from email.mime.image import MIMEImage
from email.mime.message import MIMEMessage

import pytest


def test_binary_mime_classes_set_types_and_default_to_base64():
    raw = b"\x00\xffpayload"
    application = MIMEApplication(raw)
    image = MIMEImage(raw, _subtype="x-demo")
    audio = MIMEAudio(raw, _subtype="x-demo")

    assert application.get_content_type() == "application/octet-stream"
    assert image.get_content_type() == "image/x-demo"
    assert audio.get_content_type() == "audio/x-demo"
    for part in (application, image, audio):
        assert part["Content-Transfer-Encoding"] == "base64"
        assert part.get_payload(decode=True) == raw


def test_image_and_audio_require_a_subtype_when_the_bytes_are_not_recognized():
    with pytest.raises(TypeError):
        MIMEImage(b"not an image")
    with pytest.raises(TypeError):
        MIMEAudio(b"not audio")


def test_mime_message_wraps_a_message_and_rejects_arbitrary_payloads():
    inner = Message()
    inner["Subject"] = "nested"
    wrapped = MIMEMessage(inner)

    assert wrapped.get_content_type() == "message/rfc822"
    assert wrapped.is_multipart() is True
    assert wrapped.get_payload() == [inner]
    with pytest.raises(TypeError):
        MIMEMessage("not a Message")


def test_specialized_class_accepts_a_custom_encoder_protocol():
    def encode_as_hex(message):
        raw = message.get_payload(decode=True)
        message.set_payload(raw.hex())
        message["Content-Transfer-Encoding"] = "x-hex"

    part = MIMEApplication(b"\x00\xff", _encoder=encode_as_hex)
    assert part.get_payload() == "00ff"
    assert part["Content-Transfer-Encoding"] == "x-hex"
