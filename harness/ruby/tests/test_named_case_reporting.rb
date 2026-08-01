# frozen_string_literal: true

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

support_directory = File.expand_path("../support", __dir__)

A.case("named passing cases report independently and emit runtime metrics") do
  source = <<~'RUBY'
    require "assertions"
    A = PolyglotAssertions
    A.case("value equality") { A.equal(42, 40 + 2) }
    A.case("exception boundary") { A.raises(ArgumentError) { Integer("nope") } }
    A.done
  RUBY
  stdout, stderr, status = H.ruby_command(
    "-I",
    support_directory,
    "-e",
    source,
    environment: {"POLYGLOT_TEST_LAYER" => "harness"}
  )

  A.truth(status.success?, stderr)
  A.includes(stdout, "PASS -e :: value equality (1 assertions)")
  A.includes(stdout, "PASS -e :: exception boundary (1 assertions)")
  A.includes(stdout, '"cases":2')
  A.includes(stdout, '"assertions":2')
  A.includes(stdout, '"failed":0')
end

A.case("a failed case preserves diagnostics and does not stop later cases") do
  source = <<~'RUBY'
    require "assertions"
    A = PolyglotAssertions
    A.case("wrong value") { A.equal(1, 2) }
    A.case("unexpected error") { raise ArgumentError, "original problem" }
    A.case("still runs") { A.equal(:continued, :continued) }
    A.done
  RUBY
  stdout, stderr, status = H.ruby_command(
    "-I",
    support_directory,
    "-e",
    source,
    environment: {"POLYGLOT_TEST_LAYER" => "harness"}
  )

  A.falsey(status.success?)
  A.includes(stdout, "FAIL -e :: wrong value")
  A.includes(stdout, "  assertion: equal")
  A.includes(stdout, "  expected: 1")
  A.includes(stdout, "  actual: 2")
  A.includes(stdout, "original: PolyglotAssertions::AssertionFailure")
  A.includes(stdout, "FAIL -e :: unexpected error")
  A.includes(stdout, "original: ArgumentError: original problem")
  A.includes(stdout, "PASS -e :: still runs (1 assertions)")
  A.includes(stdout, '"cases":3')
  A.includes(stdout, '"failed":2')
  A.includes(stderr, "PolyglotAssertions::SuiteFailure")
end

A.done
