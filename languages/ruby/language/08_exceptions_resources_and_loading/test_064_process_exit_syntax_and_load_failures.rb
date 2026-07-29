# frozen_string_literal: true
# polyglot-covers: ruby.loading.process-exit-syntax-and-load-failures

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

stdout, stderr, status = H.ruby_command("-e", "puts 'ok'; exit 7")
A.equal("ok\n", stdout)
A.equal("", stderr)
A.equal(7, status.exitstatus)

_stdout, syntax_error, syntax_status = H.ruby_command("-c", "-e", "def broken")
A.falsey(syntax_status.success?)
A.matches(/syntax error/i, syntax_error)

_stdout, load_error, load_status = H.ruby_command("-e", "require 'polyglot_missing_feature'")
A.falsey(load_status.success?)
A.truth(load_error.include?("LoadError"))

A.done
