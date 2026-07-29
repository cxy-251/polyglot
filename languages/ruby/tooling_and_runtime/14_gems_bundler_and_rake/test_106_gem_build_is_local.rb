# frozen_string_literal: true
# polyglot-covers: ruby.packages.gem-build-is-local

require "assertions"
require "package_helpers"
require "rubygems/package"

A = PolyglotAssertions
P = PolyglotRubyPackages

_source, archive = P.build_gem("gem-build")
A.truth(File.file?(archive))
A.truth(File.basename(archive).start_with?("polyglot_ruby_fixture-0.1.0"))

package = Gem::Package.new(archive)
A.equal("polyglot_ruby_fixture", package.spec.name)
A.equal(Gem::Version.new("0.1.0"), package.spec.version)
A.includes(package.spec.files, "exe/polyglot-ruby-fixture")
A.truth(File.size(archive).positive?)

A.done
