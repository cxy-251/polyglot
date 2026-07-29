# frozen_string_literal: true
# polyglot-covers: ruby.runtime.ruby-4-capability-detection

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

A.truth(defined?(Ractor::Port))
A.truth(Ractor::Port.instance_methods.include?(:receive))
A.truth(Ractor.respond_to?(:shareable?))
A.truth(defined?(RubyVM::InstructionSequence))

stdout, stderr, status = H.ruby_command(
  "-W:no-experimental",
  "-e",
  "print [RUBY_VERSION, defined?(Ruby::Box)].join('|')"
)
A.truth(status.success?, stderr)
version, box_capability = stdout.split("|", 2)
A.equal("4.0.6", version)
A.truth(["constant", ""].include?(box_capability))

A.done
