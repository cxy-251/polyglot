# Next task

Status: `in_progress`

## Goal

将锁定的 CRuby 4.0.6 正式接入 Polyglot，成为第九门 active language。以已经完成 Lua
接入的当前 `main` 为基线，交付完整 Ruby 纵向课程、现有 49 个横向 topic 的 Ruby
实现、统一运行入口、精确版本锁、离线 RubyGems/Bundler/Rake 工作流、C Extension、
结构门禁和可复现的最终验证结果。

## Locked scope

- 工具链：从官方 `ruby-4.0.6.tar.gz` 构建 CRuby，安装到
  `/opt/polyglot/ruby-4.0.6`；SHA-256 为
  `837d299e8f7ddf2be31a229a7a7e019d354979825117989acb3b32b1a9be262a`。
- 纵向课程：建立 `languages/ruby/{language,standard_library,tooling_and_runtime}/`，
  固定为连续 `001`–`128` 共 128 个独立执行的 `test_NNN_topic.rb`。
- 测试基础：采用仓库内最小断言库；每文件使用独立 CRuby 进程，并隔离 `HOME`、
  RubyGems、Bundler、load path、启动环境、临时目录和进程级状态。
- 内容范围：Ruby 值与对象模型、作用域、方法与 block、类与 mixin、动态分派、
  refinement、元编程、集合、字符串、模式匹配、异常、标准库、Thread、Fiber、
  Ractor、GC、RubyGems、Bundler、Rake、CRuby 运行时观察和 C Extension。
- 横向课程：为现有 49 个 topic 增加 Ruby 实现，镜像既有局部 stem，共 73 个
  `concepts/NN_family/NN_topic/ruby/test_NN_name.rb`。
- 门禁与验证：接入 `ruby`、`doctor`、`concept`、`family`、`concepts`、
  `list-concepts` 和 `check`；最终逐 family 验证 10 个 family，并执行完整纵向、
  完整横向、离线 package 工作流、C Extension、结构检查和 `git diff --check`。

## Official sources

- Ruby 4.0.6 release：`https://www.ruby-lang.org/en/news/2026/07/14/ruby-4-0-6-released/`
- Ruby 4.0.6 source：`https://cache.ruby-lang.org/pub/ruby/4.0/ruby-4.0.6.tar.gz`
- Ruby 4.0 documentation：`https://docs.ruby-lang.org/en/4.0/`
- RubyGems guides：`https://guides.rubygems.org/`
- Bundler manual：`https://bundler.io/man/`

## Current progress

- 已核对 Lua 完成基线、附件锁定范围、官方资料、Docker 架构和现有构建工具。
- 正在建立 CRuby 4.0.6 bootstrap、精确版本检查、独立进程 runner、断言库和
  C Extension 骨架。

## Handoff

当前唯一下一步：完成并验证 CRuby 4.0.6 工具链与最小测试骨架；不得在实际验证前记录
课程或横向通过数字，也不得在全部闭环前将状态改为 `complete`。
