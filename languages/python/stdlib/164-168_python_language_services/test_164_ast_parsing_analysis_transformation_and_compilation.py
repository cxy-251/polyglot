"""164｜ast：从源码解析到树分析、改写、回译与编译。

AST 是 Python 语法结构的稳定编程入口，但不是原始文本的无损模型：注释和
排版会丢失，位置列是 UTF-8 字节偏移，节点上下文与位置又是编译器
的真实输入。本套覆盖解析模式、3.10 模式匹配节点、访问器、变换器、
位置工具、literal_eval、unparse 和回译 code object 的完整工作流。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.ast python.ast.ast-base python.ast.abstract-grammar
# polyglot-covers: python.ast.parse python.ast.parse-modes python.ast.feature-version
# polyglot-covers: python.ast.pycf-only-ast python.ast.compile-tree
# polyglot-covers: python.ast.pycf-type-comments python.ast.type-comments
# polyglot-covers: python.ast.type-ignore python.ast.misplaced-type-comment
# polyglot-covers: python.ast.pycf-allow-top-level-await
# polyglot-covers: python.ast.parse-not-full-validation
# polyglot-covers: python.ast.node-fields python.ast.optional-and-list-fields
# polyglot-covers: python.ast.source-locations python.ast.utf8-byte-offsets
# polyglot-covers: python.ast.load-store-del-context
# polyglot-covers: python.ast.constant python.ast.deprecated-literal-nodes
# polyglot-covers: python.ast.index-extslice-deprecated
# polyglot-covers: python.ast.operator-singletons
# polyglot-covers: python.ast.expression-nodes python.ast.call-starred-keyword-unpack
# polyglot-covers: python.ast.dict-unpack python.ast.fstring-nodes
# polyglot-covers: python.ast.subscript-slice-tuple python.ast.comprehension
# polyglot-covers: python.ast.statement-nodes python.ast.function-arguments
# polyglot-covers: python.ast.import-from-level python.ast.try-with-class
# polyglot-covers: python.ast.async-nodes python.ast.await-async-for-with
# polyglot-covers: python.ast.pattern-matching-3.10 python.ast.match-pattern-nodes
# polyglot-covers: python.ast.dump python.ast.dump-indent-attributes
# polyglot-covers: python.ast.iter-fields python.ast.iter-child-nodes python.ast.walk
# polyglot-covers: python.ast.get-docstring python.ast.get-source-segment
# polyglot-covers: python.ast.copy-location python.ast.fix-missing-locations
# polyglot-covers: python.ast.increment-lineno
# polyglot-covers: python.ast.node-visitor python.ast.generic-visit
# polyglot-covers: python.ast.node-transformer python.ast.statement-list-replacement
# polyglot-covers: python.ast.transformer-delete-node python.ast.transformer-context
# polyglot-covers: python.ast.literal-eval python.ast.literal-eval-not-untrusted-safe
# polyglot-covers: python.ast.unparse-3.9 python.ast.unparse-not-source-roundtrip

import ast
import inspect

import pytest


def test_parse_modes_return_the_four_root_node_families():
    module = ast.parse("value = 42\n", mode="exec")
    expression = ast.parse("40 + 2", mode="eval")
    interactive = ast.parse("value = 42\n", mode="single")
    function_type = ast.parse("(int, str) -> bool", mode="func_type")

    assert isinstance(module, ast.Module)
    assert isinstance(module.body[0], ast.Assign)
    assert module.type_ignores == []
    assert isinstance(expression, ast.Expression)
    assert isinstance(expression.body, ast.BinOp)
    assert isinstance(interactive, ast.Interactive)
    assert isinstance(function_type, ast.FunctionType)
    assert [argument.id for argument in function_type.argtypes] == ["int", "str"]
    assert function_type.returns.id == "bool"


def test_compile_only_ast_and_parse_are_equivalent_frontends():
    source = "answer = 6 * 7\n"
    parsed = ast.parse(source, filename="lesson.py")
    compiled_as_tree = compile(
        source,
        "lesson.py",
        "exec",
        flags=ast.PyCF_ONLY_AST,
    )

    assert isinstance(compiled_as_tree, ast.Module)
    assert ast.dump(parsed) == ast.dump(compiled_as_tree)

    namespace = {}
    code = compile(parsed, "lesson.py", "exec")
    exec(code, namespace)
    assert namespace["answer"] == 42


def test_feature_version_uses_an_older_grammar_on_a_best_effort_basis():
    source = "match value:\n    case 42:\n        result = True\n"

    with pytest.raises(SyntaxError):
        ast.parse(source, feature_version=(3, 9))

    current = ast.parse(source, feature_version=(3, 10))
    assert isinstance(current.body[0], ast.Match)
    # feature_version 是语法兼容工具，不会把当前解释器完整变成旧版本。


def test_type_comments_and_type_ignores_require_the_explicit_parser_flag():
    source = (
        "values = []  # type: list[int]\n"
        "for item in values:  # type: int\n"
        "    print(item)\n"
        "values.missing()  # type: ignore[attr-defined]\n"
    )
    ordinary = ast.parse(source)
    typed = ast.parse(source, type_comments=True)

    assert ordinary.body[0].type_comment is None
    assert ordinary.body[1].type_comment is None
    assert ordinary.type_ignores == []

    assignment, loop = typed.body[:2]
    assert assignment.type_comment == "list[int]"
    assert loop.type_comment == "int"
    assert len(typed.type_ignores) == 1
    assert typed.type_ignores[0].lineno == 4
    assert typed.type_ignores[0].tag == "[attr-defined]"

    compiled_as_tree = compile(
        source,
        "typed.py",
        "exec",
        flags=ast.PyCF_ONLY_AST | ast.PyCF_TYPE_COMMENTS,
    )
    assert compiled_as_tree.body[0].type_comment == "list[int]"


def test_misplaced_type_comment_is_only_an_error_when_type_comments_are_enabled():
    source = "print('not an assignment')  # type: int\n"
    assert isinstance(ast.parse(source).body[0], ast.Expr)

    with pytest.raises(SyntaxError):
        ast.parse(source, type_comments=True)
    # 不带标志时这只是普通注释；带标志后它被按类型注释解读，
    # 而表达式语句没有 type_comment 字段，因此是错位注释。


def test_top_level_await_needs_a_compiler_flag_and_marks_the_code_coroutine():
    source = "await work()\n"
    with pytest.raises(SyntaxError, match="outside function"):
        compile(source, "console.py", "exec")

    tree = compile(
        source,
        "console.py",
        "exec",
        flags=ast.PyCF_ONLY_AST | ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
    )
    assert isinstance(tree.body[0].value, ast.Await)

    code = compile(
        source,
        "console.py",
        "exec",
        flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
    )
    assert code.co_flags & inspect.CO_COROUTINE
    # 这类 code object 执行后产生 coroutine；调用者还必须在事件循环中 await，
    # 编译标志本身不会运行异步代码。


def test_parse_builds_a_tree_before_some_contextual_compiler_checks():
    tree = ast.parse("return 42\n")
    assert isinstance(tree.body[0], ast.Return)

    with pytest.raises(SyntaxError, match="outside function"):
        compile(tree, "invalid_scope.py", "exec")
    # ast.parse 主要负责语法建树；return 是否位于函数体内属于
    # 后续编译检查。


def test_node_fields_distinguish_children_optional_values_and_lists():
    tree = ast.parse("result = left + right\n")
    assignment = tree.body[0]
    operation = assignment.value

    assert ast.Assign._fields == ("targets", "value", "type_comment")
    assert assignment.targets[0].id == "result"
    assert assignment.type_comment is None
    assert ast.BinOp._fields == ("left", "op", "right")
    assert isinstance(operation.op, ast.Add)
    assert isinstance(operation.left, ast.Name)
    assert isinstance(operation.right, ast.Name)
    # ASDL 中的 ``*`` 字段变成 list，``?`` 字段变成 None 或单个值。


def test_name_context_records_load_store_and_delete_roles():
    tree = ast.parse("target = source\ndel target\n")
    names = [node for node in ast.walk(tree) if isinstance(node, ast.Name)]
    by_role = {(node.id, type(node.ctx)) for node in names}

    assert by_role == {
        ("target", ast.Store),
        ("source", ast.Load),
        ("target", ast.Del),
    }


def test_location_columns_are_utf8_byte_offsets_and_end_is_exclusive():
    source = "变量 = 1\nresult = 变量 + 2\n"
    tree = ast.parse(source)
    loaded_name = next(
        node
        for node in ast.walk(tree.body[1])
        if isinstance(node, ast.Name) and node.id == "变量"
    )

    assert loaded_name.lineno == 2
    assert loaded_name.end_lineno == 2
    assert loaded_name.col_offset == 9
    assert loaded_name.end_col_offset == 15
    assert ast.get_source_segment(source, loaded_name) == "变量"
    # 两个中文字符在 UTF-8 中各占 3 字节，所以不能直接用 Python 字符
    # 下标去切 source；get_source_segment 会正确处理这个差异。


def test_deprecated_literal_and_slice_constructors_return_modern_nodes():
    number = ast.Num(n=42)
    text = ast.Str(s="lesson")
    truth = ast.NameConstant(value=True)
    value = ast.Constant(value=1)
    old_index = ast.Index(value=value)
    old_extended_slice = ast.ExtSlice(
        dims=[ast.Slice(lower=None, upper=ast.Constant(2)), ast.Constant(3)]
    )

    assert type(number) is ast.Constant
    assert number.value == 42
    assert type(text) is ast.Constant
    assert text.value == "lesson"
    assert type(truth) is ast.Constant
    assert truth.value is True
    assert old_index is value
    assert isinstance(old_extended_slice, ast.Tuple)
    assert len(old_extended_slice.elts) == 2
    # 3.10 仍接受旧名字，但构造结果已是 Constant/Tuple；新工具不应按
    # Num、Str、Index 等旧类名分支。


def test_operator_nodes_from_one_parse_are_shared_singletons():
    tree = ast.parse("first + second + third", mode="eval")
    additions = [node.op for node in ast.walk(tree) if isinstance(node, ast.BinOp)]

    assert len(additions) == 2
    assert additions[0] is additions[1]
    # operator、unaryop、cmpop、boolop 和 expr_context 节点会被共享；给 Add
    # 实例加属性可能污染整棵树，分析器应把它们当不可变标记。


def test_call_dict_fstring_and_subscript_shapes_preserve_syntactic_roles():
    call = ast.parse(
        "invoke(*items, named=value, **options)",
        mode="eval",
    ).body
    mapping = ast.parse('{**base, "answer": 42}', mode="eval").body
    formatted = ast.parse('f"{value!r:>10}"', mode="eval").body
    subscript = ast.parse("matrix[1:3, column]", mode="eval").body

    assert isinstance(call.args[0], ast.Starred)
    assert call.args[0].value.id == "items"
    assert [(item.arg, item.value.id) for item in call.keywords] == [
        ("named", "value"),
        (None, "options"),
    ]

    assert mapping.keys[0] is None
    assert mapping.values[0].id == "base"
    assert mapping.keys[1].value == "answer"

    field = formatted.values[0]
    assert isinstance(field, ast.FormattedValue)
    assert field.conversion == ord("r")
    assert isinstance(field.format_spec, ast.JoinedStr)

    assert isinstance(subscript.slice, ast.Tuple)
    assert isinstance(subscript.slice.elts[0], ast.Slice)
    assert subscript.slice.elts[1].id == "column"
    # ** 实参用 arg=None，字典 ** 展开用 key=None；这两个 None 都是协议
    # 标记，不是缺失数据。


def test_comprehension_keeps_generator_order_targets_filters_and_async_flag():
    expression = ast.parse(
        "[item * 2 for group in groups for item in group if item > 0]",
        mode="eval",
    ).body

    assert isinstance(expression, ast.ListComp)
    assert [generator.target.id for generator in expression.generators] == [
        "group",
        "item",
    ]
    assert expression.generators[0].ifs == []
    assert len(expression.generators[1].ifs) == 1
    assert [generator.is_async for generator in expression.generators] == [0, 0]

    async_tree = ast.parse(
        "async def collect(stream):\n"
        "    return [item async for item in stream]\n"
    )
    comprehension = async_tree.body[0].body[0].value
    assert comprehension.generators[0].is_async == 1


def test_function_class_import_try_and_with_nodes_keep_header_details():
    source = (
        "from ..package import thing as alias\n"
        "class Demo(Base, metaclass=Meta):\n"
        "    @decorator\n"
        "    def method(self, /, value: int = 1, *, flag=True) -> int:\n"
        "        with resource() as handle:\n"
        "            try:\n"
        "                return value\n"
        "            except ValueError as error:\n"
        "                raise error\n"
    )
    tree = ast.parse(source)
    imported = tree.body[0]
    class_node = tree.body[1]
    function = class_node.body[0]
    with_node = function.body[0]
    try_node = with_node.body[0]

    assert imported.module == "package"
    assert imported.level == 2
    assert [(item.name, item.asname) for item in imported.names] == [
        ("thing", "alias")
    ]
    assert class_node.bases[0].id == "Base"
    assert class_node.keywords[0].arg == "metaclass"
    assert function.decorator_list[0].id == "decorator"
    assert [item.arg for item in function.args.posonlyargs] == ["self"]
    assert [item.arg for item in function.args.args] == ["value"]
    assert [item.arg for item in function.args.kwonlyargs] == ["flag"]
    assert function.args.kw_defaults[0].value is True
    assert with_node.items[0].optional_vars.id == "handle"
    assert try_node.handlers[0].name == "error"
    assert isinstance(try_node.handlers[0].type, ast.Name)


def test_async_function_contains_distinct_await_async_with_and_async_for_nodes():
    source = (
        "async def consume(stream, manager):\n"
        "    async with manager() as resource:\n"
        "        async for item in stream:\n"
        "            await resource.send(item)\n"
    )
    function = ast.parse(source).body[0]

    assert isinstance(function, ast.AsyncFunctionDef)
    assert isinstance(function.body[0], ast.AsyncWith)
    assert isinstance(function.body[0].body[0], ast.AsyncFor)
    expression = function.body[0].body[0].body[0]
    assert isinstance(expression.value, ast.Await)


def test_python_310_pattern_matching_has_dedicated_pattern_node_families():
    source = (
        "match subject:\n"
        "    case {'kind': 'point', 'x': x, **rest} if x > 0:\n"
        "        result = x\n"
        "    case [first, *tail]:\n"
        "        result = first\n"
        "    case Point(a, b=y):\n"
        "        result = y\n"
        "    case 0 | 1:\n"
        "        result = 0\n"
    )
    match_node = ast.parse(source).body[0]
    mapping, sequence, class_case, either = match_node.cases

    assert isinstance(match_node, ast.Match)
    assert isinstance(mapping.pattern, ast.MatchMapping)
    assert [key.value for key in mapping.pattern.keys] == ["kind", "x"]
    assert mapping.pattern.rest == "rest"
    assert isinstance(mapping.guard, ast.Compare)

    assert isinstance(sequence.pattern, ast.MatchSequence)
    assert isinstance(sequence.pattern.patterns[1], ast.MatchStar)
    assert sequence.pattern.patterns[1].name == "tail"

    assert isinstance(class_case.pattern, ast.MatchClass)
    assert class_case.pattern.cls.id == "Point"
    assert class_case.pattern.kwd_attrs == ["b"]
    assert isinstance(either.pattern, ast.MatchOr)
    assert len(either.pattern.patterns) == 2


def test_dump_can_trade_compactness_for_fields_locations_and_indentation():
    tree = ast.parse("answer = 42\n")
    compact = ast.dump(tree, annotate_fields=False)
    detailed = ast.dump(
        tree,
        include_attributes=True,
        indent=2,
    )

    assert compact.startswith("Module([Assign(")
    assert "targets=" not in compact
    assert "\n" in detailed
    assert "lineno=1" in detailed
    assert "end_col_offset=11" in detailed

    with pytest.raises(TypeError, match="expected AST"):
        ast.dump("not a node")


def test_iter_fields_children_and_walk_offer_three_traversal_depths():
    tree = ast.parse("result = left + right\n")
    assignment = tree.body[0]
    fields = dict(ast.iter_fields(assignment))
    direct_children = list(ast.iter_child_nodes(assignment))
    all_nodes = list(ast.walk(assignment))

    assert set(fields) == {"targets", "value", "type_comment"}
    assert direct_children == [assignment.targets[0], assignment.value]
    assert all_nodes[0] is assignment
    assert {node.id for node in all_nodes if isinstance(node, ast.Name)} == {
        "result",
        "left",
        "right",
    }
    # walk 的递归顺序未承诺；除了根节点之外，不要把当前遍历次序
    # 写进工具逻辑。


def test_get_docstring_can_clean_indentation_or_return_raw_text():
    source = (
        '"""Module summary.\n\n    Indented detail.\n"""\n'
        "def function():\n"
        '    """Function summary."""\n'
        "    pass\n"
    )
    tree = ast.parse(source)

    assert ast.get_docstring(tree) == "Module summary.\n\nIndented detail."
    assert ast.get_docstring(tree, clean=False) == (
        "Module summary.\n\n    Indented detail.\n"
    )
    assert ast.get_docstring(tree.body[1]) == "Function summary."

    with pytest.raises(TypeError, match="can't have docstrings"):
        ast.get_docstring(tree.body[1].body[-1])


def test_get_source_segment_handles_multiline_padding_and_missing_locations():
    source = (
        "if ready:\n"
        "    value = (\n"
        "        left + right\n"
        "    )\n"
    )
    assignment = ast.parse(source).body[0].body[0]
    ordinary = ast.get_source_segment(source, assignment)
    padded = ast.get_source_segment(source, assignment, padded=True)

    assert ordinary.startswith("value = (")
    assert ordinary.endswith("    )")
    assert padded.startswith("    value = (")
    assert ast.get_source_segment(source, ast.Constant(1)) is None


def test_location_helpers_make_generated_trees_compilable_and_relocatable():
    expression = ast.Expression(
        body=ast.BinOp(
            left=ast.Constant(40),
            op=ast.Add(),
            right=ast.Constant(2),
        )
    )
    with pytest.raises(TypeError, match="lineno"):
        compile(expression, "generated.py", "eval")

    fixed = ast.fix_missing_locations(expression)
    assert fixed is expression
    assert expression.body.lineno == 1
    assert eval(compile(expression, "generated.py", "eval")) == 42

    original = ast.parse("value = 1\n").body[0].value
    replacement = ast.copy_location(ast.Constant(2), original)
    assert replacement.lineno == original.lineno
    assert replacement.col_offset == original.col_offset
    assert replacement.end_col_offset == original.end_col_offset

    assert ast.increment_lineno(replacement, 10) is replacement
    assert replacement.lineno == 11
    assert replacement.end_lineno == 11


def test_manual_assignment_target_must_use_store_context():
    bad_tree = ast.Module(
        body=[
            ast.Assign(
                targets=[ast.Name(id="value", ctx=ast.Load())],
                value=ast.Constant(42),
            )
        ],
        type_ignores=[],
    )
    ast.fix_missing_locations(bad_tree)

    with pytest.raises(ValueError, match="Store context"):
        compile(bad_tree, "bad_context.py", "exec")

    bad_tree.body[0].targets[0].ctx = ast.Store()
    namespace = {}
    exec(compile(bad_tree, "good_context.py", "exec"), namespace)
    assert namespace["value"] == 42


def test_node_visitor_dispatches_by_class_and_requires_explicit_recursion_override():
    tree = ast.parse(
        "def calculate(value):\n"
        "    offset = 2\n"
        "    return value + offset\n"
    )

    class NameCollector(ast.NodeVisitor):
        def __init__(self):
            self.names = []

        def visit_Name(self, node):
            self.names.append((node.id, type(node.ctx).__name__))

    collector = NameCollector()
    collector.visit(tree)
    assert collector.names == [
        ("offset", "Store"),
        ("value", "Load"),
        ("offset", "Load"),
    ]

    class FunctionBoundaryVisitor(ast.NodeVisitor):
        def __init__(self):
            self.functions = []
            self.names = []

        def visit_FunctionDef(self, node):
            self.functions.append(node.name)
            # 故意不调 generic_visit：自定义 visit_X 不会自动继续遍历。

        def visit_Name(self, node):
            self.names.append(node.id)

    boundary = FunctionBoundaryVisitor()
    boundary.visit(tree)
    assert boundary.functions == ["calculate"]
    assert boundary.names == []


def test_node_transformer_can_rewrite_loaded_names_and_preserve_context():
    tree = ast.parse("result = answer + 1\n")

    class RewriteAnswer(ast.NodeTransformer):
        def visit_Name(self, node):
            if node.id != "answer" or not isinstance(node.ctx, ast.Load):
                return node
            replacement = ast.Subscript(
                value=ast.Name(id="environment", ctx=ast.Load()),
                slice=ast.Constant("answer"),
                ctx=node.ctx,
            )
            return ast.copy_location(replacement, node)

    transformed = RewriteAnswer().visit(tree)
    ast.fix_missing_locations(transformed)
    namespace = {"environment": {"answer": 41}}
    exec(compile(transformed, "rewrite.py", "exec"), namespace)

    assert namespace["result"] == 42
    remaining_names = {
        node.id for node in ast.walk(transformed) if isinstance(node, ast.Name)
    }
    assert "answer" not in remaining_names
    assert {"result", "environment"} <= remaining_names


def test_node_transformer_can_delete_or_splice_statement_list_entries():
    tree = ast.parse(
        "debug('remove me')\n"
        "value = 40\n"
        "result = value + 2\n"
    )

    class InstrumentAssignments(ast.NodeTransformer):
        def visit_Expr(self, node):
            if (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "debug"
            ):
                return None
            return self.generic_visit(node)

        def visit_Assign(self, node):
            node = self.generic_visit(node)
            target_name = node.targets[0].id
            audit = ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="record", ctx=ast.Load()),
                    args=[ast.Constant(target_name)],
                    keywords=[],
                )
            )
            ast.copy_location(audit, node)
            return [audit, node]

    transformed = InstrumentAssignments().visit(tree)
    ast.fix_missing_locations(transformed)
    events = []
    namespace = {"record": events.append}
    exec(compile(transformed, "instrumented.py", "exec"), namespace)

    assert events == ["value", "result"]
    assert namespace["result"] == 42
    assert all(
        not (
            isinstance(node, ast.Name)
            and node.id == "debug"
        )
        for node in ast.walk(transformed)
    )
    # None 只能用于可删除位置，list 只能替换语句列表中的节点；表达式
    # 字段仍必须返回单个合法 AST 节点。


def test_literal_eval_accepts_literals_but_never_runs_calls_or_comprehensions():
    value = ast.literal_eval(
        "  {'numbers': (1, -2, 3 + 4j), 'flags': [True, None], 'empty': set()}"
    )
    assert value == {
        "numbers": (1, -2, 3 + 4j),
        "flags": [True, None],
        "empty": set(),
    }
    assert ast.literal_eval(ast.parse("{'answer': 42}", mode="eval")) == {
        "answer": 42
    }

    with pytest.raises(ValueError, match="malformed node"):
        ast.literal_eval("1 + 2")
    with pytest.raises(ValueError, match="malformed node"):
        ast.literal_eval("[item for item in values]")
    with pytest.raises(ValueError, match="malformed node"):
        ast.literal_eval("__import__('os')")
    # literal_eval 不执行任意代码，但巨大或极深的字面量仍可耗尽内存或
    # C 栈；它不是对无限制不受信输入的资源安全沙箱。


def test_unparse_round_trips_structure_but_not_comments_or_formatting():
    source = "# leading comment\nresult=(1+2)*3\n"
    tree = ast.parse(source)
    rebuilt = ast.unparse(tree)

    assert "comment" not in rebuilt
    assert rebuilt == "result = (1 + 2) * 3"
    assert ast.dump(ast.parse(rebuilt)) == ast.dump(tree)
    assert rebuilt != source.strip()
    # unparse 承诺的是再次 parse 后语法树等价，不是字符串级的格式保留。
