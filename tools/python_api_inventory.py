#!/usr/bin/env python3
"""Print a compact inventory of Python built-in APIs for checklist work."""

from __future__ import annotations

import builtins
import inspect
import sys
from collections.abc import Callable


OBJECTS = {
    "list": list,
    "tuple": tuple,
    "dict": dict,
    "set": set,
    "frozenset": frozenset,
    "str": str,
    "bytes": bytes,
    "bytearray": bytearray,
    "memoryview": memoryview,
    "range": range,
    "int": int,
    "float": float,
    "complex": complex,
    "object": object,
}


def callable_name(value: object) -> str:
    if inspect.isdatadescriptor(value):
        return "data-descriptor"
    if isinstance(value, (staticmethod, classmethod, property)):
        return type(value).__name__
    if isinstance(value, Callable):
        return "callable"
    return type(value).__name__


def describe_object(name: str, value: object) -> None:
    print(f"# {name}")
    public = []
    dunder = []
    for attr in dir(value):
        item = getattr(value, attr, None)
        row = f"{attr} [{callable_name(item)}]"
        if attr.startswith("__") and attr.endswith("__"):
            dunder.append(row)
        elif not attr.startswith("_"):
            public.append(row)

    if public:
        print("## public")
        for row in public:
            print(f"- {row}")

    if dunder:
        print("## dunder")
        for row in dunder:
            print(f"- {row}")
    print()


def describe_builtins() -> None:
    print("# builtins")
    for name in sorted(dir(builtins)):
        if name.startswith("_"):
            continue
        value = getattr(builtins, name)
        print(f"- {name} [{callable_name(value)}]")


def main(argv: list[str]) -> int:
    names = argv[1:] or ["builtins", *OBJECTS]
    for name in names:
        if name == "builtins":
            describe_builtins()
            continue
        if name not in OBJECTS:
            choices = ", ".join(["builtins", *OBJECTS])
            print(f"unknown object {name!r}; choose one of: {choices}", file=sys.stderr)
            return 2
        describe_object(name, OBJECTS[name])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
