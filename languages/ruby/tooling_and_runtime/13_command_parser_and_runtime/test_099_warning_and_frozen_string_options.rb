# frozen_string_literal: true
# polyglot-covers: ruby.tooling.warning-and-frozen-string-options

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

stdout, _stderr, status = H.ruby_command("-W0", "-e", "print $VERBOSE.inspect")
A.equal("nil", stdout)
A.truth(status.success?)

stdout, _stderr, status = H.ruby_command("-W1", "-e", "print $VERBOSE.inspect")
A.equal("false", stdout)
A.truth(status.success?)

stdout, _stderr, status = H.ruby_command("-W2", "-e", "print $VERBOSE.inspect")
A.equal("true", stdout)
A.truth(status.success?)

stdout, _stderr, status = H.ruby_command(
  "--enable-frozen-string-literal",
  "-e",
  "print 'ruby'.frozen?"
)
A.equal("true", stdout)
A.truth(status.success?)

A.done
