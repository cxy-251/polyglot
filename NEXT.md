# NEXT

Status: `ready`

## Current task

启动 C++ 阶段的环境与资料锁定。在写第一个 C++ 教学测试前，先让 `ohdev` 中的
GoogleTest/CMake 测试入口可复现，再把 C++ 版本和权威资料写入 `sources.lock`。

## Official references

- GCC 11.4 官方手册
- C++20 标准草案或等价的稳定规范入口
- GoogleTest 官方文档
- 选定版本和固定 URL 必须落入 `sources.lock`，以后测试套不反复重新选来源

## Target files

- `sources.lock`
- `project.json`
- `tools/run-in-container.sh`
- `languages/cpp/` 下最小 CMake/GoogleTest 骨架；环境验证前不要开始大批案例

## Coverage and cases

- 先确认 C++20 与 GCC 11.4 的可用边界，不把较新标准特性误写进基础套。
- GoogleTest 只作为测试框架；教学 API 仍限 C++ 语言和标准库。
- 宿主机不安装编译器或测试框架，不使用联网 `FetchContent` 作为每次测试的隐式前置。
- 骨架必须提供 `./tools/run.sh cpp`，并让新对话能从容器命令得到明确缺依赖诊断。

## Handoff

1. Python 3.10 已完成：178 个文件、编号 `001`–`178` 连续、无重复或缺号，
   每个文件都有 `polyglot-covers`，分类目录范围一致，Unicode 100 列审计为零。
2. 最终严格命令：

   ```bash
   ./tools/run.sh python -q --tb=short --timeout=30 -W error
   ```

   结果为 `5012 passed, 52 skipped`；52 个 skip 均是 Tk/Windows/zone data/dbm/
   ensurepip 等明确环境能力差异。
3. `ohdev` 当前有 `g++ 11.4.0` 和 `cmake 3.22.1`，没有检测到 pkg-config
   GoogleTest 或 `/usr/src/googletest`。
4. 优先为容器建立可复现的 GoogleTest 供应方式；不要把 GoogleTest 源码直接塞进
   本仓库，也不要让普通测试运行临时联网下载。若必须修改容器外部配置，先向用户说明。
5. 环境入口通过后，锁定 C++20 资料并创建第一个 `test_001_...`；C++ 文件编号在
   `languages/cpp/` 内独立连续。
