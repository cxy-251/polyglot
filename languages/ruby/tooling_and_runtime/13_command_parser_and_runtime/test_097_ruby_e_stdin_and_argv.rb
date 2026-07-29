# frozen_string_literal: true
# polyglot-covers: ruby.tooling.ruby-e-stdin-and-argv

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

stdout, stderr, status = H.ruby_command(
  "-e",
  "print [ARGV, STDIN.read].inspect",
  "one",
  "two",
  stdin_data: "input"
)
A.equal('[["one", "two"], "input"]', stdout)
A.equal("", stderr)
A.truth(status.success?)

stdout, _stderr, status = H.ruby_command("-e", "puts RUBY_VERSION")
A.equal("4.0.6\n", stdout)
A.truth(status.success?)

A.done
