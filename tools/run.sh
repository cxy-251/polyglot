#!/usr/bin/env bash
set -euo pipefail

container="${POLYGLOT_CONTAINER:-ohdev}"
container_root="${POLYGLOT_CONTAINER_ROOT:-/home/polyglot}"

if [[ -f /.dockerenv ]]; then
  exec ./tools/run-in-container.sh "$@"
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "宿主机需要 Docker；也可以在容器中直接运行 ./tools/run-in-container.sh。" >&2
  exit 127
fi

tty_args=(-i)
if [[ -t 0 && -t 1 ]]; then
  tty_args=(-it)
fi

exec docker exec "${tty_args[@]}" -w "$container_root" "$container" \
  bash -lc './tools/run-in-container.sh "$@"' _ "$@"
