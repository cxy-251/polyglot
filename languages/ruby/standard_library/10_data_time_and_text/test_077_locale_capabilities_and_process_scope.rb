# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.locale-capabilities-and-process-scope

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

A.case("a child process can select C locale without changing the parent environment") do
  original_locale = ENV["LC_ALL"]
  code = <<~'RUBY'
    values = [
      ENV.fetch("LC_ALL"),
      Encoding.find("locale").name,
      format("%.2f", 1234.5),
      Time.utc(2026, 7, 29).strftime("%A %B"),
      ["\u{E4}", "a", "Z"].sort.join(",")
    ]
    print values.join("|")
  RUBY
  stdout, stderr, status = H.ruby_command(
    "-e",
    code,
    environment: {"LC_ALL" => "C"}
  )
  A.truth(status.success?, stderr)
  A.equal("C|US-ASCII|1234.50|Wednesday July|Z,a,ä", stdout)
  A.equal(original_locale, ENV["LC_ALL"])
end

A.case("core numeric parsing and String ordering do not offer locale-sensitive alternatives") do
  A.raises(ArgumentError) { Float("1234,5") }
  A.equal(-1, "Z" <=> "a")
end

A.done
