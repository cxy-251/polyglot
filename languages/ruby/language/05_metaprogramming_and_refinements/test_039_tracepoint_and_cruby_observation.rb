# frozen_string_literal: true
# polyglot-covers: ruby.metaprogramming.tracepoint-and-rubyvm-observation

require "assertions"

A = PolyglotAssertions

def traced_method(value)
  value + 1
end

events = []
trace = TracePoint.new(:call, :return) do |point|
  events << [point.event, point.method_id] if point.method_id == :traced_method
end
result = trace.enable { traced_method(2) }

A.equal(3, result)
A.equal([[:call, :traced_method], [:return, :traced_method]], events)
A.falsey(trace.enabled?)

# RubyVM::InstructionSequence 是锁定 CRuby 的实现观察；课程只检测能力和对象接口，
# 不把 opcode 文本、优化选择或编译器输出当作 Ruby 语言保证。
A.truth(defined?(RubyVM::InstructionSequence))
sequence = RubyVM::InstructionSequence.compile("1 + 2")
A.same(RubyVM::InstructionSequence, sequence.class)
A.truth(sequence.to_a.is_a?(Array))

A.done
