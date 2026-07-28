#!/usr/bin/env bash
set -euo pipefail

# 这个脚本是显式的容器环境引导步骤，会从各语言的官方站点下载锁定归档。
# 普通测试入口不会调用它，因此日常测试不会暗中访问网络或修改系统包。

readonly INSTALL_ROOT="/opt/polyglot"
readonly JULIA_VERSION="1.12.6"
readonly R_VERSION="4.6.1"
readonly LUA_VERSION="5.5.0"
readonly RUBY_VERSION="4.0.6"
readonly GO_VERSION="1.26.5"
readonly RUST_VERSION="1.97.1"
readonly RUST_RELEASE_DATE="2026-07-16"

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

mkdir -p "$INSTALL_ROOT"

download_verified() {
  local download_url="$1"
  local archive_path="$2"
  local expected_sha="$3"

  if [[ -f "$archive_path" ]] && \
    printf '%s  %s\n' "$expected_sha" "$archive_path" | \
      sha256sum --check --status; then
    return
  fi

  rm -f "$archive_path"
  curl --fail --location --output "$archive_path" "$download_url"
  if ! printf '%s  %s\n' "$expected_sha" "$archive_path" | \
    sha256sum --check --status; then
    rm -f "$archive_path"
    echo "归档校验失败: $download_url" >&2
    exit 1
  fi
}

install_julia() {
  local archive_arch
  local archive_directory
  local expected_sha
  case "$(uname -m)" in
    aarch64|arm64)
      archive_arch="aarch64"
      archive_directory="aarch64"
      expected_sha="029b93b857bd0ffd627f9a8580d3bbaa63daf008d7b7aed02fbceb8fd57c4899"
      ;;
    x86_64|amd64)
      archive_arch="x86_64"
      archive_directory="x64"
      expected_sha="bbabf3bef19421a9dbd24a767d807606ab85e444323b5a1c73ffe293fa3d079a"
      ;;
    *)
      echo "尚未锁定此容器架构的 Julia 归档: $(uname -m)" >&2
      exit 1
      ;;
  esac

  local archive_name="julia-${JULIA_VERSION}-linux-${archive_arch}.tar.gz"
  local archive_path="/tmp/${archive_name}"
  local install_dir="${INSTALL_ROOT}/julia-${JULIA_VERSION}"
  local download_url
  download_url="https://julialang-s3.julialang.org/bin/linux"
  download_url+="/${archive_directory}/1.12/${archive_name}"

  if [[ ! -x "$install_dir/bin/julia" ]] || \
    [[ "$($install_dir/bin/julia --startup-file=no --history-file=no \
      -e 'print(VERSION)')" != "$JULIA_VERSION" ]]; then
    download_verified "$download_url" "$archive_path" "$expected_sha"
    rm -rf "$install_dir"
    tar --extract --gzip --file "$archive_path" --directory "$INSTALL_ROOT"
  fi

  ln -sfn "$install_dir/bin/julia" /usr/local/bin/julia
  printf 'julia: '
  julia --startup-file=no --history-file=no --version
}

