"""303｜SubprocessTransport/Protocol 的 pipe callback 工作流。

高层 create_subprocess_exec 通常更方便；框架可用 loop.subprocess_exec 获得 transport 和
protocol。stdout/stderr 由 pipe_data_received(fd, data) 分流，process_exited 与 pipe 关闭
callback 的先后不应被假定。asyncio 子进程流是 bytes，文本解码由调用者负责。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.loop.subprocess_exec
# polyglot-covers: python.asyncio.loop.subprocess_shell
# polyglot-covers: python.asyncio.subprocess-exec-variadic-argv
# polyglot-covers: python.asyncio.low-level-subprocess-shell-command-string
# polyglot-covers: python.asyncio.SubprocessTransport
# polyglot-covers: python.asyncio.SubprocessProtocol
# polyglot-covers: python.asyncio.subprocess-protocol.pipe_data_received
# polyglot-covers: python.asyncio.subprocess-protocol.pipe_connection_lost
# polyglot-covers: python.asyncio.subprocess-protocol.process_exited
# polyglot-covers: python.asyncio.subprocess-callback-order-not-assumed
# polyglot-covers: python.asyncio.subprocess-transport.get_pid
# polyglot-covers: python.asyncio.subprocess-transport.get_returncode
# polyglot-covers: python.asyncio.subprocess-transport.get_pipe_transport
# polyglot-covers: python.asyncio.subprocess-protocol-bytes-not-text

import asyncio
import shlex
import sys


class CapturingSubprocessProtocol(asyncio.SubprocessProtocol):
    def __init__(self, loop):
        self.loop = loop
        self.transport = None
        self.output = {1: bytearray(), 2: bytearray()}
        self.closed_pipes = set()
        self.exited = False
        self.done = loop.create_future()

    def connection_made(self, transport):
        self.transport = transport

    def pipe_data_received(self, fd, data):
        self.output[fd].extend(data)

    def pipe_connection_lost(self, fd, exc):
        # stdin (fd=0) 可能因 child 提前关闭读端而报告 BrokenPipeError；输出管道正常 EOF
        # 才应给出 None，不能把三个 pipe 的关闭原因一概而论。
        if fd in (1, 2):
            assert exc is None
        self.closed_pipes.add(fd)
        self._finish_when_complete()

    def process_exited(self):
        self.exited = True
        self._finish_when_complete()

    def _finish_when_complete(self):
        # 文档没有承诺 process_exited 与最后一次 pipe callback 的顺序，所以显式等两者。
        if self.exited and {1, 2} <= self.closed_pipes and not self.done.done():
            self.done.set_result(None)


def test_subprocess_protocol_collects_stdout_and_stderr_by_pipe_number():
    async def scenario():
        loop = asyncio.get_running_loop()
        protocol = CapturingSubprocessProtocol(loop)
        code = "import sys;sys.stdout.buffer.write(b'out');sys.stderr.buffer.write(b'err')"
        transport, returned = await loop.subprocess_exec(
            lambda: protocol,
            sys.executable,
            "-c",
            code,
        )
        try:
            assert returned is protocol
            assert protocol.transport is transport
            assert isinstance(transport.get_pid(), int)
            assert transport.get_pipe_transport(1) is not None
            assert transport.get_pipe_transport(2) is not None

            await protocol.done
            assert transport.get_returncode() == 0
            assert bytes(protocol.output[1]) == b"out"
            assert bytes(protocol.output[2]) == b"err"
        finally:
            transport.close()

    asyncio.run(scenario())


def test_low_level_shell_also_returns_a_subprocess_transport_protocol_pair():
    async def scenario():
        loop = asyncio.get_running_loop()
        protocol = CapturingSubprocessProtocol(loop)
        script = "import sys;sys.stdout.write('shell')"
        command = f"{shlex.quote(sys.executable)} -c {shlex.quote(script)}"
        transport, returned = await loop.subprocess_shell(
            lambda: protocol,
            command,
        )
        try:
            assert returned is protocol
            await protocol.done
            assert transport.get_returncode() == 0
            assert bytes(protocol.output[1]) == b"shell"
            assert bytes(protocol.output[2]) == b""
        finally:
            transport.close()

    asyncio.run(scenario())
