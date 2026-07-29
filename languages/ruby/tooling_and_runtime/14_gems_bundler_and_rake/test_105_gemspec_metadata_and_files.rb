# frozen_string_literal: true
# polyglot-covers: ruby.packages.gemspec-metadata-and-files

require "assertions"
require "package_helpers"

A = PolyglotAssertions
P = PolyglotRubyPackages

source = P.prepare_fixture("gemspec")
specification = Gem::Specification.load(
  File.join(source, "polyglot_ruby_fixture.gemspec")
)

A.equal("polyglot_ruby_fixture", specification.name)
A.equal(Gem::Version.new("0.1.0"), specification.version)
A.equal(Gem::Requirement.new("= 4.0.6"), specification.required_ruby_version)
A.equal(["polyglot-ruby-fixture"], specification.executables)
A.includes(specification.files, "lib/polyglot_ruby_fixture.rb")
A.equal(["lib"], specification.require_paths)
A.equal("MIT", specification.license)

A.done