install_r_build_dependencies() {
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install --yes --no-install-recommends \
    build-essential \
    gfortran \
    pkg-config \
    texinfo \
    tzdata \
    libblas-dev \
    liblapack-dev \
    libreadline-dev \
    libpcre2-dev \
    libbz2-dev \
    liblzma-dev \
    zlib1g-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    libicu-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff5-dev \
    libcairo2-dev \
    libdeflate-dev \
    libtirpc-dev
  rm -rf /var/lib/apt/lists/*
}

install_r() {
  local expected_sha="e4149581e151f3f1bc5edd6475e24ca1e2f452c08b6a22c29b570ce8abfe5783"
  local archive_name="R-${R_VERSION}.tar.xz"
  local archive_path="/tmp/${archive_name}"
  local source_dir="/tmp/R-${R_VERSION}"
  local install_dir="${INSTALL_ROOT}/R-${R_VERSION}"
  local download_url
  download_url="https://cran.r-project.org/src/base/R-4/${archive_name}"

  if [[ ! -x "$install_dir/bin/R" ]] || \
    [[ "$("$install_dir/bin/R" --version | sed -n '1p')" != \
      "R version ${R_VERSION}"* ]]; then
    install_r_build_dependencies
    download_verified "$download_url" "$archive_path" "$expected_sha"
    rm -rf "$source_dir" "$install_dir"
    tar --extract --xz --file "$archive_path" --directory /tmp
    (
      cd "$source_dir"
      ./configure \
        --prefix="$install_dir" \
        --with-x=no \
        --enable-R-shlib \
        --with-blas \
        --with-lapack
      make --jobs "${POLYGLOT_BUILD_JOBS:-4}"
      make install
    )
    rm -rf "$source_dir"
  fi

  ln -sfn "$install_dir/bin/R" /usr/local/bin/R
  ln -sfn "$install_dir/bin/Rscript" /usr/local/bin/Rscript
  printf 'R: '
  R --version | sed -n '1p'
}

install_lua() {
  local expected_sha="57ccc32bbbd005cab75bcc52444052535af691789dba2b9016d5c50640d68b3d"
  local archive_name="lua-${LUA_VERSION}.tar.gz"
  local archive_path="/tmp/${archive_name}"
  local source_dir="/tmp/lua-${LUA_VERSION}"
  local install_dir="${INSTALL_ROOT}/lua-${LUA_VERSION}"
  local download_url="https://www.lua.org/ftp/${archive_name}"
  local installed_release=""

  if [[ -x "$install_dir/bin/lua" ]]; then
    installed_release="$("$install_dir/bin/lua" -v 2>&1 | awk '{print $2}')"
  fi

  if [[ "$installed_release" != "$LUA_VERSION" ]] || \
    [[ ! -x "$install_dir/bin/luac" ]] || \
    [[ ! -f "$install_dir/include/lua.h" ]] || \
    [[ ! -f "$install_dir/lib/liblua.a" ]]; then
    download_verified "$download_url" "$archive_path" "$expected_sha"
    rm -rf "$source_dir" "$install_dir"
    tar --extract --gzip --file "$archive_path" --directory /tmp
    (
      cd "$source_dir"
      make all
      make test
      make install INSTALL_TOP="$install_dir"
    )
    rm -rf "$source_dir"
  fi

  ln -sfn "$install_dir/bin/lua" /usr/local/bin/lua
  ln -sfn "$install_dir/bin/luac" /usr/local/bin/luac
  printf 'lua: '
  lua -v
  printf 'luac: '
  luac -v
}

install_ruby_build_dependencies() {
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install --yes --no-install-recommends \
    autoconf \
    bison \
    build-essential \
    libffi-dev \
    libgdbm-dev \
    libncurses-dev \
    libreadline-dev \
    libssl-dev \
    libyaml-dev \
    pkg-config \
    zlib1g-dev
  rm -rf /var/lib/apt/lists/*
}

install_ruby() {
  local expected_sha="837d299e8f7ddf2be31a229a7a7e019d354979825117989acb3b32b1a9be262a"
  local archive_name="ruby-${RUBY_VERSION}.tar.gz"
  local archive_path="/tmp/${archive_name}"
  local source_dir="/tmp/ruby-${RUBY_VERSION}"
  local install_dir="${INSTALL_ROOT}/ruby-${RUBY_VERSION}"
  local download_url="https://cache.ruby-lang.org/pub/ruby/4.0/${archive_name}"
  local installed_version=""

  if [[ -x "$install_dir/bin/ruby" ]]; then
    installed_version="$("$install_dir/bin/ruby" -e 'print RUBY_VERSION')"
  fi

  if [[ "$installed_version" != "$RUBY_VERSION" ]] || \
    [[ ! -x "$install_dir/bin/gem" ]] || \
    [[ ! -x "$install_dir/bin/bundle" ]] || \
    [[ ! -x "$install_dir/bin/rake" ]]; then
    install_ruby_build_dependencies
    download_verified "$download_url" "$archive_path" "$expected_sha"
    rm -rf "$source_dir" "$install_dir"
    tar --extract --gzip --file "$archive_path" --directory /tmp
    (
      cd "$source_dir"
      ./configure \
        --prefix="$install_dir" \
        --disable-install-doc \
        --disable-yjit \
        --disable-zjit
      make --jobs "${POLYGLOT_BUILD_JOBS:-4}"
      make install
    )
    rm -rf "$source_dir"
  fi

  for command_name in ruby gem bundle bundler rake rdoc ri; do
    if [[ -x "$install_dir/bin/$command_name" ]]; then
      ln -sfn "$install_dir/bin/$command_name" "/usr/local/bin/$command_name"
    fi
  done
  printf 'ruby: '
  ruby --version
  printf 'gem: '
  gem --version
  printf 'bundle: '
  bundle --version
  printf 'rake: '
  rake --version
}

install_go() {
  local archive_arch
  local expected_sha
  case "$(uname -m)" in
    aarch64|arm64)
      archive_arch="arm64"
      expected_sha="fe4789e92b1f33358680864bbe8704289e7bb5fc207d80623c308935bd696d49"
      ;;
    x86_64|amd64)
      archive_arch="amd64"
      expected_sha="5c2c3b16caefa1d968a94c1daca04a7ca301a496d9b086e17ad77bb81393f053"
      ;;
    *)
      echo "尚未锁定此容器架构的 Go 归档: $(uname -m)" >&2
      exit 1
      ;;
  esac

  local archive_name="go${GO_VERSION}.linux-${archive_arch}.tar.gz"
  local archive_path="/tmp/${archive_name}"
  local extraction_dir="/tmp/polyglot-go-${GO_VERSION}"
  local install_dir="${INSTALL_ROOT}/go-${GO_VERSION}"
  local download_url="https://go.dev/dl/${archive_name}"

  if [[ ! -x "$install_dir/bin/go" ]] || \
    [[ "$($install_dir/bin/go version)" != *"go${GO_VERSION}"* ]]; then
    download_verified "$download_url" "$archive_path" "$expected_sha"
    rm -rf "$extraction_dir" "$install_dir"
    mkdir -p "$extraction_dir"
    tar --extract --gzip --file "$archive_path" --directory "$extraction_dir"
    mv "$extraction_dir/go" "$install_dir"
    rmdir "$extraction_dir"
  fi

  ln -sfn "$install_dir/bin/go" /usr/local/bin/go
  ln -sfn "$install_dir/bin/gofmt" /usr/local/bin/gofmt
  printf 'go: '
  go version
}

install_rust() {
  local rust_target
  local expected_sha
  case "$(uname -m)" in
    aarch64|arm64)
      rust_target="aarch64-unknown-linux-gnu"
      expected_sha="9a7a2c336b4787f1b72f6bab7c35d5b7af2fd03cbd39b4fc721466a70d402a7d"
      ;;
    x86_64|amd64)
      rust_target="x86_64-unknown-linux-gnu"
      expected_sha="88f28fa9af20594179f85d6df67078dfd6fa93e2f6da5e1e9b0ac4997988ca4f"
      ;;
    *)
      echo "尚未锁定此容器架构的 Rust 归档: $(uname -m)" >&2
      exit 1
      ;;
  esac

  local archive_name="rust-${RUST_VERSION}-${rust_target}.tar.xz"
  local archive_path="/tmp/${archive_name}"
  local source_dir="/tmp/${archive_name%.tar.xz}"
  local install_dir="${INSTALL_ROOT}/rust-${RUST_VERSION}"
  local download_url="https://static.rust-lang.org/dist/${RUST_RELEASE_DATE}/${archive_name}"

  if [[ ! -x "$install_dir/bin/rustc" ]] || \
    [[ "$($install_dir/bin/rustc --version)" != "rustc ${RUST_VERSION}"* ]]; then
    download_verified "$download_url" "$archive_path" "$expected_sha"
    rm -rf "$source_dir" "$install_dir"
    tar --extract --xz --file "$archive_path" --directory /tmp
    "$source_dir/install.sh" \
      --prefix="$install_dir" \
      --disable-ldconfig
    rm -rf "$source_dir"
  fi

  for command_name in cargo rustc rustdoc; do
    ln -sfn "$install_dir/bin/$command_name" "/usr/local/bin/$command_name"
  done
  for optional_command in cargo-clippy clippy-driver cargo-fmt rustfmt; do
    if [[ -x "$install_dir/bin/$optional_command" ]]; then
      ln -sfn \
        "$install_dir/bin/$optional_command" \
        "/usr/local/bin/$optional_command"
    fi
  done
  printf 'rustc: '
  rustc --version
  printf 'cargo: '
  cargo --version
}

if [[ $# -eq 0 ]]; then
  set -- all
fi

for target in "$@"; do
  case "$target" in
    all)
      install_julia
      install_r
      install_lua
      install_ruby
      install_go
      install_rust
      ;;
    julia)
      install_julia
      ;;
    r)
      install_r
      ;;
    lua)
      install_lua
      ;;
    ruby)
      install_ruby
      ;;
    go)
      install_go
      ;;
    rust)
      install_rust
      ;;
    *)
      echo "用法: $0 [all|julia|r|lua|ruby|go|rust]..." >&2
      exit 2
      ;;
  esac
done
