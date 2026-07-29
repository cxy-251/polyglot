# 共同问题：哪些观察属于 Ruby 接口，哪些只属于锁定 CRuby 实现。
# 输入：语言常量、RubyVM、RbConfig、ObjectSpace 和 C Extension；观察：portable API、实现 namespace 及 ABI 配置。
# polyglot-family: time_locale_and_runtime
# polyglot-concept: runtime_capabilities_versions_and_feature_detection
# polyglot-related: languages/ruby/tooling_and_runtime/16_advanced_runtime_and_compat/
# polyglot-related+: test_127_public_c_abi_configuration.rb

require "assertions"
require "objspace"
require "polyglot_native"
require "rbconfig"

A = PolyglotAssertions

A.equal("ruby", RUBY_ENGINE)
A.equal("4.0.6", RUBY_VERSION)
A.truth(RubyVM.is_a?(Module))
A.equal("aarch64-linux", RbConfig::CONFIG.fetch("arch"))
A.equal("so", RbConfig::CONFIG.fetch("DLEXT"))
A.equal("CRuby 4.0.6", PolyglotNative::RELEASE)

dump = ObjectSpace.dump(Object.new)
A.truth(dump.start_with?("{"))
# RubyVM、ObjectSpace dump 和具体架构只作 CRuby 观察，不上升为跨实现语言保证。
A.truth(defined?(RubyVM::InstructionSequence))

A.done
