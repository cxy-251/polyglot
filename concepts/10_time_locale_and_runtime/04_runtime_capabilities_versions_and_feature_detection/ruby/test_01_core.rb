# 共同问题：运行时版本和可选 capability 怎样精确检测。
# 输入：RUBY_ENGINE、RUBY_VERSION、respond_to?、defined?、RubyVM 和 Ractor；观察：锁定 release 及 feature probing。
# polyglot-family: time_locale_and_runtime
# polyglot-concept: runtime_capabilities_versions_and_feature_detection
# polyglot-related: languages/ruby/tooling_and_runtime/16_advanced_runtime_and_compat/
# polyglot-related+: test_128_locked_runtime_contract.rb

require "assertions"

A = PolyglotAssertions

A.equal("ruby", RUBY_ENGINE)
A.equal("4.0.6", RUBY_VERSION)
A.equal("03b6d3f8898a28604fe6cb00eae3226b821168f4", RUBY_REVISION)
A.truth(defined?(RubyVM))
A.truth(defined?(Ractor::Port))
A.truth(Ractor.respond_to?(:shareable?))
A.truth(GC.respond_to?(:compact))
A.falsey(Object.new.respond_to?(:polyglot_missing_capability))

A.done
