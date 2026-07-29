# frozen_string_literal: true
# polyglot-covers: ruby.tooling.rubyopt-and-rubylib-isolation

require "assertions"
require "open3"
require "rbconfig"

A = PolyglotAssertions

A.nil_value(ENV["RUBYOPT"])
A.nil_value(ENV["RUBYLIB"])

stdout, stderr, status = Open3.capture3(
  {"RUBYOPT" => "-W2", "RUBYLIB" => ""},
  RbConfig.ruby,
  "-e",
  "print $VERBOSE.inspect"
)
A.equal("true", stdout)
A.equal("", stderr)
A.truth(status.success?)
A.nil_value(ENV["RUBYOPT"])
A.nil_value(ENV["RUBYLIB"])

A.done
