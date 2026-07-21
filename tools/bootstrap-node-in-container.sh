#!/usr/bin/env bash
set -euo pipefail

# 这个脚本是显式的容器环境引导步骤，会从 Node.js 官方站点下载锁定归档。
# 普通测试入口 run-in-container.sh 不调用它，因此日常测试不会暗中访问网络。

readonly NODE_VERSION="24.18.0"
readonly INSTALL_ROOT="/opt/polyglot"

if [[ ! -f /.dockerenv ]]; then
  echo "请只在 ohdev Docker 容器内运行此脚本。" >&2
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "安装到 /opt 和 /usr/local/bin 需要容器内的 root 权限。" >&2
  exit 1
fi

for command_name in curl tar xz sha256sum; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "缺少引导命令: $command_name" >&2
    exit 127
  fi
done

case "$(uname -m)" in
  aarch64|arm64)
    archive_arch="arm64"
    expected_sha="58c9520501f6ae2b52d5b210444e24b9d0c029a58c5011b797bc1fe7105886f6"
    ;;
  x86_64|amd64)
    archive_arch="x64"
    expected_sha="55aa7153f9d88f28d765fcdad5ae6945b5c0f98a36881703817e4c450fa76742"
    ;;
  *)
    echo "尚未锁定此容器架构的 Node.js 归档: $(uname -m)" >&2
    exit 1
    ;;
esac

archive_name="node-v${NODE_VERSION}-linux-${archive_arch}.tar.xz"
install_dir="${INSTALL_ROOT}/${archive_name%.tar.xz}"
archive_path="/tmp/${archive_name}"
download_url="https://nodejs.org/dist/v${NODE_VERSION}/${archive_name}"

if [[ ! -x "$install_dir/bin/node" ]] || \
  [[ "$($install_dir/bin/node --version)" != "v${NODE_VERSION}" ]]; then
  curl --fail --location --output "$archive_path" "$download_url"
  printf '%s  %s\n' "$expected_sha" "$archive_path" | sha256sum --check --status

  mkdir -p "$INSTALL_ROOT"
  rm -rf "$install_dir"
  tar --extract --xz --file "$archive_path" --directory "$INSTALL_ROOT"
  rm -f "$archive_path"
fi

for command_name in node npm npx corepack; do
  ln -sfn "$install_dir/bin/$command_name" "/usr/local/bin/$command_name"
done

printf 'node: '
node --version
printf 'npm: '
npm --version
