# frozen_string_literal: true
# polyglot-covers: ruby.metaprogramming.tracepoint-and-rubyvm-observation

require "assertions"

A = PolyglotAssertions

def traced_method(value)
  value + 1
end

A.case("TracePoint observes selected call boundaries only while enabled") do
  events = []
  trace = TracePoint.new(:call, :return) do |point|
    events << [point.event, point.method_id] if point.method_id == :traced_method
  end
  result = trace.enable { traced_method(2) }

  A.equal(3, result)
  A.equal([[:call, :traced_method], [:return, :traced_method]], events)
  A.falsey(trace.enabled?)
end

A.case("InstructionSequence is a CRuby observation without stable opcode guarantees") do
  A.truth(defined?(RubyVM::InstructionSequence))
  sequence = RubyVM::InstructionSequence.compile("1 + 2")
  A.same(RubyVM::InstructionSequence, sequence.class)
  A.truth(sequence.to_a.is_a?(Array))
end

A.done
