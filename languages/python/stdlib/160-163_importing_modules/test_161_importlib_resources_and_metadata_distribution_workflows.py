"""161｜importlib.resources 与 importlib.metadata：包数据和发行版元数据。

可导入 package 与可安装 distribution 是两个层次：resources 从 package loader
读取随包数据，metadata 从 ``dist-info/egg-info`` 读取名称、版本、入口点和文件
清单。本套在临时目录中构造完整的 package、zip package 和 dist-info，避免依赖
容器中偶然安装的发行版，也展示“模块名不一定等于发行版名”的边界。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.importlib.resources
# polyglot-covers: python.importlib.resources.files python.resources.traversable
# polyglot-covers: python.resources.iterdir-joinpath-div
# polyglot-covers: python.resources.read-text-read-bytes-open
# polyglot-covers: python.resources.as-file python.resources.filesystem-resource
# polyglot-covers: python.resources.zip-resource python.resources.temporary-extraction
# polyglot-covers: python.resources.package-name-or-module
# polyglot-covers: python.resources.legacy-open-binary-open-text
# polyglot-covers: python.resources.legacy-read-binary-read-text
# polyglot-covers: python.resources.legacy-path
# polyglot-covers: python.resources.contents python.resources.is-resource
# polyglot-covers: python.resources.directory-not-resource
# polyglot-covers: python.importlib.resource-reader
# polyglot-covers: python.importlib.traversable python.importlib.traversable-resources
# polyglot-covers: python.stdlib.importlib.metadata
# polyglot-covers: python.metadata.version python.metadata.distribution
# polyglot-covers: python.metadata.package-not-found
# polyglot-covers: python.metadata.metadata-message python.metadata.json-3.10
# polyglot-covers: python.metadata.requires python.metadata.files
# polyglot-covers: python.metadata.package-path python.metadata.file-hash-size
# polyglot-covers: python.metadata.package-path-locate-read
# polyglot-covers: python.metadata.entry-point python.metadata.entry-point-load
# polyglot-covers: python.metadata.entry-points-select python.metadata.names-groups
# polyglot-covers: python.metadata.packages-distributions-3.10
# polyglot-covers: python.metadata.distributions python.metadata.path-distribution
# polyglot-covers: python.metadata.files-may-be-none
# polyglot-covers: python.metadata.distribution-finder
# polyglot-covers: python.metadata.find-distributions-context
# polyglot-covers: python.metadata.normalized-distribution-name

from contextlib import contextmanager
from importlib import abc
import importlib
from importlib import metadata
from importlib import resources
from io import BytesIO
from io import StringIO
from pathlib import Path
from pathlib import PurePosixPath
import sys
import zipfile

import pytest


@contextmanager
def without_new_modules(*prefixes):
    existing = set(sys.modules)
    try:
        yield
    finally:
        for name in list(sys.modules):
            if name in existing:
                continue
            if any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes):
                sys.modules.pop(name, None)


def build_resource_package(root, name="polyglot_resource_package"):
    package = root / name
    data = package / "data"
    data.mkdir(parents=True)
    (package / "__init__.py").write_text("PACKAGE_KIND = 'filesystem'\n", encoding="utf-8")
    (package / "message.txt").write_text("你好，resource!\n", encoding="utf-8")
    (package / "payload.bin").write_bytes(b"\x00\x01polyglot")
    (data / "nested.json").write_text('{"answer": 42}\n', encoding="utf-8")
    return package


def build_distribution(root, *, include_record=True):
    package = root / "polyglot_demo"
    dist_info = root / "polyglot_teaching-1.2.3.dist-info"
    package.mkdir()
    dist_info.mkdir()
    (package / "__init__.py").write_text(
        "def plugin(value=40):\n"
        "    return value + 2\n",
        encoding="utf-8",
    )
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.1\n"
        "Name: Polyglot-Teaching\n"
        "Version: 1.2.3\n"
        "Summary: A local metadata teaching distribution\n"
        "Requires-Python: >=3.10\n"
        "Requires-Dist: first-dependency>=1\n"
        "Requires-Dist: optional-dependency; extra == 'demo'\n"
        "Provides-Extra: demo\n"
        "Project-URL: Documentation, https://example.invalid/docs\n"
        "\n"
        "Long distribution description.\n",
        encoding="utf-8",
    )
    (dist_info / "entry_points.txt").write_text(
        "[polyglot.plugins]\n"
        "answer = polyglot_demo:plugin [demo]\n"
        "other = polyglot_demo:plugin\n",
        encoding="utf-8",
    )
    (dist_info / "top_level.txt").write_text("polyglot_demo\n", encoding="utf-8")
    if include_record:
        (dist_info / "RECORD").write_text(
            "polyglot_demo/__init__.py,sha256=YWJj,52\n"
            "polyglot_teaching-1.2.3.dist-info/METADATA,,\n"
            "polyglot_teaching-1.2.3.dist-info/entry_points.txt,,\n"
            "polyglot_teaching-1.2.3.dist-info/top_level.txt,,\n"
            "polyglot_teaching-1.2.3.dist-info/RECORD,,\n",
            encoding="utf-8",
        )
    return package, dist_info


class MemoryTraversable(abc.Traversable):
    def __init__(self, name, content=None, children=()):
        self._name = name
        self.content = content
        self.children = {child.name: child for child in children}

    @property
    def name(self):
        return self._name

    def iterdir(self):
        return iter(self.children.values())

    def is_dir(self):
        return self.content is None

    def is_file(self):
        return self.content is not None

    def joinpath(self, child):
        return self.children[child]

    def __truediv__(self, child):
        return self.joinpath(child)

    def open(self, mode="r", *args, **kwargs):
        if not self.is_file():
            raise IsADirectoryError(self.name)
        if mode == "rb":
            return BytesIO(self.content)
        if mode == "r":
            encoding = kwargs.get("encoding") or "utf-8"
            errors = kwargs.get("errors") or "strict"
            return StringIO(self.content.decode(encoding, errors))
        raise ValueError("resources are read-only")


class MemoryResourceReader(abc.TraversableResources):
    def __init__(self, root):
        self.root = root

    def files(self):
        return self.root


class MemoryDistribution(metadata.Distribution):
    def __init__(self, metadata_text, files=None):
        self._metadata_text = metadata_text
        self._files = files or {}

    def read_text(self, filename):
        if filename == "METADATA":
            return self._metadata_text
        return self._files.get(filename)

    def locate_file(self, path):
        return PurePosixPath("memory-distribution") / path


class MemoryDistributionFinder(metadata.DistributionFinder):
    def __init__(self, distribution):
        self.distribution = distribution
        self.contexts = []

    def find_distributions(self, context=metadata.DistributionFinder.Context()):
        self.contexts.append(context)
        if context.name is None or context.name in {
            "memory-teaching",
            "memory_teaching",
        }:
            yield self.distribution


def test_files_returns_traversable_for_package_name_or_module(tmp_path, monkeypatch):
    build_resource_package(tmp_path)
    monkeypatch.syspath_prepend(tmp_path)

    with without_new_modules("polyglot_resource_package"):
        package = importlib.import_module("polyglot_resource_package")
        by_module = resources.files(package)
        by_name = resources.files("polyglot_resource_package")

        assert by_module.name == "polyglot_resource_package"
        assert Path(str(by_module)) == Path(str(by_name))
        assert by_module.is_dir()
        assert not by_module.is_file()


def test_traversable_navigation_reads_top_level_and_nested_resources(tmp_path, monkeypatch):
    build_resource_package(tmp_path)
    monkeypatch.syspath_prepend(tmp_path)

    with without_new_modules("polyglot_resource_package"):
        root = resources.files("polyglot_resource_package")
        names = {child.name for child in root.iterdir()}
        message = root.joinpath("message.txt")
        payload = root / "payload.bin"
        nested = root / "data" / "nested.json"

        assert {"__init__.py", "message.txt", "payload.bin", "data"} <= names
        assert message.is_file()
        assert message.read_text(encoding="utf-8") == "你好，resource!\n"
        assert payload.read_bytes() == b"\x00\x01polyglot"
        assert nested.read_text() == '{"answer": 42}\n'
        with message.open("r", encoding="utf-8") as stream:
            assert stream.readline().strip() == "你好，resource!"


def test_as_file_provides_real_path_for_a_filesystem_resource(tmp_path, monkeypatch):
    build_resource_package(tmp_path)
    monkeypatch.syspath_prepend(tmp_path)

    with without_new_modules("polyglot_resource_package"):
        resource = resources.files("polyglot_resource_package") / "message.txt"
        with resources.as_file(resource) as path:
            assert isinstance(path, Path)
            assert path.exists()
            assert path.read_text(encoding="utf-8") == "你好，resource!\n"
        assert path.exists()
    # 文件系统资源无需提取，所以离开上下文后原文件仍存在。


def test_zip_resource_uses_same_traversable_api_and_as_file_extracts_temporarily(
    tmp_path,
    monkeypatch,
):
    archive = tmp_path / "resources.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("polyglot_zip_resources/__init__.py", "KIND = 'zip'\n")
        bundle.writestr("polyglot_zip_resources/message.txt", "from zip\n")
        bundle.writestr("polyglot_zip_resources/data/nested.txt", "nested\n")
    monkeypatch.syspath_prepend(archive)

    with without_new_modules("polyglot_zip_resources"):
        root = resources.files("polyglot_zip_resources")
        resource = root / "message.txt"
        assert resource.read_text() == "from zip\n"
        assert (root / "data" / "nested.txt").read_text() == "nested\n"

        with resources.as_file(resource) as extracted:
            extracted_path = extracted
            assert extracted_path.exists()
            assert extracted_path.read_text() == "from zip\n"
        assert not extracted_path.exists()
    # Traversable 不承诺是 pathlib.Path；需要传给只接受真实路径的 API 时，
    # 用 as_file，并且不要把临时提取路径保存到上下文之外。


def test_legacy_resource_functions_read_open_and_expose_context_managed_path(
    tmp_path,
    monkeypatch,
):
    build_resource_package(tmp_path)
    monkeypatch.syspath_prepend(tmp_path)

    with without_new_modules("polyglot_resource_package"):
        package = importlib.import_module("polyglot_resource_package")
        assert resources.read_text(package, "message.txt") == "你好，resource!\n"
        assert resources.read_binary(package, "payload.bin") == b"\x00\x01polyglot"

        with resources.open_text(package, "message.txt") as text_stream:
            assert text_stream.read().startswith("你好")
        with resources.open_binary(package, "payload.bin") as binary_stream:
            assert binary_stream.read(2) == b"\x00\x01"
        with resources.path(package, "message.txt") as path:
            assert path.read_text(encoding="utf-8") == "你好，resource!\n"


def test_contents_lists_nonrecursive_names_and_directories_are_not_resources(
    tmp_path,
    monkeypatch,
):
    build_resource_package(tmp_path)
    monkeypatch.syspath_prepend(tmp_path)

    with without_new_modules("polyglot_resource_package"):
        names = set(resources.contents("polyglot_resource_package"))
        assert {"message.txt", "payload.bin", "data"} <= names
        assert "nested.json" not in names
        assert resources.is_resource("polyglot_resource_package", "message.txt")
        assert not resources.is_resource("polyglot_resource_package", "data")
        assert not resources.is_resource("polyglot_resource_package", "missing.txt")

        with pytest.raises((ValueError, FileNotFoundError)):
            resources.read_text("polyglot_resource_package", "data/nested.json")
    # 旧 API 的 resource 参数只接收单个文件名；需要子目录时使用 files()。


def test_traversable_resources_adapts_files_tree_to_legacy_resource_reader_methods():
    root = MemoryTraversable(
        "package",
        children=(
            MemoryTraversable("message.txt", b"hello"),
            MemoryTraversable(
                "data",
                children=(MemoryTraversable("nested.txt", b"nested"),),
            ),
        ),
    )
    reader = MemoryResourceReader(root)

    assert issubclass(abc.TraversableResources, abc.ResourceReader)
    assert list(reader.contents()) == ["message.txt", "data"]
    assert reader.is_resource("message.txt") is True
    assert reader.is_resource("data") is False
    with reader.open_resource("message.txt") as stream:
        assert stream.read() == b"hello"
    with pytest.raises(FileNotFoundError):
        reader.resource_path("message.txt")
    # 内存/zip 资源没有永久文件系统路径，ResourceReader.resource_path 应失败；
    # files()+as_file 是新接口的可移植替代。


def test_version_distribution_and_metadata_read_local_dist_info(tmp_path, monkeypatch):
    build_distribution(tmp_path)
    monkeypatch.syspath_prepend(tmp_path)

    assert metadata.version("Polyglot-Teaching") == "1.2.3"
    assert metadata.version("polyglot_teaching") == "1.2.3"
    distribution = metadata.distribution("polyglot-teaching")
    package_metadata = metadata.metadata("polyglot-teaching")

    assert distribution.version == "1.2.3"
    assert distribution.metadata["Name"] == "Polyglot-Teaching"
    assert package_metadata["Summary"] == "A local metadata teaching distribution"
    assert package_metadata["Description"] == "Long distribution description.\n"
    assert package_metadata.json["name"] == "Polyglot-Teaching"
    assert package_metadata.json["requires_python"] == ">=3.10"


def test_missing_distribution_raises_package_not_found_with_requested_name(tmp_path):
    with pytest.raises(metadata.PackageNotFoundError) as captured:
        metadata.distribution("polyglot-distribution-that-does-not-exist")
    assert captured.value.name == "polyglot-distribution-that-does-not-exist"


def test_requires_returns_unparsed_requirement_lines(tmp_path, monkeypatch):
    build_distribution(tmp_path)
    monkeypatch.syspath_prepend(tmp_path)

    assert metadata.requires("polyglot-teaching") == [
        "first-dependency>=1",
        "optional-dependency; extra == 'demo'",
    ]
    # importlib.metadata 负责发现和读取，不解析版本约束；需要语义化
    # 匹配时交给 packaging.requirements 等专门工具。


def test_files_returns_package_paths_with_record_hash_size_and_distribution(
    tmp_path,
    monkeypatch,
):
    package, dist_info = build_distribution(tmp_path)
    monkeypatch.syspath_prepend(tmp_path)
    distribution = metadata.distribution("polyglot-teaching")
    paths = {str(path): path for path in metadata.files("polyglot-teaching")}

    module_path = paths["polyglot_demo/__init__.py"]
    assert isinstance(module_path, metadata.PackagePath)
    assert module_path.size == 52
    assert module_path.hash.mode == "sha256"
    assert module_path.hash.value == "YWJj"
    assert module_path.dist.metadata["Name"] == "Polyglot-Teaching"
    assert module_path.read_text(encoding="utf-8") == (package / "__init__.py").read_text(
        encoding="utf-8"
    )
    assert module_path.locate() == package / "__init__.py"

    metadata_path = paths["polyglot_teaching-1.2.3.dist-info/METADATA"]
    assert metadata_path.hash is None
    assert metadata_path.size is None
    assert metadata_path.locate() == dist_info / "METADATA"
    assert distribution.locate_file(module_path) == package / "__init__.py"


def test_files_returns_none_when_distribution_has_no_record_or_sources_list(
    tmp_path,
    monkeypatch,
):
    build_distribution(tmp_path, include_record=False)
    monkeypatch.syspath_prepend(tmp_path)
    assert metadata.files("polyglot-teaching") is None
    # 调用者不能无条件迭代 files()；旧安装格式可能根本没有文件清单。


def test_entry_point_exposes_components_extras_and_loads_target(tmp_path, monkeypatch):
    build_distribution(tmp_path)
    monkeypatch.syspath_prepend(tmp_path)

    entry_point = metadata.EntryPoint(
        name="answer",
        value="polyglot_demo:plugin [demo]",
        group="polyglot.plugins",
    )
    assert entry_point.name == "answer"
    assert entry_point.group == "polyglot.plugins"
    assert entry_point.module == "polyglot_demo"
    assert entry_point.attr == "plugin"
    assert entry_point.extras == ["demo"]

    with without_new_modules("polyglot_demo"):
        plugin = entry_point.load()
        assert plugin() == 42
        assert plugin(5) == 7


def test_entry_points_select_by_group_and_name_with_sequence_helpers(tmp_path, monkeypatch):
    build_distribution(tmp_path)
    monkeypatch.syspath_prepend(tmp_path)
    selected = metadata.entry_points(group="polyglot.plugins")

    assert isinstance(selected, metadata.EntryPoints)
    assert selected.names == {"answer", "other"}
    assert selected.groups == {"polyglot.plugins"}
    assert selected["answer"].value == "polyglot_demo:plugin [demo]"

    answer = selected.select(name="answer")
    assert len(answer) == 1
    assert answer[0].name == "answer"
    assert selected.select(name="missing") == metadata.EntryPoints()
    # Python 3.10 引入 selectable API；新代码应传 group/name 或调用 select，
    # 不依赖无参数 entry_points() 暂时保留的字典兼容视图。


def test_distribution_entry_points_property_matches_functional_selection(
    tmp_path,
    monkeypatch,
):
    build_distribution(tmp_path)
    monkeypatch.syspath_prepend(tmp_path)
    distribution = metadata.distribution("polyglot-teaching")

    assert distribution.entry_points.names == {"answer", "other"}
    assert distribution.entry_points["answer"].group == "polyglot.plugins"


def test_packages_distributions_uses_top_level_mapping_not_name_guessing(
    tmp_path,
    monkeypatch,
):
    build_distribution(tmp_path)
    monkeypatch.syspath_prepend(tmp_path)
    mapping = metadata.packages_distributions()

    assert mapping["polyglot_demo"] == ["Polyglot-Teaching"]
    assert "Polyglot-Teaching" not in mapping
    # distribution 名含连字符而 import package 用下划线，二者没有通用
    # 一一转换。


def test_distributions_path_filter_returns_path_distribution_objects(tmp_path):
    build_distribution(tmp_path)
    found = list(metadata.distributions(path=[str(tmp_path)]))

    assert len(found) == 1
    assert found[0].metadata["Name"] == "Polyglot-Teaching"
    assert found[0].version == "1.2.3"
    assert type(found[0]).__name__ == "PathDistribution"


def test_custom_distribution_finder_extends_metadata_beyond_filesystem(monkeypatch):
    distribution = MemoryDistribution(
        "Metadata-Version: 2.1\n"
        "Name: Memory-Teaching\n"
        "Version: 9.8.7\n"
        "Summary: metadata from an importer hook\n"
        "\n"
    )
    finder = MemoryDistributionFinder(distribution)
    monkeypatch.setattr(sys, "meta_path", [finder, *sys.meta_path])

    assert isinstance(finder, metadata.DistributionFinder)
    assert metadata.version("memory-teaching") == "9.8.7"
    found = metadata.distribution("memory_teaching")
    assert found is distribution
    assert found.metadata["Summary"] == "metadata from an importer hook"

    context = finder.contexts[-1]
    assert isinstance(context, metadata.DistributionFinder.Context)
    assert context.name == "memory_teaching"
    assert list(context.path) == list(sys.path)
    # DistributionFinder 同时是 MetaPathFinder；继承它可保留普通模块查找的
    # “未命中就继续”fallback，不会因只实现 find_distributions 而破坏 import。
