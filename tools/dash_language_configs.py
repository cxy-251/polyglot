#!/usr/bin/env python3
"""Dash-backed checklist configuration for planned languages."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from dash_docset import DashToken


@dataclass(frozen=True)
class DashLanguageConfig:
    lang_id: str
    display_name: str
    docset_name: str
    entry_kind: str
    object_filter: Callable[[DashToken], bool]
    object_name: Callable[[DashToken], str | None]
    object_kind: Callable[[DashToken], str]
    entry_id: Callable[[DashToken, str], str]
    entry_title: Callable[[str], str]
    doc_url: Callable[[DashToken], str | None]
    task_example_query: str
    future_test_framework: str
    future_test_extension: str


NODE_KIND_MAP = {
    "Module": "module",
    "cl": "class",
    "clm": "function",
    "instp": "property",
    "Event": "event",
    "Error": "error",
    "Variable": "variable",
}


def strip_call_signature(name: str) -> str:
    value = name.strip()
    if value.startswith("new "):
        value = value[4:]
    paren = value.find("(")
    if paren != -1:
        value = value[:paren]
    return value.strip()


def node_api_page(path: str | None) -> str:
    if not path:
        return "misc"
    match = re.search(r"nodejs/api/([^/#]+)\.html", path)
    return match.group(1) if match else "misc"


def node_object_filter(token: DashToken) -> bool:
    return token.kind in NODE_KIND_MAP and (token.path or "").startswith("nodejs/api/")


def node_object_name(token: DashToken) -> str | None:
    if token.kind == "Module":
        return f"node:{node_api_page(token.path)}"
    name = strip_call_signature(token.name)
    return name or None


def node_doc_url(token: DashToken) -> str | None:
    path = token.path
    if not path:
        return None
    if path.startswith("nodejs/api/"):
        return "https://nodejs.org/api/" + path.removeprefix("nodejs/api/")
    return token.doc_url


def julia_object_filter(token: DashToken) -> bool:
    path = token.path or ""
    return (
        path.startswith("docs.julialang.org/en/v1/base/")
        or path.startswith("docs.julialang.org/en/v1/stdlib/")
        or token.name.startswith(("Base.", "Core.", "Dates.", "LinearAlgebra.", "Random.", "Statistics."))
    )


def julia_entry_id(token: DashToken, _name: str) -> str:
    path = token.path or ""
    match = re.search(r"/stdlib/([^/]+)/", path)
    if match:
        return match.group(1)
    match = re.search(r"/base/([^/]+)/", path)
    if match:
        return "base." + match.group(1)
    if token.name.startswith("Base."):
        return "Base"
    if token.name.startswith("Core."):
        return "Core"
    return "julia"


def r_package(path: str | None) -> str:
    match = re.search(r"/library/([^/]+)/", path or "")
    return match.group(1) if match else "unknown"


def r_object_filter(token: DashToken) -> bool:
    return token.kind in {"Function", "Package"} and "/library/" in (token.path or "")


def r_object_name(token: DashToken) -> str | None:
    package = r_package(token.path)
    if token.kind == "Package":
        return package
    name = token.name.strip()
    return f"{package}::{name}" if name else None


def go_package(path: str | None, name: str | None = None) -> str:
    match = re.search(r"pkg\.go\.dev/(.+?)@go", path or "")
    if match:
        return match.group(1)
    if name and "." in name:
        return name.rsplit(".", 1)[0]
    return "unknown"


def go_object_filter(token: DashToken) -> bool:
    path = token.path or ""
    return (
        path.startswith("pkg.go.dev/")
        and "/internal" not in path
        and "/vendor" not in path
        and token.kind in {"Package", "Function", "Constant", "Variable", "tdef"}
    )


def go_object_kind(token: DashToken) -> str:
    return {
        "Package": "package",
        "Function": "function",
        "Constant": "constant",
        "Variable": "variable",
        "tdef": "type",
    }.get(token.kind, token.kind.lower())


def go_doc_url(token: DashToken) -> str | None:
    path = token.path
    if not path:
        return None
    if path.startswith("pkg.go.dev/"):
        cleaned = path.replace(".html", "")
        return "https://" + cleaned
    return token.doc_url


def rust_object_filter(token: DashToken) -> bool:
    path = token.path or ""
    return (
        ("/std/" in path or path.endswith("/std/index.html"))
        and token.name.startswith("std")
        and token.kind in {"Module", "Function", "Method", "Type", "_Struct", "Trait", "Enum", "Constant", "Variant", "Macro", "Union", "Field"}
    )


def rust_object_kind(token: DashToken) -> str:
    return {
        "_Struct": "struct",
        "Module": "module",
        "Function": "function",
        "Method": "method",
        "Type": "type",
        "Trait": "trait",
        "Enum": "enum",
        "Constant": "constant",
        "Variant": "variant",
        "Macro": "macro",
        "Union": "union",
        "Field": "field",
    }.get(token.kind, token.kind.lower())


def rust_entry_id(_token: DashToken, name: str) -> str:
    parts = name.split("::")
    if len(parts) >= 2:
        return "::".join(parts[:2])
    return "std"


CONFIGS: dict[str, DashLanguageConfig] = {
    "nodejs": DashLanguageConfig(
        lang_id="nodejs",
        display_name="Node.js",
        docset_name="NodeJS",
        entry_kind="api-page",
        object_filter=node_object_filter,
        object_name=node_object_name,
        object_kind=lambda token: NODE_KIND_MAP.get(token.kind, token.kind.lower()),
        entry_id=lambda token, _name: node_api_page(token.path),
        entry_title=lambda entry_id: entry_id,
        doc_url=node_doc_url,
        task_example_query="path",
        future_test_framework="node:test",
        future_test_extension=".test.mjs",
    ),
    "julia": DashLanguageConfig(
        lang_id="julia",
        display_name="Julia",
        docset_name="Julia",
        entry_kind="module-or-category",
        object_filter=julia_object_filter,
        object_name=lambda token: token.name.strip() or None,
        object_kind=lambda token: token.kind.lower(),
        entry_id=julia_entry_id,
        entry_title=lambda entry_id: entry_id,
        doc_url=lambda token: token.doc_url,
        task_example_query="Base.Dict",
        future_test_framework="Test stdlib",
        future_test_extension="_test.jl",
    ),
    "r": DashLanguageConfig(
        lang_id="r",
        display_name="R",
        docset_name="R",
        entry_kind="package",
        object_filter=r_object_filter,
        object_name=r_object_name,
        object_kind=lambda token: "package" if token.kind == "Package" else "function",
        entry_id=lambda token, _name: r_package(token.path),
        entry_title=lambda entry_id: entry_id,
        doc_url=lambda token: token.doc_url,
        task_example_query="base",
        future_test_framework="base stopifnot",
        future_test_extension="_test.R",
    ),
    "go": DashLanguageConfig(
        lang_id="go",
        display_name="Go",
        docset_name="Go",
        entry_kind="package",
        object_filter=go_object_filter,
        object_name=lambda token: token.name.strip() or None,
        object_kind=go_object_kind,
        entry_id=lambda token, name: go_package(token.path, name),
        entry_title=lambda entry_id: entry_id,
        doc_url=go_doc_url,
        task_example_query="strings",
        future_test_framework="testing",
        future_test_extension="_test.go",
    ),
    "rust": DashLanguageConfig(
        lang_id="rust",
        display_name="Rust",
        docset_name="Rust",
        entry_kind="module",
        object_filter=rust_object_filter,
        object_name=lambda token: token.name.strip() or None,
        object_kind=rust_object_kind,
        entry_id=rust_entry_id,
        entry_title=lambda entry_id: entry_id,
        doc_url=lambda token: token.doc_url,
        task_example_query="std::vec",
        future_test_framework="cargo test",
        future_test_extension=".rs",
    ),
}
