#!/usr/bin/env python3
"""Audit and regenerate Rust Dash-backed stdlib checklist data."""

from dash_stdlib_common import dispatch


if __name__ == "__main__":
    raise SystemExit(dispatch("rust", "audit"))
