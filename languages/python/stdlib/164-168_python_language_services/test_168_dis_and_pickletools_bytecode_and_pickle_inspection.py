"""168｜dis 与 pickletools：检查字节码和 pickle 虚拟机指令。

dis 把 code object 还原为 CPython 字节码指令、跳转目标、源码行和栈效果；
pickletools 对 pickle 数据做同类的静态反汇编，并能删除无用 memo 写入。
两者都适合解释和诊断实现细节，
但输出不是跨 Python 版本的稳定文件格式，
而且“能检查 pickle”绝不意味着“不可信 pickle 可以安全加载”。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.stdlib.dis python.dis.get-instructions
# polyglot-covers: python.dis.instruction-fields python.dis.opmap
# polyglot-covers: python.dis.constant-folding python.dis.binary-add-3.10
# polyglot-covers: python.dis.control-flow python.dis.jump-targets
# polyglot-covers: python.dis.findlabels python.dis.findlinestarts
# polyglot-covers: python.dis.first-line python.dis.stack-effect
# polyglot-covers: python.dis.bytecode python.dis.bytecode-dis-info
# polyglot-covers: python.dis.dis python.dis.dis-depth python.dis.raw-bytecode
# polyglot-covers: python.dis.code-info python.dis.show-code
# polyglot-covers: python.dis.compiler-flags python.dis.pretty-flags
# polyglot-covers: python.dis.bytecode-from-traceback python.dis.current-offset
# polyglot-covers: python.stdlib.pickletools python.pickletools.opcodes
# polyglot-covers: python.pickletools.opcode-info python.pickletools.genops
# polyglot-covers: python.pickletools.positions python.pickletools.file-input
# polyglot-covers: python.pickletools.dis python.pickletools.annotate
# polyglot-covers: python.pickletools.protocols python.pickletools.frame
# polyglot-covers: python.pickletools.newobj-ex python.pickletools.protocol5-buffer
# polyglot-covers: python.pickletools.optimize python.pickletools.memo-aliasing
# polyglot-covers: python.pickletools.malformed-stream
# polyglot-covers: python.pickletools.stops-at-stop
# polyglot-covers: python.pickletools.inspect-not-safe-unpickle

import dis
import io
import pickle
import pickletools

import pytest


def calculate(left, right):
    return left + right


def branch(value):
    if value > 0:
        return "positive"
    return "other"


def outer_function(value):
    def inner_function(increment):
        return value + increment

    return inner_function


def variadic_generator(first, *items, **options):
    yield first
    yield from items
    yield options


class KeywordConstructed:
    def __new__(cls, value, *, label):
        instance = super().__new__(cls)
        instance.value = value
        instance.label = label
        return instance

    def __getnewargs_ex__(self):
        return (self.value,), {"label": self.label}


def instruction_names(subject):
    return [instruction.opname for instruction in dis.get_instructions(subject)]


def test_get_instructions_exposes_opcode_arguments_offsets_and_lines():
    instructions = list(dis.get_instructions(calculate))
    names = [instruction.opname for instruction in instructions]

    assert names == [
        "LOAD_FAST",
        "LOAD_FAST",
        "BINARY_ADD",
        "RETURN_VALUE",
    ]
    first = instructions[0]
    assert isinstance(first, dis.Instruction)
    assert first.opcode == dis.opmap["LOAD_FAST"]
    assert first.arg == 0
    assert first.argval == "left"
    assert first.argrepr == "left"
    assert first.offset == 0
    assert first.starts_line == calculate.__code__.co_firstlineno + 1
    assert first.is_jump_target is False
    assert [item.offset for item in instructions] == sorted(
        item.offset for item in instructions
    )


def test_disassembly_reveals_constant_folding_before_runtime():
    def folded():
        return 2 + 3

    def dynamic(left, right):
        return left + right

    folded_names = instruction_names(folded)
    dynamic_names = instruction_names(dynamic)

    assert "BINARY_ADD" not in folded_names
    assert "LOAD_CONST" in folded_names
    assert "BINARY_ADD" in dynamic_names
    # 源码相同的“+”不保证有同一指令形状：
    # 常量表达式会在编译阶段折叠。


def test_control_flow_marks_jump_instructions_and_their_targets():
    instructions = list(dis.get_instructions(branch))
    jumps = [
        item
        for item in instructions
        if item.opcode in dis.hasjabs or item.opcode in dis.hasjrel
    ]
    labels = dis.findlabels(branch.__code__.co_code)

    assert any(item.opname == "POP_JUMP_IF_FALSE" for item in jumps)
    assert labels == sorted({item.argval for item in jumps})
    assert {
        item.offset for item in instructions if item.is_jump_target
    } == set(labels)
    # arg 是编码后的操作数；argval 已被 dis 解析为真实目标偏移。


def test_source_line_tables_match_instruction_line_markers():
    starts = list(dis.findlinestarts(branch.__code__))
    marked = [
        (item.offset, item.starts_line)
        for item in dis.get_instructions(branch)
        if item.starts_line is not None
    ]

    assert starts == marked
    assert starts[0][1] == branch.__code__.co_firstlineno + 1
    # co_firstlineno 指向 def；3.10 的行号表从第一条可执行的函数体指令开始，
    # 因而 findlinestarts 不必包含定义行本身。

    original_first = next(
        item.starts_line for item in dis.get_instructions(branch) if item.starts_line
    )
    shifted = list(
        dis.get_instructions(
            branch,
            first_line=1000,
        )
    )
    shifted_first = next(item.starts_line for item in shifted if item.starts_line)
    assert shifted_first == original_first + (
        1000 - branch.__code__.co_firstlineno
    )
    # first_line 只改变展示映射，不会修改原 code object。
    assert branch.__code__.co_firstlineno != 1000


def test_stack_effect_can_compare_fallthrough_and_jump_paths():
    assert dis.stack_effect(dis.opmap["LOAD_CONST"], 0) == 1
    assert dis.stack_effect(dis.opmap["POP_TOP"]) == -1

    for_iter = dis.opmap["FOR_ITER"]
    assert dis.stack_effect(for_iter, 0, jump=False) == 1
    assert dis.stack_effect(for_iter, 0, jump=True) == -1
    # FOR_ITER 继续时保留迭代器并压入元素，耗尽跳转时则弹出迭代器。

    with pytest.raises(ValueError):
        dis.stack_effect(dis.opmap["LOAD_CONST"])


def test_bytecode_wraps_iteration_text_disassembly_and_code_info():
    bytecode = dis.Bytecode(calculate)

    assert [item.opname for item in bytecode] == instruction_names(calculate)
    assert "BINARY_ADD" in bytecode.dis()
    info = bytecode.info()
    assert "Name:              calculate" in info
    assert "Argument count:    2" in info
    assert calculate.__code__.co_filename in info


def test_dis_depth_controls_recursive_nested_code_output():
    shallow = io.StringIO()
    recursive = io.StringIO()

    dis.dis(outer_function, file=shallow, depth=0)
    dis.dis(outer_function, file=recursive)

    heading = "Disassembly of <code object inner_function"
    assert heading not in shallow.getvalue()
    assert heading in recursive.getvalue()
    # 外层 LOAD_CONST 的参数仍可能出现 inner_function 名字；
    # depth 控制的是递归段落。


def test_dis_accepts_source_code_objects_and_raw_bytecode():
    source_output = io.StringIO()
    code_output = io.StringIO()
    raw_output = io.StringIO()
    source = "result = left + right\n"
    code = compile(source, "lesson.py", "exec")

    dis.dis(source, file=source_output)
    dis.dis(code, file=code_output)
    dis.dis(code.co_code, file=raw_output)

    assert "BINARY_ADD" in source_output.getvalue()
    assert "BINARY_ADD" in code_output.getvalue()
    assert "BINARY_ADD" in raw_output.getvalue()
    assert "left" in code_output.getvalue()
    assert "left" not in raw_output.getvalue()
    # 裸 co_code 缺少 co_names/co_consts 等表，
    # 只能显示操作数，无法完整解析 argval。


def test_code_info_show_code_and_pretty_flags_explain_code_metadata():
    info = dis.code_info(variadic_generator)
    shown = io.StringIO()
    assert dis.show_code(variadic_generator, file=shown) is None

    assert shown.getvalue() == info + "\n"
    assert "Name:              variadic_generator" in info
    assert "Variable names:" in info

    flags = variadic_generator.__code__.co_flags
    pretty = dis.pretty_flags(flags)
    assert "OPTIMIZED" in pretty
    assert "NEWLOCALS" in pretty
    assert "VARARGS" in pretty
    assert "VARKEYWORDS" in pretty
    assert "GENERATOR" in pretty
    assert dis.COMPILER_FLAG_NAMES[0x20] == "GENERATOR"


def test_bytecode_from_traceback_marks_the_failing_instruction():
    def divide(value):
        return 42 // value

    try:
        divide(0)
    except ZeroDivisionError as error:
        traceback = error.__traceback__
    else:  # pragma: no cover - 这个分支只用于让案例失败信息更明确。
        raise AssertionError("divide(0) should fail")

    while traceback.tb_next is not None:
        traceback = traceback.tb_next

    bytecode = dis.Bytecode.from_traceback(traceback)
    assert bytecode.current_offset == traceback.tb_lasti
    current = next(
        item for item in bytecode if item.offset == bytecode.current_offset
    )
    assert current.opname == "BINARY_FLOOR_DIVIDE"
    assert "-->" in bytecode.dis()


def test_pickle_opcode_registry_exposes_machine_readable_metadata():
    by_name = {opcode.name: opcode for opcode in pickletools.opcodes}
    stop = by_name["STOP"]
    proto = by_name["PROTO"]

    assert isinstance(stop, pickletools.OpcodeInfo)
    assert stop.code == "."
    assert stop.arg is None
    assert stop.proto == 0
    assert "stop" in stop.doc.lower()

    assert proto.code == "\x80"
    assert proto.arg.name == "uint1"
    assert proto.proto == 2
    assert proto.stack_before == []
    # OpcodeInfo 描述的是 pickle 虚拟机协议，不必靠硬编码单字节猜语义。


@pytest.mark.parametrize("protocol", [0, 1, 2, 3, 4, 5])
def test_genops_decodes_each_supported_protocol_without_unpickling(protocol):
    value = {"numbers": [1, 2, 3], "text": "中文"}
    data = pickle.dumps(value, protocol=protocol)
    operations = list(pickletools.genops(data))

    assert operations[-1][0].name == "STOP"
    assert operations[-1][2] == len(data) - 1
    assert [position for _, _, position in operations] == sorted(
        position for _, _, position in operations
    )
    if protocol >= 2:
        assert operations[0][0].name == "PROTO"
        assert operations[0][1] == protocol
    else:
        assert operations[0][0].name != "PROTO"
    assert pickle.loads(data) == value


def test_genops_accepts_a_binary_file_and_reports_opcode_arguments():
    data = pickle.dumps([10, 20], protocol=2)
    stream = io.BytesIO(data)
    operations = list(pickletools.genops(stream))
    integers = [
        argument
        for opcode, argument, _ in operations
        if opcode.name in {"BININT1", "BININT2", "BININT"}
    ]

    assert integers == [10, 20]
    assert operations[0][2] == 0
    assert stream.tell() == len(data)


def test_pickletools_dis_writes_stack_aware_annotated_output():
    data = pickle.dumps({"answer": 42}, protocol=4)
    output = io.StringIO()

    assert pickletools.dis(data, out=output, indentlevel=2, annotate=1) is None

    rendered = output.getvalue()
    assert "PROTO" in rendered
    assert "FRAME" in rendered
    assert "STOP" in rendered
    assert "highest protocol among opcodes = 4" in rendered
    assert "Protocol version indicator" in rendered


def test_protocol_four_frames_delimit_large_pickle_payloads():
    value = list(range(50_000))
    data = pickle.dumps(value, protocol=4)
    operations = list(pickletools.genops(data))
    frames = [argument for opcode, argument, _ in operations if opcode.name == "FRAME"]

    assert len(frames) >= 2
    assert all(size > 0 for size in frames)
    assert pickle.loads(data) == value
    # FRAME 是传输分段，不是对象层级；大 pickle 可包含多个 frame。


def test_newobj_ex_records_keyword_arguments_for_object_construction():
    value = KeywordConstructed(42, label="answer")
    data = pickle.dumps(value, protocol=4)
    names = [opcode.name for opcode, _, _ in pickletools.genops(data)]

    assert "NEWOBJ_EX" in names
    restored = pickle.loads(data)
    assert isinstance(restored, KeywordConstructed)
    assert restored.value == 42
    assert restored.label == "answer"


def test_protocol_five_marks_out_of_band_buffers_in_the_opcode_stream():
    buffers = []
    data = pickle.dumps(
        pickle.PickleBuffer(b"binary payload"),
        protocol=5,
        buffer_callback=buffers.append,
    )
    names = [opcode.name for opcode, _, _ in pickletools.genops(data)]

    assert names[0] == "PROTO"
    assert "NEXT_BUFFER" in names
    assert "READONLY_BUFFER" in names
    assert len(buffers) == 1
    restored = pickle.loads(data, buffers=buffers)
    assert bytes(restored) == b"binary payload"


def test_optimize_removes_unused_memo_writes_and_preserves_aliasing():
    shared = []
    value = [shared, shared, {"numbers": [1, 2, 3]}]
    original = pickle.dumps(value, protocol=0)
    optimized = pickletools.optimize(original)

    assert len(optimized) < len(original)
    restored = pickle.loads(optimized)
    assert restored == value
    assert restored[0] is restored[1]

    original_names = [
        opcode.name for opcode, _, _ in pickletools.genops(original)
    ]
    optimized_names = [
        opcode.name for opcode, _, _ in pickletools.genops(optimized)
    ]
    assert optimized_names.count("PUT") < original_names.count("PUT")
    assert "GET" in optimized_names
    # 被 GET 引用的 memo 会保留；只有永远不会读取的 PUT/BINPUT 可删除。


@pytest.mark.parametrize(
    "data",
    [
        b"!",
        pickle.dumps([1, 2, 3], protocol=4)[:-1],
    ],
)
def test_genops_rejects_unknown_or_truncated_streams(data):
    with pytest.raises(ValueError):
        list(pickletools.genops(data))


def test_dis_detects_pickle_virtual_machine_stack_underflow():
    output = io.StringIO()
    with pytest.raises(ValueError, match="stack"):
        pickletools.dis(b"a.", out=output)
    # genops 负责解码，dis 还模拟 MARK、memo 与栈，因此能发现更多结构错误。


def test_genops_stops_at_the_first_stop_opcode_in_concatenated_pickles():
    first = pickle.dumps("first", protocol=4)
    second = pickle.dumps("second", protocol=4)
    operations = list(pickletools.genops(first + second))

    assert operations[-1][0].name == "STOP"
    assert operations[-1][2] == len(first) - 1
    assert operations[-1][2] < len(first + second) - 1
    # 若协议允许连续对象，调用者必须从 STOP 后的位置
    # 显式开始解析下一段。


def test_inspection_of_global_reduce_opcodes_does_not_make_loading_safe():
    dangerous_shape = b"cos\nsystem\n(S'echo must-not-run'\ntR."
    operations = list(pickletools.genops(dangerous_shape))
    summary = [(opcode.name, argument) for opcode, argument, _ in operations]

    assert ("GLOBAL", "os system") in summary
    assert any(name == "REDUCE" for name, _ in summary)
    assert summary[-1][0] == "STOP"
    # genops 只读指令所以不会调用 os.system；pickle.loads 会执行归约，
    # 绝不能在此尝试。
