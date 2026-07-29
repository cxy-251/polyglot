# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.process-environment-and-spawn

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

stdout, stderr, status = H.ruby_command(
  "-e",
  "print [ENV['POLYGLOT_CHILD'], Dir.pwd].join('|')",
  stdin_data: ""
)
A.equal("", stderr)
A.truth(status.success?)
A.truth(stdout.end_with?(Dir.pwd))

read_end, write_end = IO.pipe
pid = Process.spawn(
  {"POLYGLOT_CHILD" => "isolated"},
  RbConfig.ruby,
  "-e",
  "print ENV.fetch('POLYGLOT_CHILD')",
  out: write_end
)
write_end.close
A.equal("isolated", read_end.read)
read_end.close
_child, child_status = Process.wait2(pid)
A.truth(child_status.success?)
A.nil_value(ENV["POLYGLOT_CHILD"])

A.done
