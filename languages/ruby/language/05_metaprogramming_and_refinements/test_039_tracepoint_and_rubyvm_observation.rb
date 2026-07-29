# frozen_string_literal: true
# polyglot-covers: ruby.metaprogramming.tracepoint-and-rubyvm-observation

require "assertions"

A = PolyglotAssertions

def traced_method(value)
  value + 1
end

events = []
trace = TracePoint.new(:call, :return) do |point|
  events << point.event if point.method_id == :traced_method
end
result = trace.enable { traced_method(2) }

A.equal(3, result)
A.equal(%i[call return], events)
A.falsey(trace.enabled?)
A.truth(defined?(RubyVM))

if defined?(RubyVM::InstructionSequence)
  sequence = RubyVM::InstructionSequence.compile("1 + 2")
  A.same(RubyVM::InstructionSequence, sequence.class)
  A.truth(sequence.disasm.include?("putobject"))
else
  A.truth(false, "CRuby 4.0.6 should expose InstructionSequence")
end

A.done
