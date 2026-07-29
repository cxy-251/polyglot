# frozen_string_literal: true
# polyglot-covers: ruby.tooling.instruction-sequence-observation

require "assertions"

A = PolyglotAssertions

A.equal("ruby", RUBY_ENGINE)
A.truth(defined?(RubyVM::InstructionSequence))

sequence = RubyVM::InstructionSequence.compile("left = 20; left * 2")
A.same(RubyVM::InstructionSequence, sequence.class)
A.equal(40, sequence.eval)
A.truth(sequence.disasm.include?("putobject"))
A.truth(sequence.to_a.is_a?(Array))
A.truth(sequence.path.is_a?(String))

# 指令名称与布局只作为锁定 CRuby 4.0.6 的诊断观察，不作为 Ruby 语言保证。
A.equal("4.0.6", RUBY_VERSION)

A.done
