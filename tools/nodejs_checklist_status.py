#!/usr/bin/env python3
"""Summarize Node.js checklist/task progress."""

from dash_stdlib_common import dispatch


if __name__ == "__main__":
    raise SystemExit(dispatch("nodejs", "status"))
