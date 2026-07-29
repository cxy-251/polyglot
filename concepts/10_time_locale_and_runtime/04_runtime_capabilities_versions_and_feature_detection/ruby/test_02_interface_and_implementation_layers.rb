# 共同问题：哪些观察属于 Ruby 接口，哪些只属于当前实现。
# 输入：语言常量、RubyVM、RbConfig 和 ObjectSpace；观察：portable API、实现 namespace 及诊断能力。
# polyglot-family: time_locale_and_runtime
# polyglot-concept: runtime_capabilities_versions_and_feature_detection
# polyglot-related: languages/ruby/tooling_and_runtime/13_command_parser_and_runtime/
# polyglot-related+: test_102_runtime_capabilities_and_cruby_interfaces.rb
# polyglot-related: languages/ruby/standard_library/12_gc_introspection_and_ffi/
# polyglot-related+: test_090_objectspace_enumeration_allocation_and_dump_observation.rb

require "assertions"
require "json"
require "objspace"
require "rbconfig"

A = PolyglotAssertions

A.truth(RUBY_ENGINE.is_a?(String))
A.truth(RUBY_VERSION.is_a?(String))
A.truth(RbConfig::CONFIG.fetch("arch").is_a?(String))
A.truth(RbConfig::CONFIG.fetch("DLEXT").is_a?(String))

if RUBY_ENGINE == "ruby"
  A.truth(RubyVM.is_a?(Module))
  A.truth(defined?(RubyVM::InstructionSequence))
  dump = JSON.parse(ObjectSpace.dump(Object.new))
  A.truth(dump.fetch("type").is_a?(String))
end

# RubyVM、ObjectSpace dump、架构字符串和动态库扩展名只能在 capability 检测后使用。
A.falsey(Object.const_defined?(:PolyglotPortableRubyVM, false))

A.done
