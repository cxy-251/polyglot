#!/usr/bin/env python3
"""Render one R checklist or curated task target for ChatGPT handoff."""

from dash_stdlib_common import dispatch


if __name__ == "__main__":
    raise SystemExit(dispatch("r", "render"))
