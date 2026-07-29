# frozen_string_literal: true
# polyglot-covers: ruby.runtime.monkey-patch-process-boundary

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

code = <<~'RUBY'
  class String
    def polyglot_marker = :child
  end
  print "ruby".polyglot_marker
RUBY
stdout, stderr, status = H.ruby_command("-e", code)
A.truth(status.success?, stderr)
A.equal("child", stdout)
A.falsey("ruby".respond_to?(:polyglot_marker))
A.falsey(String.instance_methods(false).include?(:polyglot_marker))

A.done
