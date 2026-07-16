"""151｜distutils：Distribution/Command、文件选择、版本与编译计划。

``distutils`` 在 Python 3.10 已弃用并计划于 3.12 移除，
但阅读旧 setup.py、维护历史构建系统时仍会遇到。本套覆盖其对象模型和
纯本地工具，不实际调用 C 编译器或安装到解释器；新项目应采用当前
PyPA 工具链。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.stdlib.distutils python.distutils.deprecated-3.10
# polyglot-covers: python.distutils.distribution python.distutils.metadata
# polyglot-covers: python.distutils.distribution-feature-predicates
# polyglot-covers: python.distutils.extension python.distutils.extension-options
# polyglot-covers: python.distutils.command python.distutils.user-options
# polyglot-covers: python.distutils.command-initialize-finalize-run
# polyglot-covers: python.distutils.command-object-cache
# polyglot-covers: python.distutils.reinitialize-command
# polyglot-covers: python.distutils.set-undefined-options
# polyglot-covers: python.distutils.parse-command-line
# polyglot-covers: python.distutils.parse-config-files
# polyglot-covers: python.distutils.command-line-overrides-config
# polyglot-covers: python.distutils.command-validation-helpers
# polyglot-covers: python.distutils.filelist python.distutils.manifest-template
# polyglot-covers: python.distutils.include-pattern python.distutils.exclude-pattern
# polyglot-covers: python.distutils.translate-pattern
# polyglot-covers: python.distutils.text-file python.distutils.logical-lines
# polyglot-covers: python.distutils.fancy-getopt python.distutils.option-aliases
# polyglot-covers: python.distutils.strict-version python.distutils.loose-version
# polyglot-covers: python.distutils.version-predicate
# polyglot-covers: python.distutils.strtobool python.distutils.split-quoted
# polyglot-covers: python.distutils.subst-vars python.distutils.change-root
# polyglot-covers: python.distutils.byte-compile
# polyglot-covers: python.distutils.file-util python.distutils.dir-util
# polyglot-covers: python.distutils.dep-util python.distutils.archive-util
# polyglot-covers: python.distutils.ccompiler-new-compiler
# polyglot-covers: python.distutils.preprocess-options python.distutils.library-options
# polyglot-covers: python.distutils.compiler-state-only-no-compilation
# polyglot-covers: python.distutils.log-threshold python.distutils.dry-run
# polyglot-covers: python.distutils.errors

import warnings

with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message="The distutils package is deprecated",
        category=DeprecationWarning,
    )
    from distutils import log
from distutils.archive_util import ARCHIVE_FORMATS
from distutils.archive_util import check_archive_formats
from distutils.archive_util import make_archive
from distutils.ccompiler import gen_lib_options
from distutils.ccompiler import gen_preprocess_options
from distutils.ccompiler import new_compiler
from distutils.cmd import Command
from distutils.dep_util import newer
from distutils.dep_util import newer_group
from distutils.dep_util import newer_pairwise
from distutils.dir_util import copy_tree
from distutils.dist import Distribution
from distutils.errors import DistutilsFileError
from distutils.errors import DistutilsOptionError
from distutils.extension import Extension
from distutils.fancy_getopt import FancyGetopt
from distutils.file_util import copy_file
from distutils.file_util import move_file
from distutils.file_util import write_file
from distutils.filelist import FileList
from distutils.filelist import translate_pattern
from distutils.text_file import TextFile
from distutils.util import byte_compile
from distutils.util import change_root
from distutils.util import convert_path
from distutils.util import get_platform
from distutils.util import split_quoted
from distutils.util import strtobool
from distutils.util import subst_vars
from distutils.version import LooseVersion
from distutils.version import StrictVersion
from distutils.versionpredicate import VersionPredicate

import importlib.util
import os
from pathlib import Path
import zipfile

import pytest


class RecordCommand(Command):
    description = "record a message without touching installation state"
    user_options = [
        ("message=", "m", "message to record"),
        ("repeat=", "r", "number of repetitions"),
        ("tag=", None, "optional tag list"),
    ]

    def initialize_options(self):
        self.message = None
        self.repeat = None
        self.tag = None

    def finalize_options(self):
        if self.message is None:
            self.message = "default"
        if self.repeat is None:
            self.repeat = 1
        try:
            self.repeat = int(self.repeat)
        except (TypeError, ValueError) as error:
            raise DistutilsOptionError("repeat must be an integer") from error
        if self.repeat < 1:
            raise DistutilsOptionError("repeat must be positive")
        self.ensure_string_list("tag")

    def run(self):
        if not hasattr(self.distribution, "recorded_events"):
            self.distribution.recorded_events = []
        for _ in range(self.repeat):
            self.distribution.recorded_events.append((self.message, self.tag))


class ParentCommand(Command):
    user_options = [("shared=", None, "value inherited by a child command")]

    def initialize_options(self):
        self.shared = None

    def finalize_options(self):
        if self.shared is None:
            self.shared = "parent-default"

    def run(self):
        pass


class ChildCommand(Command):
    user_options = []

    def initialize_options(self):
        self.inherited = None

    def finalize_options(self):
        self.set_undefined_options("parent", ("shared", "inherited"))

    def run(self):
        pass


def make_distribution(**overrides):
    attributes = {
        "name": "polyglot-demo",
        "version": "1.2.0",
        "description": "distutils teaching distribution",
        "author": "Example Author",
        "author_email": "author@example.invalid",
        "url": "https://example.invalid/polyglot-demo",
        "license": "MIT",
        "packages": ["demo"],
        "py_modules": ["standalone"],
        "scripts": ["bin/demo"],
        "cmdclass": {
            "record": RecordCommand,
            "parent": ParentCommand,
            "child": ChildCommand,
        },
    }
    attributes.update(overrides)
    return Distribution(attributes)


def test_distribution_metadata_and_feature_predicates():
    distribution = make_distribution()
    metadata = distribution.metadata

    assert metadata.get_name() == "polyglot-demo"
    assert metadata.get_version() == "1.2.0"
    assert metadata.get_fullname() == "polyglot-demo-1.2.0"
    assert metadata.get_contact() == "Example Author"
    assert metadata.get_contact_email() == "author@example.invalid"
    assert metadata.get_url() == "https://example.invalid/polyglot-demo"
    assert metadata.get_license() == "MIT"

    assert distribution.has_pure_modules() is True
    assert distribution.has_modules() is True
    assert distribution.has_scripts() is True
    # 未配置 ext_modules 时旧 API 返回 None 而非规范 bool；谓词调用方应按真假值解释。
    assert distribution.has_ext_modules() is None
    assert distribution.is_pure() is True


def test_extension_records_build_inputs_without_invoking_a_compiler():
    extension = Extension(
        "demo._speedups",
        sources=["src/speedups.c", "src/helpers.c"],
        include_dirs=["include"],
        define_macros=[("FEATURE", "1"), ("TRACE", None)],
        undef_macros=["LEGACY"],
        library_dirs=["vendor/lib"],
        libraries=["example"],
        runtime_library_dirs=["runtime/lib"],
        extra_objects=["prebuilt/helper.o"],
        extra_compile_args=["-fno-strict-aliasing"],
        extra_link_args=["-Wl,--as-needed"],
        export_symbols=["PyInit__speedups"],
        depends=["include/schema.h"],
        language="c",
        optional=True,
    )
    distribution = make_distribution(ext_modules=[extension])

    assert extension.name == "demo._speedups"
    assert extension.sources == ["src/speedups.c", "src/helpers.c"]
    assert extension.define_macros == [("FEATURE", "1"), ("TRACE", None)]
    assert extension.undef_macros == ["LEGACY"]
    assert extension.libraries == ["example"]
    assert extension.language == "c"
    assert extension.optional is True
    assert distribution.has_ext_modules() is True
    assert distribution.is_pure() is False


def test_command_lifecycle_caches_objects_and_reinitializes_on_request():
    distribution = make_distribution()
    command = distribution.get_command_obj("record")

    assert isinstance(command, RecordCommand)
    assert command.distribution is distribution
    assert not command.finalized
    assert distribution.get_command_obj("record") is command

    command.message = "hello"
    command.repeat = "2"
    command.tag = "alpha,beta"
    distribution.run_command("record")

    assert command.finalized
    assert command.repeat == 2
    assert command.tag == ["alpha", "beta"]
    assert distribution.recorded_events == [
        ("hello", ["alpha", "beta"]),
        ("hello", ["alpha", "beta"]),
    ]

    fresh = distribution.reinitialize_command("record")
    assert fresh is command
    assert not fresh.finalized
    assert (fresh.message, fresh.repeat, fresh.tag) == (None, None, None)


def test_set_undefined_options_copies_only_values_the_child_did_not_set():
    distribution = make_distribution()
    parent = distribution.get_command_obj("parent")
    parent.shared = "from-parent"
    child = distribution.get_command_obj("child")

    child.ensure_finalized()
    assert parent.finalized
    assert child.inherited == "from-parent"

    child = distribution.reinitialize_command("child")
    child.inherited = "explicit-child"
    child.ensure_finalized()
    assert child.inherited == "explicit-child"


def test_parse_command_line_populates_options_and_runs_selected_commands():
    distribution = make_distribution()
    distribution.script_name = "setup.py"
    distribution.script_args = [
        "--verbose",
        "record",
        "--message=cli",
        "--repeat=2",
        "--tag=one,two",
    ]

    assert distribution.parse_command_line() is True
    assert distribution.commands == ["record"]
    assert distribution.verbose >= 1
    command = distribution.get_command_obj("record")
    assert command.message == "cli"
    assert command.repeat == "2"
    assert command.tag == "one,two"

    distribution.run_commands()
    assert distribution.recorded_events == [
        ("cli", ["one", "two"]),
        ("cli", ["one", "two"]),
    ]


def test_config_file_options_are_tagged_with_sources_and_cli_wins(tmp_path):
    configuration = tmp_path / "setup.cfg"
    configuration.write_text(
        """[global]\nverbose = 0\n\n[record]\nmessage = config\nrepeat = 3\ntag = cfg\n""",
        encoding="utf-8",
    )
    distribution = make_distribution()
    distribution.parse_config_files([str(configuration)])

    assert distribution.command_options["record"]["message"] == (
        str(configuration),
        "config",
    )
    assert distribution.command_options["record"]["repeat"] == (
        str(configuration),
        "3",
    )

    distribution.script_args = ["record", "--message=cli", "--repeat=1"]
    assert distribution.parse_command_line() is True
    command = distribution.get_command_obj("record")
    assert command.message == "cli"
    assert command.repeat == "1"
    assert command.tag == "cfg"


def test_command_validation_helpers_normalize_strings_lists_files_and_dirs(tmp_path):
    distribution = make_distribution()
    command = distribution.get_command_obj("record")
    existing_file = tmp_path / "record.txt"
    existing_file.write_text("data", encoding="utf-8")
    existing_dir = tmp_path / "records"
    existing_dir.mkdir()

    command.message = 42
    with pytest.raises(DistutilsOptionError, match="must be a string"):
        command.ensure_string("message")

    command.tag = "one, two three"
    command.ensure_string_list("tag")
    assert command.tag == ["one", "two", "three"]

    command.input_file = str(existing_file)
    command.input_dir = str(existing_dir)
    command.ensure_filename("input_file")
    command.ensure_dirname("input_dir")

    command.input_file = str(tmp_path / "missing.txt")
    with pytest.raises(DistutilsOptionError, match="does not exist"):
        command.ensure_filename("input_file")


def test_filelist_processes_manifest_rules_and_removes_duplicates(tmp_path, monkeypatch):
    (tmp_path / "pkg" / "docs").mkdir(parents=True)
    (tmp_path / "pkg" / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "pkg" / "docs" / "guide.txt").write_text(
        "guide\n",
        encoding="utf-8",
    )
    (tmp_path / "pkg" / "secret.txt").write_text("secret\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("readme\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    files = FileList()
    files.findall()
    assert set(files.allfiles) >= {
        "README.md",
        "pkg/module.py",
        "pkg/docs/guide.txt",
        "pkg/secret.txt",
    }

    assert files.include_pattern("*.md", anchor=True)
    files.process_template_line("recursive-include pkg *.py *.txt")
    files.process_template_line("exclude pkg/secret.txt")
    files.files.append("README.md")
    files.sort()
    files.remove_duplicates()

    assert files.files == [
        "README.md",
        "pkg/module.py",
        "pkg/docs/guide.txt",
    ]


def test_translate_pattern_builds_anchored_and_prefix_aware_regular_expressions():
    anchored = translate_pattern("*.py", anchor=True)
    under_package = translate_pattern("*.txt", anchor=False, prefix="pkg/docs")

    assert anchored.match("module.py")
    assert not anchored.match("pkg/module.py")
    assert under_package.match("pkg/docs/guide.txt")
    assert not under_package.match("other/guide.txt")


def test_textfile_turns_physical_lines_into_clean_logical_lines(tmp_path):
    source = tmp_path / "options.txt"
    # 显式生成反斜杠 + newline，避免 Python 字符串词法层先吞掉 TextFile 的续行标记。
    source.write_text(
        "# full-line comment\n"
        "alpha = one \\\n"
        "    two   # trailing comment\n"
        "\n"
        " beta = three\n",
        encoding="utf-8",
    )

    reader = TextFile(
        filename=str(source),
        strip_comments=True,
        skip_blanks=True,
        join_lines=True,
        lstrip_ws=True,
        rstrip_ws=True,
        collapse_join=True,
    )
    try:
        assert reader.readlines() == ["alpha = one two", "beta = three"]
        # full-line comment 在计数递增前被 continue；current_line 是清洗器内部位置，不是原文件
        # 的可靠物理行号。续行和空白处理后此处为 4。
        assert reader.current_line == 4
    finally:
        reader.close()


def test_fancy_getopt_supports_short_options_aliases_and_help_text():
    parser = FancyGetopt(
        [
            ("verbose", "v", "show details"),
            ("quiet", "q", "hide details"),
            ("output=", "o", "write to DIR"),
            ("silent", None, "alias for --quiet"),
        ]
    )
    parser.set_aliases({"silent": "quiet"})
    remaining, options = parser.getopt(["-v", "--output", "dist", "input.py"])

    assert remaining == ["input.py"]
    assert options.verbose == 1
    assert options.output == "dist"
    help_lines = parser.generate_help("usage: build [options]")
    assert help_lines[0] == "usage: build [options]"
    assert any("--output" in line and "-o" in line for line in help_lines)

    remaining, aliased = parser.getopt(["--silent"])
    assert remaining == []
    assert aliased.quiet == 1


def test_versions_and_version_predicate_expose_legacy_comparison_rules():
    assert StrictVersion("1.2") == StrictVersion("1.2.0")
    assert StrictVersion("1.2a1") < StrictVersion("1.2b1")
    assert StrictVersion("1.2b1") < StrictVersion("1.2")
    with pytest.raises(ValueError, match="invalid version number"):
        StrictVersion("1.2.dev1")

    assert LooseVersion("1.2.10") > LooseVersion("1.2.2")
    assert LooseVersion("2026.07") == LooseVersion("2026.7")

    # legacy 包名语法只接受标识符/点，不接受现代发行名常见的 hyphen。
    predicate = VersionPredicate("polyglot_demo (>=1.2, <2.0)")
    assert predicate.name == "polyglot_demo"
    assert predicate.satisfied_by(StrictVersion("1.5")) is True
    assert predicate.satisfied_by(StrictVersion("2.0")) is False
    assert str(predicate) == "polyglot_demo (>= 1.2, < 2.0)"


def test_boolean_shell_word_and_variable_helpers_have_strict_boundaries():
    assert strtobool("yes") == 1
    assert strtobool("ON") == 1
    assert strtobool("0") == 0
    assert strtobool("false") == 0
    with pytest.raises(ValueError, match="invalid truth value"):
        strtobool("perhaps")

    assert split_quoted("alpha 'two words' three\\ four") == [
        "alpha",
        "two words",
        "three four",
    ]
    variables = {"name": "demo", "version": "1.2"}
    assert subst_vars("$name-$version", variables) == "demo-1.2"
    # distutils 只支持 $name，不支持 shell 风格 ${name}。
    assert subst_vars("$name-${version}", variables) == "demo-${version}"
    with pytest.raises(ValueError, match="invalid variable"):
        subst_vars("$missing", {})


def test_path_platform_and_byte_compile_helpers_stay_inside_tmp_path(tmp_path):
    assert convert_path("pkg/module.py").endswith(os.path.join("pkg", "module.py"))
    assert isinstance(get_platform(), str)
    assert get_platform()

    rooted = change_root(str(tmp_path), os.path.abspath(os.path.join("etc", "demo")))
    assert Path(rooted).is_relative_to(tmp_path)

    source = tmp_path / "compiled.py"
    source.write_text("VALUE = 42\n", encoding="utf-8")
    byte_compile([str(source)], optimize=0, force=True, direct=True)
    cache = Path(importlib.util.cache_from_source(str(source), optimization=""))
    assert cache.exists()
    assert cache.parent == tmp_path / "__pycache__"


def test_file_directory_dependency_and_archive_utilities_form_a_local_workflow(
    tmp_path,
):
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()
    original = source_dir / "record.txt"
    original.write_text("alpha\n", encoding="utf-8")

    copied_path, copied = copy_file(
        str(original),
        str(target_dir / "record.txt"),
        preserve_mode=True,
    )
    assert copied == 1
    assert Path(copied_path).read_text(encoding="utf-8") == "alpha\n"

    write_file(str(source_dir / "lines.txt"), ["one", "two"])
    copied_tree = copy_tree(str(source_dir), str(target_dir), update=False)
    assert str(target_dir / "lines.txt") in copied_tree

    moved = move_file(str(target_dir / "lines.txt"), str(target_dir / "moved.txt"))
    assert Path(moved).read_text(encoding="utf-8") == "one\ntwo\n"

    # 这些 legacy helper 返回整数 0/1，不保证 bool 单例。
    assert newer(str(original), str(target_dir / "missing.txt")) == 1
    assert newer_group([str(original)], str(target_dir / "missing.txt")) == 1
    sources, targets = newer_pairwise(
        [str(original)],
        [str(target_dir / "missing.txt")],
    )
    assert sources == [str(original)]
    assert targets == [str(target_dir / "missing.txt")]

    archive_base = tmp_path / "release"
    archive = make_archive(
        str(archive_base),
        "zip",
        root_dir=str(tmp_path),
        base_dir="source",
    )
    assert Path(archive).exists()
    with zipfile.ZipFile(archive) as bundle:
        assert "source/record.txt" in bundle.namelist()

    assert "zip" in ARCHIVE_FORMATS
    assert check_archive_formats(["zip", "gztar"]) is None
    assert check_archive_formats(["not-a-format"]) == "not-a-format"


def test_compiler_factory_and_option_generators_only_plan_commands(tmp_path):
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="The distutils.sysconfig module is deprecated",
            category=DeprecationWarning,
        )
        compiler = new_compiler(compiler="unix", dry_run=True, force=True)
    compiler.add_include_dir(str(tmp_path / "include"))
    compiler.add_library_dir(str(tmp_path / "lib"))
    compiler.define_macro("FEATURE", "1")
    compiler.undefine_macro("LEGACY")

    preprocess = gen_preprocess_options(
        [("FEATURE", "1"), ("TRACE", None), ("LEGACY",)],
        [str(tmp_path / "include")],
    )
    assert "-DFEATURE=1" in preprocess
    assert "-DTRACE" in preprocess
    assert "-ULEGACY" in preprocess
    assert f"-I{tmp_path / 'include'}" in preprocess

    libraries = gen_lib_options(
        compiler,
        [str(tmp_path / "lib")],
        [str(tmp_path / "runtime")],
        ["example"],
    )
    assert any(option.startswith("-L") for option in libraries)
    assert "-lexample" in libraries
    assert compiler.dry_run is True
    assert compiler.include_dirs == [str(tmp_path / "include")]
    # 没有调用 compile/link；示例可在没有工具链的容器中静态学习命令规划。


def test_distutils_log_threshold_is_process_global_and_must_be_restored(capsys):
    previous = log.set_threshold(log.DEBUG)
    try:
        log.debug("debug %s", "message")
        log.info("info message")
    finally:
        log.set_threshold(previous)

    output = capsys.readouterr().out
    assert "debug message" in output
    assert "info message" in output


def test_file_helpers_report_missing_sources_with_distutils_errors(tmp_path):
    with pytest.raises(DistutilsFileError, match="can't copy"):
        copy_file(
            str(tmp_path / "missing.txt"),
            str(tmp_path / "target.txt"),
        )
