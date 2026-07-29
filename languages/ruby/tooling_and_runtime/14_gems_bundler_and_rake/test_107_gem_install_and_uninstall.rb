# frozen_string_literal: true
# polyglot-covers: ruby.packages.gem-install-and-uninstall

require "assertions"
require "package_helpers"

A = PolyglotAssertions
P = PolyglotRubyPackages

_source, archive = P.build_gem("gem-install")
stdout, stderr, status = P.run_tool(
  "gem",
  "install",
  "--local",
  "--no-document",
  archive,
  chdir: File.dirname(archive)
)
A.truth(status.success?, "#{stdout}\n#{stderr}")

Gem::Specification.reset
installed = Gem::Specification.find_all_by_name("polyglot_ruby_fixture")
A.equal(1, installed.length)
A.equal(ENV.fetch("GEM_HOME"), installed.first.base_dir)

stdout, stderr, status = P.run_tool(
  "gem",
  "uninstall",
  "--all",
  "--executables",
  "--ignore-dependencies",
  "polyglot_ruby_fixture",
  chdir: File.dirname(archive)
)
A.truth(status.success?, "#{stdout}\n#{stderr}")
Gem::Specification.reset
A.equal([], Gem::Specification.find_all_by_name("polyglot_ruby_fixture"))

A.done
