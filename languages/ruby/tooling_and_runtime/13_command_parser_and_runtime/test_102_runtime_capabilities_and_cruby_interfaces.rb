# frozen_string_literal: true
# polyglot-covers: ruby.tooling.instruction-sequence-observation

require "assertions"
require "rbconfig"

A = PolyglotAssertions

A.truth(defined?(RUBY_ENGINE))
A.truth(RUBY_VERSION.match?(/\A\d+\.\d+\.\d+\z/))
A.truth(RbConfig.ruby.end_with?("/ruby"))
A.truth(RbConfig::CONFIG.fetch("target_os").is_a?(String))
A.truth(RbConfig::CONFIG.fetch("DLEXT").is_a?(String))

# RubyVM 是 CRuby namespace，不是跨实现 Ruby API；使用前必须做 capability detection。
A.equal("ruby", RUBY_ENGINE)
A.truth(defined?(RubyVM::InstructionSequence))
sequence = RubyVM::InstructionSequence.compile("left = 20; left * 2")
A.same(RubyVM::InstructionSequence, sequence.class)
A.equal(40, sequence.eval)
A.truth(sequence.to_a.is_a?(Array))
A.truth(sequence.path.is_a?(String))
# 不断言 disasm opcode、JIT 状态、平台架构或编译结果布局。

A.truth(Ractor.respond_to?(:shareable?))
A.truth(GC.respond_to?(:compact))
A.falsey(Object.new.respond_to?(:polyglot_missing_capability))

A.done
