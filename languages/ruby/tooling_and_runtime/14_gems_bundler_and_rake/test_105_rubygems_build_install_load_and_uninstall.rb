# frozen_string_literal: true
# polyglot-covers: ruby.packages.gemspec-metadata-and-files

require "assertions"
require "package_helpers"
require "rubygems/package"

A = PolyglotAssertions
P = PolyglotRubyPackages

A.case("gem build packages declared metadata, library files and executables") do
  _source, archive = P.build_gem("rubygems-metadata")
  package = Gem::Package.new(archive)
  A.equal("polyglot_ruby_fixture", package.spec.name)
  A.equal(Gem::Version.new("0.1.0"), package.spec.version)
  A.includes(package.spec.files, "lib/polyglot_ruby_fixture.rb")
  A.includes(package.spec.files, "exe/polyglot-ruby-fixture")
end

A.case("local install activates library and executable until explicit uninstall") do
  source, archive = P.build_gem("rubygems-lifecycle")
  installed = false
  begin
    stdout, stderr, status = P.run_tool(
      "gem",
      "install",
      "--local",
      "--no-document",
      archive,
      chdir: source
    )
    A.truth(status.success?, "#{stdout}\n#{stderr}")
    installed = true
    Gem::Specification.reset
    specification = Gem::Specification.find_by_name("polyglot_ruby_fixture")
    A.equal(ENV.fetch("GEM_HOME"), specification.base_dir)

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
  ensure
    if installed
      P.run_tool(
        "gem",
        "uninstall",
        "--all",
        "--executables",
        "--ignore-dependencies",
        "polyglot_ruby_fixture",
        chdir: source
      )
      Gem::Specification.reset
    end
  end
  A.equal([], Gem::Specification.find_all_by_name("polyglot_ruby_fixture"))
end

A.done
