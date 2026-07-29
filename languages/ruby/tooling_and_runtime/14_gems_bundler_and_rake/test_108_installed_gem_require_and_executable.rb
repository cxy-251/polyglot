# frozen_string_literal: true
# polyglot-covers: ruby.packages.installed-gem-require-and-executable

require "assertions"
require "package_helpers"

A = PolyglotAssertions
P = PolyglotRubyPackages

_source, archive = P.build_gem("gem-executable")
_stdout, stderr, status = P.run_tool(
  "gem",
  "install",
  "--local",
  "--no-document",
  archive,
  chdir: File.dirname(archive)
)
A.truth(status.success?, stderr)

environment = PolyglotRubyHelpers.isolated_gem_environment
stdout, stderr, status = Open3.capture3(
  environment,
  RbConfig.ruby,
  "-rpolyglot_ruby_fixture",
  "-e",
  "print PolyglotRubyFixture.label('loaded')"
)
A.equal("ruby:loaded", stdout)
A.equal("", stderr)
A.truth(status.success?)

executable = File.join(ENV.fetch("GEM_HOME"), "bin", "polyglot-ruby-fixture")
stdout, stderr, status = Open3.capture3(environment, executable, "cli")
A.equal("ruby:cli\n", stdout)
A.equal("", stderr)
A.truth(status.success?)

A.done
