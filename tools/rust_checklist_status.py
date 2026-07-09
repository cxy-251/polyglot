#!/usr/bin/env python3
"""Summarize Rust checklist/task progress."""

from dash_stdlib_common import dispatch


if __name__ == "__main__":
    raise SystemExit(dispatch("rust", "status"))
