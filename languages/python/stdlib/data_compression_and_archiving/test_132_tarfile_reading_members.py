"""132｜TAR 成员索引、顺序迭代、``extractfile`` 与损坏/拼接归档读取。

TAR 允许重复成员名，``getmember`` 选择最后一次出现；``getmembers``/``getnames`` 保持
物理顺序。``extractfile`` 只返回 file-like payload，不写磁盘，并能解析 hard-link target。
``ignore_zeros`` 可恢复拼接或部分损坏归档，但不应作为默认容错策略。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.tarfile.getmember python.tarfile.duplicate-members
# polyglot-covers: python.tarfile.getmembers python.tarfile.getnames
# polyglot-covers: python.tarfile.member-order python.tarfile.member-mutation
# polyglot-covers: python.tarfile.next python.tarfile.iteration
# polyglot-covers: python.tarfile.list python.tarfile.list-members
# polyglot-covers: python.tarfile.extractfile python.tarfile.extractfile-buffered
# polyglot-covers: python.tarfile.extractfile-directory python.tarfile.extractfile-link
# polyglot-covers: python.tarfile.extractfile-missing python.tarfile.ignore-zeros
# polyglot-covers: python.tarfile.concatenated-archive python.tarfile.tarinfo-factory

import copy
import io
import tarfile

import pytest


def _add_bytes(archive, name, payload):
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    archive.addfile(info, io.BytesIO(payload))


def _build_archive(*members):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        for name, payload in members:
            _add_bytes(archive, name, payload)
    return buffer.getvalue()


def test_getmember_uses_the_last_occurrence_of_a_duplicate_name():
    """更新式 TAR 可重复保存同名成员；名称 lookup 视最后一份为最新版本。"""

    raw = _build_archive(
        ("same.txt", b"first"),
        ("other.txt", b"other"),
        ("same.txt", b"latest"),
    )
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        all_versions = [info for info in archive.getmembers() if info.name == "same.txt"]
        latest = archive.getmember("same.txt")
        member = archive.extractfile(latest)

        assert latest is all_versions[-1]
        assert member is not None
        assert member.read() == b"latest"
        with pytest.raises(KeyError, match="missing.txt"):
            archive.getmember("missing.txt")


def test_getmembers_and_getnames_preserve_physical_order():
    """list 结果不是去重索引；审计/安全预检必须检查每一次出现。"""

    raw = _build_archive(
        ("second.txt", b"2"),
        ("first.txt", b"1"),
        ("second.txt", b"updated"),
    )
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        members = archive.getmembers()
        assert archive.getnames() == ["second.txt", "first.txt", "second.txt"]
        assert [info.name for info in members] == archive.getnames()


def test_next_and_iteration_walk_members_sequentially():
    """next 返回 TarInfo/None；for archive 是同一顺序协议的惯用形式。"""

    raw = _build_archive(("a.txt", b"a"), ("b.txt", b"b"))
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        assert archive.next().name == "a.txt"
        assert archive.next().name == "b.txt"
        assert archive.next() is None

    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        assert [info.name for info in archive] == ["a.txt", "b.txt"]


def test_list_supports_compact_output_and_member_subset(capsys):
    """list 是人读输出；members 接 TarInfo 子集，结构化处理仍应使用 getmembers。"""

    raw = _build_archive(("first.txt", b"1"), ("second.txt", b"22"))
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        selected = [archive.getmember("second.txt")]
        archive.list(verbose=False, members=selected)

    output = capsys.readouterr().out
    assert output.strip() == "second.txt"


def test_extractfile_returns_a_buffered_reader_for_regular_content():
    """TarInfo 只有 offset/size metadata；extractfile 才创建按成员边界读取的 BufferedReader。"""

    raw = _build_archive(("lines.txt", b"first\nsecond\n"))
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        member = archive.extractfile("lines.txt")

        assert isinstance(member, io.BufferedReader)
        assert member.readline() == b"first\n"
        assert member.read() == b"second\n"


def test_extractfile_returns_none_for_a_directory():
    """directory/device 等无普通 payload 的成员返回 None，不返回空 BytesIO。"""

    buffer = io.BytesIO()
    directory = tarfile.TarInfo("empty/")
    directory.type = tarfile.DIRTYPE
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        archive.addfile(directory)

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        assert archive.extractfile("empty/") is None
        with pytest.raises(KeyError, match="missing"):
            archive.extractfile("missing")


def test_extractfile_resolves_a_hard_link_to_its_archived_target():
    """LNKTYPE 没有重复 payload；extractfile 根据 archive-root-relative linkname 找目标。"""

    buffer = io.BytesIO()
    target = tarfile.TarInfo("target.txt")
    target.size = len(b"shared")
    link = tarfile.TarInfo("alias.txt")
    link.type = tarfile.LNKTYPE
    link.linkname = "target.txt"
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        archive.addfile(target, io.BytesIO(b"shared"))
        archive.addfile(link)

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        member = archive.extractfile("alias.txt")
        assert member is not None
        assert member.read() == b"shared"


def test_ignore_zeros_reads_a_second_concatenated_archive():
    """默认首个 zero block 即 EOF；ignore_zeros=True 跳过 padding 继续搜索后续 header。"""

    concatenated = _build_archive(("first.txt", b"first")) + _build_archive(
        ("second.txt", b"second")
    )

    with tarfile.open(fileobj=io.BytesIO(concatenated), mode="r:") as archive:
        assert archive.getnames() == ["first.txt"]
    with tarfile.open(
        fileobj=io.BytesIO(concatenated),
        mode="r:",
        ignore_zeros=True,
    ) as archive:
        assert archive.getnames() == ["first.txt", "second.txt"]


def test_mutating_cached_tarinfo_changes_subsequent_archive_views():
    """getmember/getmembers 返回 archive 持有的对象；只想展示修改时先 copy。"""

    raw = _build_archive(("member.txt", b"content"))
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        cached = archive.getmember("member.txt")
        detached = copy.copy(cached)
        detached.mode = 0o600
        assert archive.getmember("member.txt").mode != 0o600

        cached.mode = 0o640
        assert archive.getmembers()[0].mode == 0o640


def test_tarinfo_constructor_argument_customizes_read_member_objects():
    """tarinfo factory 支持附加领域行为；解析出来的每个 member 都是该 subclass。"""

    class TaggedTarInfo(tarfile.TarInfo):
        def display_name(self):
            return f"tar:{self.name}"

    raw = _build_archive(("member.txt", b"content"))
    with tarfile.open(
        fileobj=io.BytesIO(raw),
        mode="r:",
        tarinfo=TaggedTarInfo,
    ) as archive:
        info = archive.getmembers()[0]
        assert isinstance(info, TaggedTarInfo)
        assert info.display_name() == "tar:member.txt"
