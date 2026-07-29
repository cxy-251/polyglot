# frozen_string_literal: true
# polyglot-covers: ruby.tooling.syntax-include-and-require-options

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

root = H.temporary_path("include-option")
Dir.mkdir(root)
File.write(File.join(root, "course_feature.rb"), "COURSE_FEATURE = 42\n")

stdout, stderr, status = H.ruby_command(
  "-I",
  root,
  "-r",
  "course_feature",
  "-e",
  "print COURSE_FEATURE"
)
A.equal("42", stdout)
A.equal("", stderr)
A.truth(status.success?)

_stdout, syntax_error, syntax_status = H.ruby_command("-c", "-e", "class Broken")
A.falsey(syntax_status.success?)
A.matches(/syntax error/i, syntax_error)

A.done
