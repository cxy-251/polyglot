"""395｜BytesFeedParser/FeedParser 的任意 chunk 边界与 close 语义。

增量 parser 可接收 partial line、混合 CR/LF/CRLF，并把跨 chunk 的 header/body 拼回同一语义；
只有 close 才返回根消息。适合 socket 等阻塞来源，但 feed 本身不负责网络读取。_factory 每创建
一个 root 或 MIME subpart 调用一次；显式 policy 仍决定 header 与 message 类型。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.parser.BytesFeedParser
# polyglot-covers: python.email.parser.FeedParser
# polyglot-covers: python.email.feedparser.feed
# polyglot-covers: python.email.feedparser.close
# polyglot-covers: python.email.feedparser-partial-lines
# polyglot-covers: python.email.feedparser-mixed-line-endings
# polyglot-covers: python.email.feedparser-arbitrary-chunk-boundaries
# polyglot-covers: python.email.feedparser-policy
# polyglot-covers: python.email.feedparser-factory-per-message-part
# polyglot-covers: python.email.feedparser-close-returns-root

from email import policy
from email.message import EmailMessage
from email.parser import BytesFeedParser, FeedParser


RAW = (
    b"Subject: chunked\r\nContent-Type: multipart/mixed; boundary=x\n\r\n"
    b"--x\r\nContent-Type: text/plain\n\nfirst part\r\n--x--\n"
)


def test_bytes_feed_parser_stitches_partial_lines_and_mixed_endings():
    parser = BytesFeedParser(policy=policy.default)
    cuts = (1, 7, 19, 38, 57, len(RAW))
    start = 0
    for end in cuts:
        assert parser.feed(RAW[start:end]) is None
        start = end

    message = parser.close()
    assert isinstance(message, EmailMessage)
    assert str(message["Subject"]) == "chunked"
    assert message.is_multipart() is True
    assert list(message.iter_parts())[0].get_content().strip() == "first part"


def test_factory_is_used_for_root_and_each_mime_subpart():
    created = []

    def factory():
        message = EmailMessage(policy=policy.default)
        created.append(message)
        return message

    parser = BytesFeedParser(_factory=factory, policy=policy.default)
    parser.feed(RAW)
    root = parser.close()
    assert root is created[0]
    assert len(created) == 2
    assert list(root.iter_parts())[0] is created[1]


def test_text_feed_parser_accepts_str_but_is_best_reserved_for_ascii_messages():
    parser = FeedParser(policy=policy.default)
    parser.feed("Subject: text\n\nbo")
    parser.feed("dy\n")
    message = parser.close()
    assert isinstance(message, EmailMessage)
    assert message.get_content() == "body\n"
