"""243｜``multiprocessing.connection`` Listener/Client 与 HMAC challenge helpers。

Listener/Client 在 socket 或 Windows pipe 上提供 message-oriented Connection。这里仅用
pytest 临时目录中的 AF_UNIX socket，不访问外部网络。auth challenge 验证共享 key，之后
``recv`` 仍会 unpickle 数据；认证不等于加密，也不能让恶意 authenticated peer 变安全。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.multiprocessing.connection.Listener
# polyglot-covers: python.multiprocessing.connection.Listener-address
# polyglot-covers: python.multiprocessing.connection.Listener.last_accepted
# polyglot-covers: python.multiprocessing.connection.Listener.accept
# polyglot-covers: python.multiprocessing.connection.Listener-context-manager
# polyglot-covers: python.multiprocessing.connection.Client
# polyglot-covers: python.multiprocessing.connection-AF_UNIX-address
# polyglot-covers: python.multiprocessing.connection.deliver_challenge
# polyglot-covers: python.multiprocessing.connection.answer_challenge
# polyglot-covers: python.multiprocessing.connection-challenge-failure
# polyglot-covers: python.multiprocessing.connection-authenticated-pickle-risk

import multiprocessing
from multiprocessing.connection import Client
from multiprocessing.connection import Listener
from multiprocessing.connection import answer_challenge
from multiprocessing.connection import deliver_challenge
import os
import queue
import threading

import pytest


@pytest.mark.skipif(os.name != "posix", reason="案例使用临时 AF_UNIX socket")
def test_listener_and_client_exchange_authenticated_messages_on_unix_socket(tmp_path):
    """listener 在 client thread 启动前已 bind；双方 context manager 都确定 close。"""

    address = str(tmp_path / "multiprocessing-listener.sock")
    authkey = b"local-secret"
    results = queue.Queue()

    with Listener(address, family="AF_UNIX", authkey=authkey) as listener:
        def run_client():
            with Client(listener.address, family="AF_UNIX", authkey=authkey) as connection:
                connection.send({"request": 21})
                results.put(connection.recv())

        thread = threading.Thread(target=run_client)
        thread.start()

        with listener.accept() as connection:
            assert connection.recv() == {"request": 21}
            connection.send({"answer": 42})

        thread.join(timeout=2)
        assert thread.is_alive() is False
        assert results.get_nowait() == {"answer": 42}
        assert listener.address == address
        assert listener.last_accepted is not None


def test_deliver_and_answer_challenge_accept_same_authkey_over_pipe():
    """helpers 对任意 Connection 工作；Pipe 让测试不建立 socket。"""

    server, client = multiprocessing.Pipe()
    completed = threading.Event()

    def answer():
        answer_challenge(client, b"shared-key")
        completed.set()

    thread = threading.Thread(target=answer)
    thread.start()
    deliver_challenge(server, b"shared-key")

    assert completed.wait(timeout=2)
    thread.join()
    server.close()
    client.close()


def test_challenge_mismatch_raises_authentication_error_on_both_sides():
    """server 发 FAILURE，deliver/answer 两端都得到 AuthenticationError 而非静默继续。"""

    server, client = multiprocessing.Pipe()
    client_errors = queue.Queue()

    def answer_with_wrong_key():
        try:
            answer_challenge(client, b"wrong-key")
        except multiprocessing.AuthenticationError as error:
            client_errors.put(type(error))

    thread = threading.Thread(target=answer_with_wrong_key)
    thread.start()

    with pytest.raises(multiprocessing.AuthenticationError):
        deliver_challenge(server, b"correct-key")

    thread.join(timeout=2)
    assert client_errors.get_nowait() is multiprocessing.AuthenticationError
    server.close()
    client.close()
