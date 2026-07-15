"""116｜webbrowser 注册、默认选择、延迟构造与 0/1/2 打开模式。

``register()`` 和默认 browser 顺序是进程级状态，测试必须隔离。传 instance 时不会调用
constructor；仅传 constructor 时由 ``get()`` 按需创建。模块级 open/open_new/open_new_tab 最终
把 new=0/1/2 交给 controller；返回 True 只表示启动请求被接受，不保证页面真的已呈现。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.webbrowser.Error
# polyglot-covers: python.webbrowser.register
# polyglot-covers: python.webbrowser.register.instance-skips-constructor
# polyglot-covers: python.webbrowser.register.preferred-3.7
# polyglot-covers: python.webbrowser.get
# polyglot-covers: python.webbrowser.open
# polyglot-covers: python.webbrowser.open.new-0-1-2
# polyglot-covers: python.webbrowser.open.autoraise
# polyglot-covers: python.webbrowser.open_new
# polyglot-covers: python.webbrowser.open_new_tab
# polyglot-covers: python.webbrowser-process-global-registry

import webbrowser

import pytest


class RecordingBrowser:
    def __init__(self, result=True):
        self.result = result
        self.calls = []

    def open(self, url, new=0, autoraise=True):
        self.calls.append((url, new, autoraise))
        return self.result


def isolate_registry(monkeypatch):
    # 避免读取平台浏览器和 BROWSER 环境；注册与选择全部在测试私有容器内完成。
    monkeypatch.setattr(webbrowser, "_browsers", {})
    monkeypatch.setattr(webbrowser, "_tryorder", [])


def test_registered_instance_becomes_preferred_without_calling_constructor(monkeypatch):
    isolate_registry(monkeypatch)
    regular = RecordingBrowser()
    preferred = RecordingBrowser()

    def forbidden_constructor():
        raise AssertionError("提供 instance 后不应调用 constructor")

    webbrowser.register("regular", None, instance=regular)
    webbrowser.register(
        "preferred",
        forbidden_constructor,
        instance=preferred,
        preferred=True,
    )

    assert webbrowser.get("regular") is regular
    assert webbrowser.get() is preferred


def test_constructor_registration_is_lazy_and_unknown_name_raises(monkeypatch):
    isolate_registry(monkeypatch)
    constructed = []

    def make_browser():
        browser = RecordingBrowser()
        constructed.append(browser)
        return browser

    webbrowser.register("lazy", make_browser)
    assert constructed == []
    assert webbrowser.get("lazy") is constructed[0]

    with pytest.raises(webbrowser.Error):
        webbrowser.get("missing")


def test_module_open_helpers_forward_modes_and_return_controller_result(monkeypatch):
    isolate_registry(monkeypatch)
    browser = RecordingBrowser(result=True)
    webbrowser.register("recording", None, instance=browser, preferred=True)

    assert webbrowser.open("https://example.test/current", autoraise=False)
    assert webbrowser.open_new("https://example.test/window")
    assert webbrowser.open_new_tab("https://example.test/tab")

    assert browser.calls == [
        ("https://example.test/current", 0, False),
        ("https://example.test/window", 1, True),
        ("https://example.test/tab", 2, True),
    ]
