# frozen_string_literal: true
# polyglot-covers: ruby.runtime.child-process-state-isolation

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

ENV.delete("POLYGLOT_CHILD_ONLY")
original_verbose = $VERBOSE
stdout, stderr, status = H.ruby_command(
  "-e",
  "ENV['POLYGLOT_CHILD_ONLY']='yes'; $VERBOSE=true; Object.const_set(:ChildOnly, 42); print ChildOnly"
)
A.truth(status.success?, stderr)
A.equal("42", stdout)
A.nil_value(ENV["POLYGLOT_CHILD_ONLY"])
A.same(original_verbose, $VERBOSE)
A.falsey(Object.const_defined?(:ChildOnly, false))

A.done
