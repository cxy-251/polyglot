"""259｜无 shell pipeline、PIPE 容量与 ``communicate`` 排空策略。

多个 Popen 可用文件对象直接连成 pipeline；父进程必须关闭自己持有的中间 pipe 副本，
否则 EOF/SIGPIPE 传播可能被延后。PIPE 有限，先 wait 再读大量 stdout/stderr 可能死锁；
communicate 会并行排空各流，但会把全部内容缓存在内存，只适合有界输出。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.subprocess.shell-free-pipeline
# polyglot-covers: python.subprocess.pipeline-close-parent-copy
# polyglot-covers: python.subprocess.pipeline-returncodes
# polyglot-covers: python.subprocess.PIPE-finite-capacity
# polyglot-covers: python.subprocess.wait-pipe-deadlock-trap
# polyglot-covers: python.subprocess.communicate-multiple-pipes
# polyglot-covers: python.subprocess.communicate-memory-buffering
# polyglot-covers: python.subprocess.DEVNULL-stdin

import subprocess
import sys


def _python_command(source):
    return [sys.executable, "-c", source]


def test_popen_objects_form_a_pipeline_without_invoking_a_shell():
    producer = subprocess.Popen(
        _python_command("print('alpha'); print('beta')"),
        stdout=subprocess.PIPE,
    )
    consumer = subprocess.Popen(
        _python_command(
            "import sys; "
            "sys.stdout.buffer.write(sys.stdin.buffer.read().upper())"
        ),
        stdin=producer.stdout,
        stdout=subprocess.PIPE,
    )
    # consumer 已复制读端；父进程不再需要自己的副本。大型真实 pipeline 中，这也让
    # consumer 提前退出时的 SIGPIPE 能传回 producer。
    producer.stdout.close()

    try:
        output, _ = consumer.communicate(timeout=2)
        producer_status = producer.wait(timeout=2)
    finally:
        for process in (producer, consumer):
            if process.poll() is None:
                process.kill()
                process.wait()

    assert output == b"ALPHA\nBETA\n"
    assert producer_status == consumer.returncode == 0


def test_communicate_drains_stdout_and_stderr_larger_than_typical_pipe_buffers():
    amount = 100_000
    source = (
        f"import os; os.write(1, b'o' * {amount}); "
        f"os.write(2, b'e' * {amount})"
    )
    process = subprocess.Popen(
        _python_command(source),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # 若先 wait，child 可能在第一个满 pipe 上停住，永远写不到第二个；communicate
    # 一边等待一边读两个 pipe。生产代码对无界输出应改为流式读取或写入文件。
    stdout, stderr = process.communicate(timeout=2)

    assert process.returncode == 0
    assert stdout == b"o" * amount
    assert stderr == b"e" * amount


def test_devnull_can_supply_immediate_eof_to_child_stdin():
    completed = subprocess.run(
        _python_command(
            "import sys; print(len(sys.stdin.buffer.read()))"
        ),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )

    assert completed.stdout == "0\n"
