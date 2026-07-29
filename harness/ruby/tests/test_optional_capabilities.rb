# frozen_string_literal: true

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

A.truth(defined?(Ractor::Port))
A.truth(defined?(RubyVM::InstructionSequence))

environment = {"RUBY_BOX" => "1", "RUBYOPT" => "", "RUBYLIB" => ""}
stdout, stderr, status = H.ruby_command(
  "-W:no-experimental",
  "-e",
  "print defined?(Ruby::Box)",
  environment:
)
A.truth(status.success?, stderr)
A.truth(["constant", ""].include?(stdout))
A.falsey(RubyVM::YJIT.enabled?) if RubyVM.const_defined?(:YJIT)
A.falsey(RubyVM::ZJIT.enabled?) if RubyVM.const_defined?(:ZJIT)

A.done
