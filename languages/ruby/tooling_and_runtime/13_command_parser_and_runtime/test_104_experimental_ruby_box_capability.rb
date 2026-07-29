# frozen_string_literal: true
# polyglot-covers: ruby.tooling.experimental-ruby-box-capability

require "assertions"
require "helpers"
require "open3"
require "rbconfig"

A = PolyglotAssertions
H = PolyglotRubyHelpers

environment = {"RUBY_BOX" => "1", "RUBYOPT" => "", "RUBYLIB" => ""}
stdout, stderr, status = Open3.capture3(
  environment,
  RbConfig.ruby,
  "-W:no-experimental",
  "-e",
  "print defined?(Ruby::Box)"
)
A.truth(status.success?)
A.equal("", stderr)
A.truth(["constant", ""].include?(stdout))

if stdout == "constant"
  fixture = H.temporary_path("box_fixture.rb")
  File.write(fixture, "BOX_VALUE = 42\n")
  code = "box = Ruby::Box.new; box.load(ARGV.fetch(0)); print box::BOX_VALUE"
  box_stdout, box_stderr, box_status = Open3.capture3(
    environment,
    RbConfig.ruby,
    "-W:no-experimental",
    "-e",
    code,
    fixture
  )
  A.truth(box_status.success?)
  A.equal("42", box_stdout)
  A.equal("", box_stderr)
else
  A.falsey(defined?(Ruby::Box))
end

A.done
