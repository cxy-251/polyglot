# Current Task

ID: `python.stdlib.codecs`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `codecs` 测试套，围绕 codec registry、无状态/增量/流式编解码、Unicode 错误策略、BOM 和 Python 特有转换构建可查阅案例；讲清 text-to-bytes、bytes-to-bytes 与 text-to-text codec 的类型边界，并隔离注册表全局状态。

## Covers

- `codecs.encode()` / `codecs.decode()` 与 `str.encode()` / `bytes.decode()` 的常用关系；
- `lookup()` 返回的 `CodecInfo`，以及编码名称大小写、连字符、空格和下划线别名；
- 未知编码的 `LookupError`；
- `getencoder()` / `getdecoder()` 返回 `(output, consumed)` 的底层函数接口；
- `getincrementalencoder()` / `getincrementaldecoder()` 与分块输入；
- UTF-8 多字节字符跨 chunk 时的缓冲、`final=True`、`getstate()`、`setstate()` 和 `reset()`；
- `iterencode()` / `iterdecode()` 对迭代输入的增量处理；
- `getreader()` / `getwriter()` 在 `io.BytesIO` 上的 stream reader/writer；
- `codecs.open()` 的 Python 3.10 行为、底层二进制模式和不做自动换行转换；同时注明普通文本文件优先使用内置 `open()`；
- `EncodedFile()` 在两种字节编码之间透明转码，以及关闭 wrapper 会关闭原始流的所有权；
- `strict`、`ignore`、`replace`、`backslashreplace`、`xmlcharrefreplace`、`namereplace` 的适用方向与信息损失；
- `surrogateescape` 对未知原始字节的可逆往返，以及它不是普通 Unicode 文本；
- `register_error()` / `lookup_error()` 的 handler 参数、replacement 和继续位置协议；
- `BOM_UTF8` 与 `utf-8-sig` 的写入/消费行为；
- `BOM_UTF16_LE` / `BOM_UTF16_BE`、`utf-16` 与显式 endian codec 的差别；
- Python 特有 `base64_codec`（bytes-to-bytes）和 `rot_13`（text-to-text）的输入/输出类型；
- `iterencode()` 不适用于 bytes-to-bytes codec、`iterdecode()` 不适用于 text-to-text codec；
- `register()` 搜索函数接收规范化名称、返回 `CodecInfo` 或 `None`；
- Python 3.10 `unregister()` 移除搜索函数并清除 registry cache，确保测试不遗留全局 codec。

## Common Pitfalls To Explain

- 把 encoding 当作字符本身的属性，忽略“文本 ↔ 字节”必须由协议约定编码；
- 依赖平台默认编码，或把 `codecs` 的通用转换和普通 `str.encode()` 用途混淆；
- 用 `ignore` / `replace` 后仍假设原始数据可以无损恢复；
- 对拆开的 UTF-8 chunk 分别调用无状态 `decode()`，而不是复用 incremental decoder；
- 流结束时忘记 `final=True`，让残缺字节留在 decoder buffer；
- 把 UTF-8 BOM 当成所有 UTF-8 文件都必须有的字节，或用普通 `utf-8` 解码后意外保留 `U+FEFF`；
- 把 `utf-16-le` / `utf-16-be` 误认为会自动写入或消费 BOM；
- 假设所有 codec 都是 str-to-bytes，忽略 Python 特有 binary/text transforms；
- 注册全局 codec/error handler 后不清理，污染后续测试；
- 为普通文本文件优先使用 `codecs.open()`，忽略内置 `open()` / `io` 是官方推荐入口。

## Target File

`languages/python/stdlib/binary_data/test_042_codecs_registry_and_streams.py`

## Official Sources

- https://docs.python.org/3.10/library/codecs.html

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 标准库；
- 所有流使用 `io.BytesIO`，文件案例只使用 `tmp_path`；
- 自定义 codec search function 必须在 `try/finally` 中 `unregister()`；
- `register_error()` 没有对应 unregister，相关全局注册示例放在短生命周期子进程中；
- 增量案例必须真的把多字节字符拆在 chunk 边界，不能只把完整字符分批；
- 明确断言每类 codec 的输入和输出类型，不做庞大编码名称矩阵；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--040 已完成语言、内置层和前两类标准库首轮编写；041 `struct` 已在 `binary_data/` 完成首轮静态编写。全部 Python 文件仍未运行。下一步直接编写 042 `codecs`，注意 registry/error handler 的进程全局隔离；不要先运行 pytest。
