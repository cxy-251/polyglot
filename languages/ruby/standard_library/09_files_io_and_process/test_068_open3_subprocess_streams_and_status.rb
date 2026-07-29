# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.open3-subprocess-streams-and-status

require "assertions"
require "open3"
require "rbconfig"

A = PolyglotAssertions

stdout, stderr, status = Open3.capture3(
  RbConfig.ruby,
  "-e",
  "STDOUT.write(STDIN.read.upcase); STDERR.write('note')",
  stdin_data: "ruby"
)
A.equal("RUBY", stdout)
A.equal("note", stderr)
A.truth(status.success?)
A.equal(0, status.exitstatus)

_stdout, _stderr, failed = Open3.capture3(RbConfig.ruby, "-e", "exit 9")
A.falsey(failed.success?)
A.equal(9, failed.exitstatus)

A.done
