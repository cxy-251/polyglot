#!/usr/bin/env python3
"""Small standard-library-only reader for Dash docset indexes.

Dash docsets have used at least two index layouts over time:

- Older docsets expose a `searchIndex` table with name/type/path columns.
- Newer docsets use CoreData-style `ZTOKEN` tables.

This module intentionally reads only the searchable token layer.  Language
tools decide how to interpret names for their own baseline/object models.
"""

from __future__ import annotations

import html
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote


DASH_METADATA_RE = re.compile(r"<dash_entry_[^>]+>")
WEB_PATH_RE = re.compile(r"(https?://\S+|[A-Za-z0-9.-]+\.[A-Za-z]{2,}/\S+)")


@dataclass(frozen=True)
class DashToken:
    name: str
    kind: str
    path: str | None
    doc_url: str | None
    declared_in: str | None = None
    declaration: str | None = None
    anchor: str | None = None
    abstract: str | None = None
    source_path: str | None = None


def default_docsets_root() -> Path:
    return Path.home() / "Library" / "Application Support" / "Dash" / "DocSets"


def find_docset(name: str, docsets_root: Path | None = None) -> Path:
    root = docsets_root or default_docsets_root()
    direct = root / name / f"{name}.docset"
    if direct.exists():
        return direct

    normalized_name = _normalize_docset_name(name)
    for candidate in sorted(root.glob("*/*.docset")):
        if _normalize_docset_name(candidate.stem) == normalized_name:
            return candidate
        if _normalize_docset_name(candidate.parent.name) == normalized_name:
            return candidate
    raise FileNotFoundError(f"Dash docset not found for {name!r} under {root}")


def read_docset_tokens(docset_path: Path) -> list[DashToken]:
    index_path = docset_path / "Contents" / "Resources" / "docSet.dsidx"
    if not index_path.exists():
        raise FileNotFoundError(f"missing Dash index: {index_path}")

    with sqlite3.connect(index_path) as db:
        tables = {
            row[0]
            for row in db.execute("select name from sqlite_master where type='table'")
        }
        if "searchIndex" in tables:
            return _read_search_index(db)
        if {"ZTOKEN", "ZTOKENTYPE"}.issubset(tables):
            return _read_coredata_index(db, index_path)
    raise ValueError(f"unsupported Dash index layout: {index_path}")


def clean_dash_path(raw_path: str | None) -> str | None:
    if not raw_path:
        return None
    value = DASH_METADATA_RE.sub("", raw_path)
    value = html.unescape(value).strip()
    if not value:
        return None
    match = WEB_PATH_RE.search(value)
    if match:
        value = match.group(1)
    return _repeated_unquote(value).strip() or None


def doc_url_from_path(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith(("http://", "https://")):
        return path
    if path.startswith("www."):
        return "https://" + path
    if "." in path.split("/", 1)[0]:
        return "https://" + path
    return None


def _normalize_docset_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _repeated_unquote(value: str) -> str:
    previous = value
    for _ in range(3):
        current = unquote(previous)
        if current == previous:
            return current
        previous = current
    return previous


def _read_search_index(db: sqlite3.Connection) -> list[DashToken]:
    columns = {
        row[1]
        for row in db.execute("pragma table_info(searchIndex)")
    }
    required = {"name", "type", "path"}
    if not required.issubset(columns):
        missing = ", ".join(sorted(required - columns))
        raise ValueError(f"searchIndex table is missing columns: {missing}")

    tokens: list[DashToken] = []
    for name, kind, raw_path in db.execute(
        "select name, type, path from searchIndex where name is not null order by name"
    ):
        clean_path = clean_dash_path(raw_path)
        tokens.append(
            DashToken(
                name=str(name).strip(),
                kind=(str(kind).strip() if kind else ""),
                path=clean_path,
                doc_url=doc_url_from_path(clean_path),
                source_path=raw_path,
            )
        )
    return tokens


def _has_table(db: sqlite3.Connection, table: str) -> bool:
    return (
        db.execute(
            "select 1 from sqlite_master where type='table' and name=?",
            (table,),
        ).fetchone()
        is not None
    )


def _read_coredata_index(db: sqlite3.Connection, index_path: Path) -> list[DashToken]:
    has_metadata = _has_table(db, "ZTOKENMETAINFORMATION")
    has_file_path = _has_table(db, "ZFILEPATH")
    has_header = _has_table(db, "ZHEADER")

    joins = ["left join ZTOKENTYPE tt on tt.Z_PK = t.ZTOKENTYPE"]
    selects = [
        "t.ZTOKENNAME",
        "coalesce(tt.ZTYPENAME, '')",
        "''",
        "''",
        "''",
        "''",
        "''",
    ]
    if has_metadata:
        joins.append("left join ZTOKENMETAINFORMATION m on m.ZTOKEN = t.Z_PK")
        selects[4] = "coalesce(m.ZANCHOR, '')"
        selects[5] = "coalesce(m.ZDECLARATION, '')"
        selects[6] = "coalesce(m.ZABSTRACT, '')"
        if has_file_path:
            joins.append("left join ZFILEPATH f on f.Z_PK = m.ZFILE")
            selects[2] = "coalesce(f.ZPATH, '')"
        if has_header:
            joins.append("left join ZHEADER h on h.Z_PK = m.ZDECLAREDIN")
            selects[3] = "coalesce(h.ZHEADERPATH, '')"

    query = f"""
        select {", ".join(selects)}
        from ZTOKEN t
        {" ".join(joins)}
        where t.ZTOKENNAME is not null
        order by t.ZTOKENNAME
    """

    tokens: list[DashToken] = []
    for name, kind, raw_path, declared_in, anchor, declaration, abstract in db.execute(query):
        clean_path = clean_dash_path(raw_path)
        token_anchor = str(anchor).strip() or None
        doc_url = doc_url_from_path(clean_path)
        if doc_url and token_anchor and "#" not in doc_url:
            doc_url += "#" + token_anchor
        tokens.append(
            DashToken(
                name=str(name).strip(),
                kind=(str(kind).strip() if kind else ""),
                path=clean_path,
                doc_url=doc_url,
                declared_in=str(declared_in).strip() or None,
                declaration=str(declaration).strip() or None,
                anchor=token_anchor,
                abstract=str(abstract).strip() or None,
                source_path=os.fspath(index_path),
            )
        )
    return tokens
