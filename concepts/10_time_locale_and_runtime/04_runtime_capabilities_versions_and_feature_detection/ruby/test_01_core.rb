# 共同问题：运行时版本和可选 capability 怎样检测。
# 输入：RUBY_ENGINE、RUBY_VERSION、respond_to?、defined?、RubyVM 和 Ractor；观察：结构化版本及 feature probing。
# polyglot-family: time_locale_and_runtime
# polyglot-concept: runtime_capabilities_versions_and_feature_detection
# polyglot-related: languages/ruby/tooling_and_runtime/13_command_parser_and_runtime/
# polyglot-related+: test_102_runtime_capabilities_and_cruby_interfaces.rb

require "assertions"

A = PolyglotAssertions

A.truth(RUBY_ENGINE.is_a?(String) && !RUBY_ENGINE.empty?)
A.truth(RUBY_VERSION.match?(/\A\d+\.\d+\.\d+\z/))
A.equal(3, RUBY_VERSION.split(".").map { Integer(_1) }.length)
A.truth(defined?(Ractor::Port))
A.truth(Ractor.respond_to?(:shareable?))
A.truth(GC.respond_to?(:compact))
A.falsey(Object.new.respond_to?(:polyglot_missing_capability))

if RUBY_ENGINE == "ruby"
  A.truth(defined?(RubyVM::InstructionSequence))
else
  A.nil_value(defined?(RubyVM::InstructionSequence))
end

A.done
