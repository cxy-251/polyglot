"""145｜doctest 与 unittest：示例解析、套件、fixture、断言和运行结果。

``doctest`` 把交互式会话变成精确的文本契约，``unittest`` 则把 TestCase、
TestSuite、fixture 和 TestResult 组成可编程运行模型。两者都会产出 unittest
兼容套件，因此合并为从轻量文档示例到结构化测试的完整工作流。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.doctest python.doctest.interactive-example-contract
# polyglot-covers: python.doctest.doc-test-parser python.doctest.example-options
# polyglot-covers: python.doctest.blankline python.doctest.ellipsis
# polyglot-covers: python.doctest.normalize-whitespace python.doctest.skip
# polyglot-covers: python.doctest.ignore-exception-detail
# polyglot-covers: python.doctest.output-checker python.doctest.register-optionflag
# polyglot-covers: python.doctest.doc-test-runner python.doctest.test-results
# polyglot-covers: python.doctest.debug-runner-failures
# polyglot-covers: python.doctest.testmod python.doctest.doc-test-finder
# polyglot-covers: python.doctest.extraglobs-copy-boundary
# polyglot-covers: python.doctest.doc-file-suite python.doctest.testfile
# polyglot-covers: python.doctest.script-from-examples
# polyglot-covers: python.stdlib.unittest python.unittest.test-case
# polyglot-covers: python.unittest.setup-teardown-cleanup-order
# polyglot-covers: python.unittest.cleanup-after-setup-failure
# polyglot-covers: python.unittest.class-fixtures
# polyglot-covers: python.unittest.module-fixtures python.unittest.discovery
# polyglot-covers: python.unittest.test-loader python.unittest.test-suite
# polyglot-covers: python.unittest.load-tests-protocol python.unittest.function-test-case
# polyglot-covers: python.unittest.assertion-families
# polyglot-covers: python.unittest.assert-raises-warns-logs-contexts
# polyglot-covers: python.unittest.subtest-independent-results
# polyglot-covers: python.unittest.skip python.unittest.expected-failure
# polyglot-covers: python.unittest.unexpected-success
# polyglot-covers: python.unittest.text-test-runner python.unittest.test-result
# polyglot-covers: python.unittest.failfast python.unittest.buffer
# polyglot-covers: python.unittest.isolated-asyncio-test-case

import asyncio
import doctest
from io import StringIO
import logging
import sys
import types
import unittest
import warnings

import pytest


def run_suite(suite, **runner_options):
    """把 unittest 输出留在内存中，供外层 pytest 案例检查。"""

    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2, **runner_options)
    return runner.run(suite), stream.getvalue()


def test_doctest_parser_preserves_source_want_and_per_example_options():
    source = r'''
普通说明不会执行。

>>> total = 2 + 3
>>> print(total)
5
>>> print("top\n\nbottom")
top
<BLANKLINE>
bottom
>>> object()  # doctest: +ELLIPSIS
<object object at 0x...>
>>> print("ignored")  # doctest: +SKIP
this expected output is deliberately irrelevant
'''

    parser = doctest.DocTestParser()
    examples = parser.get_examples(source, name="lesson")

    assert [example.source for example in examples[:2]] == [
        "total = 2 + 3\n",
        "print(total)\n",
    ]
    assert examples[1].want == "5\n"
    assert examples[2].want == "top\n<BLANKLINE>\nbottom\n"
    assert examples[3].options == {doctest.ELLIPSIS: True}
    assert examples[4].options == {doctest.SKIP: True}
    assert examples[0].lineno < examples[-1].lineno


def test_output_checker_handles_blank_lines_whitespace_ellipsis_and_exceptions():
    checker = doctest.OutputChecker()

    assert checker.check_output(
        "alpha\n<BLANKLINE>\nomega\n",
        "alpha\n\nomega\n",
        0,
    )
    assert checker.check_output(
        "record(id=..., state='ready')\n",
        "record(id=918273, state='ready')\n",
        doctest.ELLIPSIS,
    )
    assert checker.check_output(
        "columns are aligned\n",
        "columns   are\n aligned\n",
        doctest.NORMALIZE_WHITESPACE,
    )

    expected = "Traceback (most recent call last):\nValueError: any detail\n"
    actual = "Traceback (most recent call last):\nValueError: platform detail\n"
    assert not checker.check_output(expected, actual, 0)
    # IGNORE_EXCEPTION_DETAIL 由 DocTestRunner 在已识别为异常的分支处理；直接把完整 traceback
    # 交给通用 OutputChecker.check_output 时，这个 bit 不会先提取异常类型。
    assert not checker.check_output(
        expected,
        actual,
        doctest.IGNORE_EXCEPTION_DETAIL,
    )


def test_custom_doctest_option_flags_are_stable_process_wide_markers():
    first = doctest.register_optionflag("POLYGLOT_REDACT_IDS")
    second = doctest.register_optionflag("POLYGLOT_REDACT_IDS")

    assert first == second
    assert first > doctest.REPORT_ONLY_FIRST_FAILURE
    # 注册只分配 bit；OutputChecker 不会自动理解这个 bit 的业务含义。
    # 需要自定义 checker/runner 才能实现“隐藏 ID”之类的比较策略。


def test_doc_test_runner_executes_examples_in_one_shared_namespace():
    source = '''
>>> values = []
>>> values.append(3)
>>> values
[3]
>>> 10 / 0  # doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
ZeroDivisionError: detail does not need to match
>>> print("skip me")  # doctest: +SKIP
different output
'''
    test = doctest.DocTestParser().get_doctest(
        source,
        globs={},
        name="stateful",
        filename="stateful.txt",
        lineno=0,
    )
    failures = []
    runner = doctest.DocTestRunner()
    # 默认 clear_globs=True 会在运行后主动断开对象引用；教学检查共享命名空间时显式保留。
    result = runner.run(test, out=failures.append, clear_globs=False)

    assert result.failed == 0
    assert result.attempted == 4
    assert failures == []
    assert test.globs["values"] == [3]
    assert runner.tries == 4
    assert runner.failures == 0
    assert runner.summarize(verbose=False) == doctest.TestResults(0, 4)


def test_debug_runner_raises_structured_failure_instead_of_printing_report():
    wrong_output = doctest.DocTestParser().get_doctest(
        ">>> 2 + 2\n5\n",
        {},
        "wrong-output",
        "lesson.txt",
        0,
    )
    with pytest.raises(doctest.DocTestFailure) as captured:
        doctest.DebugRunner().run(wrong_output)

    assert captured.value.test is wrong_output
    assert captured.value.example.want == "5\n"
    assert captured.value.got == "4\n"

    unexpected = doctest.DocTestParser().get_doctest(
        ">>> raise LookupError('missing')\n",
        {},
        "unexpected",
        "lesson.txt",
        0,
    )
    with pytest.raises(doctest.UnexpectedException) as raised:
        doctest.DebugRunner().run(unexpected)
    assert raised.value.exc_info[0] is LookupError


def test_testmod_and_finder_discover_module_and_function_docstrings(monkeypatch):
    module = types.ModuleType("polyglot_doctest_lesson")
    module.__doc__ = """Module example.\n\n>>> SCALE\n4\n"""
    exec(
        '''
SCALE = 4

def multiply(value):
    """Multiply by SCALE.

    >>> multiply(3)
    12
    """
    return value * SCALE
''',
        module.__dict__,
    )
    monkeypatch.setitem(sys.modules, module.__name__, module)

    found = doctest.DocTestFinder().find(module)
    assert [test.name for test in found] == [
        "polyglot_doctest_lesson",
        "polyglot_doctest_lesson.multiply",
    ]

    result = doctest.testmod(module, report=False, verbose=False)
    assert result == doctest.TestResults(failed=0, attempted=2)


def test_testmod_copies_extraglobs_instead_of_mutating_the_caller_mapping():
    module = types.ModuleType("polyglot_doctest_extraglobs")
    module.__doc__ = """>>> shared.append('inside')\n>>> shared\n['inside']\n"""
    shared = []
    extra = {"shared": shared}

    result = doctest.testmod(module, extraglobs=extra, report=False)

    assert result == doctest.TestResults(0, 2)
    assert set(extra) == {"shared"}
    # mapping 被浅拷贝，但其中的 mutable value 仍是同一个对象。
    assert shared == ["inside"]
    assert "__name__" not in extra


def test_doc_file_suite_and_testfile_integrate_with_unittest(tmp_path):
    lesson = tmp_path / "arithmetic.txt"
    lesson.write_text(
        """Arithmetic\n==========\n\n>>> 6 * 7\n42\n""",
        encoding="utf-8",
    )

    suite = doctest.DocFileSuite(
        str(lesson),
        module_relative=False,
        encoding="utf-8",
    )
    result, output = run_suite(suite)
    assert result.wasSuccessful()
    assert result.testsRun == 1
    assert "arithmetic.txt" in output

    direct = doctest.testfile(
        str(lesson),
        module_relative=False,
        report=False,
        encoding="utf-8",
    )
    assert direct == doctest.TestResults(0, 1)


def test_script_from_examples_removes_prompts_but_not_expected_output():
    script = doctest.script_from_examples(
        """>>> value = 21\n>>> value * 2\n42\n"""
    )

    assert ">>>" not in script
    assert "value = 21" in script
    assert "value * 2" in script
    # want 会成为注释，因此脚本适合调试，却不再自动比较结果。
    assert "# Expected:" in script
    assert "# 42" in script

    namespace = {}
    exec(compile(script, "<doctest-script>", "exec"), namespace)
    assert namespace["value"] == 21


def test_unittest_setup_teardown_and_cleanups_have_defined_order():
    events = []

    class LifecycleCase(unittest.TestCase):
        def setUp(self):
            events.append("setUp")
            self.addCleanup(events.append, "cleanup-first-added")
            self.addCleanup(events.append, "cleanup-last-added")

        def tearDown(self):
            events.append("tearDown")

        def test_work(self):
            events.append("test")
            self.assertTrue(True)

    result, _ = run_suite(unittest.defaultTestLoader.loadTestsFromTestCase(LifecycleCase))

    assert result.wasSuccessful()
    assert events == [
        "setUp",
        "test",
        "tearDown",
        "cleanup-last-added",
        "cleanup-first-added",
    ]


def test_cleanup_runs_even_when_setup_fails_but_teardown_does_not():
    events = []

    class BrokenSetupCase(unittest.TestCase):
        def setUp(self):
            events.append("setUp")
            self.addCleanup(events.append, "cleanup")
            raise RuntimeError("database unavailable")

        def tearDown(self):
            events.append("tearDown")

        def test_never_reached(self):
            events.append("test")

    result, output = run_suite(
        unittest.defaultTestLoader.loadTestsFromTestCase(BrokenSetupCase)
    )

    assert result.testsRun == 1
    assert len(result.errors) == 1
    assert events == ["setUp", "cleanup"]
    assert "database unavailable" in output


def test_class_fixtures_wrap_all_methods_once_and_loader_sorts_names():
    events = []

    class ClassFixtureCase(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            events.append("setUpClass")

        @classmethod
        def tearDownClass(cls):
            events.append("tearDownClass")

        def test_b(self):
            events.append("b")

        def test_a(self):
            events.append("a")

    loader = unittest.TestLoader()
    assert loader.getTestCaseNames(ClassFixtureCase) == ["test_a", "test_b"]

    result, _ = run_suite(loader.loadTestsFromTestCase(ClassFixtureCase))
    assert result.wasSuccessful()
    assert events == ["setUpClass", "a", "b", "tearDownClass"]


def test_discovery_imports_modules_and_wraps_them_in_module_fixtures(
    tmp_path,
    monkeypatch,
):
    module_name = "test_polyglot_discovery"
    module_path = tmp_path / f"{module_name}.py"
    module_path.write_text(
        '''
import unittest

events = []

def setUpModule():
    events.append("setUpModule")

def tearDownModule():
    events.append("tearDownModule")

class DiscoveredCase(unittest.TestCase):
    def test_loaded(self):
        events.append("test")
''',
        encoding="utf-8",
    )

    # discover 会临时依赖可导入的 top-level directory，并把模块留在
    # sys.modules。monkeypatch 恢复 sys.path，finally 则清理导入缓存。
    monkeypatch.setattr(sys, "path", sys.path.copy())
    sys.modules.pop(module_name, None)
    try:
        suite = unittest.defaultTestLoader.discover(
            start_dir=str(tmp_path),
            pattern="test_polyglot_*.py",
            top_level_dir=str(tmp_path),
        )
        assert suite.countTestCases() == 1
        result, _ = run_suite(suite)
        assert result.wasSuccessful()
        events = sys.modules[module_name].events
    finally:
        sys.modules.pop(module_name, None)

    assert events == [
        "setUpModule",
        "test",
        "tearDownModule",
    ]


def test_loader_suite_function_case_and_load_tests_protocol():
    events = []

    def body():
        events.append("body")

    def setup():
        events.append("setup")

    def teardown():
        events.append("teardown")

    function_case = unittest.FunctionTestCase(
        body,
        setUp=setup,
        tearDown=teardown,
        description="function adapter",
    )
    module = types.ModuleType("synthetic_unittest_module")

    def load_tests(loader, standard_tests, pattern):
        events.append(("load_tests", standard_tests.countTestCases(), pattern))
        return unittest.TestSuite([function_case])

    module.load_tests = load_tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(module, pattern="test_*.py")

    assert suite.countTestCases() == 1
    assert events == [("load_tests", 0, "test_*.py")]

    result, output = run_suite(suite)
    assert result.wasSuccessful()
    assert events[-3:] == ["setup", "body", "teardown"]
    assert "function adapter" in output


def test_assertion_families_and_context_managers_expose_captured_objects():
    case = unittest.TestCase()
    case.assertEqual({"a": 1}, {"a": 1})
    case.assertSequenceEqual([1, 2], [1, 2])
    case.assertCountEqual([1, 1, 2], [2, 1, 1])
    case.assertDictEqual({"a": 1}, {"a": 1})
    case.assertSetEqual({1, 2}, {2, 1})
    case.assertAlmostEqual(1.234, 1.235, places=2)
    case.assertIsInstance(True, int)
    # assertIsSubclass/assertNotIsSubclass 在 3.10 尚不存在，使用 assertTrue 包装 issubclass。
    assert not hasattr(case, "assertIsSubclass")
    case.assertTrue(issubclass(bool, int))

    with case.assertRaisesRegex(ValueError, "bad value") as exception_context:
        raise ValueError("bad value: 7")
    assert exception_context.exception.args == ("bad value: 7",)

    with case.assertWarnsRegex(UserWarning, "legacy") as warning_context:
        warnings.warn("legacy path", UserWarning)
    assert warning_context.warning.args == ("legacy path",)

    logger = logging.getLogger("polyglot.unittest")
    with case.assertLogs(logger, level="INFO") as log_context:
        logger.info("item=%d", 3)
    assert log_context.output == ["INFO:polyglot.unittest:item=3"]

    with case.assertNoLogs(logger, level="WARNING"):
        logger.info("below threshold")


def test_subtests_report_each_failed_parameter_without_stopping_the_loop():
    visited = []

    class ParameterCase(unittest.TestCase):
        def test_even(self):
            for value in [1, 2, 3]:
                with self.subTest(value=value):
                    visited.append(value)
                    self.assertEqual(value % 2, 0)

    result, output = run_suite(
        unittest.defaultTestLoader.loadTestsFromTestCase(ParameterCase)
    )

    assert visited == [1, 2, 3]
    assert result.testsRun == 1
    assert len(result.failures) == 2
    assert "(value=1)" in output
    assert "(value=3)" in output


def test_skip_expected_failure_and_unexpected_success_are_distinct_results():
    class OutcomeCase(unittest.TestCase):
        @unittest.skip("feature unavailable")
        def test_static_skip(self):
            raise AssertionError("not reached")

        def test_dynamic_skip(self):
            self.skipTest("runtime precondition")

        @unittest.expectedFailure
        def test_known_failure(self):
            self.fail("known bug")

        @unittest.expectedFailure
        def test_surprising_pass(self):
            pass

    result, _ = run_suite(unittest.defaultTestLoader.loadTestsFromTestCase(OutcomeCase))

    assert result.testsRun == 4
    assert len(result.skipped) == 2
    assert len(result.expectedFailures) == 1
    assert len(result.unexpectedSuccesses) == 1
    assert result.wasSuccessful() is False


def test_text_runner_failfast_stops_after_first_failure():
    events = []

    class FailureCase(unittest.TestCase):
        def test_a_first(self):
            events.append("first")
            self.fail("first failure")

        def test_b_second(self):
            events.append("second")
            self.fail("second failure")

    result, output = run_suite(
        unittest.defaultTestLoader.loadTestsFromTestCase(FailureCase),
        failfast=True,
    )

    assert result.testsRun == 1
    assert result.shouldStop is True
    assert events == ["first"]
    assert "first failure" in output


def test_text_runner_buffer_hides_successful_stdout_from_runner_stream():
    class ChattyCase(unittest.TestCase):
        def test_chatty(self):
            print("captured chatter")

    result, output = run_suite(
        unittest.defaultTestLoader.loadTestsFromTestCase(ChattyCase),
        buffer=True,
    )

    assert result.wasSuccessful()
    assert "captured chatter" not in output


def test_isolated_asyncio_case_runs_async_fixtures_in_a_private_loop():
    events = []
    loop_ids = []

    class AsyncCase(unittest.IsolatedAsyncioTestCase):
        async def asyncSetUp(self):
            events.append("asyncSetUp")
            loop_ids.append(id(asyncio.get_running_loop()))

        async def test_ready_future(self):
            events.append("test")
            loop_ids.append(id(asyncio.get_running_loop()))
            future = asyncio.get_running_loop().create_future()
            future.set_result("ready")
            self.assertEqual(await future, "ready")

        async def asyncTearDown(self):
            events.append("asyncTearDown")
            loop_ids.append(id(asyncio.get_running_loop()))

    result, _ = run_suite(unittest.defaultTestLoader.loadTestsFromTestCase(AsyncCase))

    assert result.wasSuccessful()
    assert events == ["asyncSetUp", "test", "asyncTearDown"]
    assert len(set(loop_ids)) == 1
    # IsolatedAsyncioTestCase 管理 loop 生命周期；不要把该 loop
    # 缓存给其他测试复用。
