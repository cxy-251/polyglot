# frozen_string_literal: true

Gem::Specification.new do |specification|
  specification.name = "polyglot_ruby_fixture"
  specification.version = "0.1.0"
  specification.summary = "Offline fixture for the Polyglot Ruby course"
  specification.description = "A minimal local gem used to test RubyGems and Bundler without network access."
  specification.authors = ["Polyglot"]
  specification.email = ["noreply@example.invalid"]
  specification.homepage = "https://example.invalid/polyglot-ruby-fixture"
  specification.license = "MIT"
  specification.required_ruby_version = "= 4.0.6"
  specification.files = [
    "README.md",
    "exe/polyglot-ruby-fixture",
    "lib/polyglot_ruby_fixture.rb",
    "lib/polyglot_ruby_fixture/version.rb"
  ]
  specification.bindir = "exe"
  specification.executables = ["polyglot-ruby-fixture"]
  specification.require_paths = ["lib"]
  specification.metadata = {
    "source_code_uri" => "https://example.invalid/polyglot-ruby-fixture"
  }
end
