# frozen_string_literal: true
# polyglot-covers: ruby.tooling.instruction-sequence-observation

require "assertions"
require "rbconfig"

A = PolyglotAssertions

A.case("portable runtime and build interfaces expose values without assuming an install layout") do
  A.truth(defined?(RUBY_ENGINE))
  A.truth(RUBY_VERSION.match?(/\A\d+\.\d+\.\d+\z/))
  A.truth(RbConfig.ruby.end_with?("/ruby"))
  A.truth(RbConfig::CONFIG.fetch("target_os").is_a?(String))
  A.truth(RbConfig::CONFIG.fetch("DLEXT").is_a?(String))
end

A.case("InstructionSequence is a capability-detected CRuby interface with unstable internals") do
  A.equal("ruby", RUBY_ENGINE)
  A.truth(defined?(RubyVM::InstructionSequence))
  sequence = RubyVM::InstructionSequence.compile("left = 20; left * 2")
  A.same(RubyVM::InstructionSequence, sequence.class)
  A.equal(40, sequence.eval)
  A.truth(sequence.to_a.is_a?(Array))
  A.truth(sequence.path.is_a?(String))
end

A.case("respond_to? detects optional interfaces without parsing version strings") do
  A.truth(Ractor.respond_to?(:shareable?))
  A.truth(GC.respond_to?(:compact))
  A.falsey(Object.new.respond_to?(:polyglot_missing_capability))
end

A.done
