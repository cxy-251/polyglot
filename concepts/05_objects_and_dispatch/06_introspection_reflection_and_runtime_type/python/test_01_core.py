"""自省、反射与运行时类型。

共同问题：如何查询真实类型与成员；能否动态读写和调用；反射是否触发用户代码；
哪些检查只存在于编译期。
"""

# polyglot-family: objects_and_dispatch
# polyglot-concept: introspection_reflection_and_runtime_type
# polyglot-related: languages/python/builtins/test_027_introspection_and_attribute_functions.py

import inspect


class Service:
    category = "worker"

    def run(self, value=1):
        return value * 2


def test_type_and_isinstance_answer_exact_and_inheritance_questions():
    service = Service()

    assert type(service) is Service
    assert isinstance(service, Service)
    assert isinstance(service, object)


def test_getattr_setattr_and_callable_enable_dynamic_operations():
    service = Service()

    operation = getattr(service, "run")
    setattr(service, "name", "alpha")

    assert callable(operation)
    assert operation(3) == 6
    assert service.name == "alpha"


def test_dir_and_vars_expose_different_member_views():
    service = Service()
    service.name = "alpha"

    assert vars(service) == {"name": "alpha"}
    assert "category" in dir(service)
    assert "run" in dir(service)


def test_signature_and_static_attribute_lookup_avoid_or_expose_dispatch():
    service = Service()

    assert str(inspect.signature(service.run)) == "(value=1)"
    raw = inspect.getattr_static(service, "run")
    assert inspect.isfunction(raw)

    # getattr 会运行 descriptor/property；getattr_static 用于检查定义而不触发动态访问。
