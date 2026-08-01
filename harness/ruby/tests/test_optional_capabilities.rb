# frozen_string_literal: true

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

A.case("locked runtime exposes required Ractor and VM inspection interfaces") do
  A.truth(defined?(Ractor::Port))
  A.truth(defined?(RubyVM::InstructionSequence))
end

A.case("optional Ruby Box capability is detected in an isolated child") do
  environment = {"RUBY_BOX" => "1", "RUBYOPT" => "", "RUBYLIB" => ""}
  stdout, stderr, status = H.ruby_command(
    "-W:no-experimental",
    "-e",
    "print defined?(Ruby::Box)",
    environment:
  )

  A.truth(status.success?, stderr)
  A.truth(["constant", ""].include?(stdout))
end

A.case("the harness does not silently enable optional JITs") do
  enabled_jits = []
  enabled_jits << :yjit if RubyVM.const_defined?(:YJIT) && RubyVM::YJIT.enabled?
  enabled_jits << :zjit if RubyVM.const_defined?(:ZJIT) && RubyVM::ZJIT.enabled?
  A.equal([], enabled_jits)
end

A.done
