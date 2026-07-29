# frozen_string_literal: true
# polyglot-covers: ruby.packages.bundler-path-dependency-and-lock

require "assertions"
require "package_helpers"

A = PolyglotAssertions
P = PolyglotRubyPackages

application = P.write_bundler_app("bundle-lock")
environment = P.bundler_environment(application)
stdout, stderr, status = P.run_tool(
  "bundle",
  "lock",
  "--local",
  chdir: application,
  environment:
)
A.truth(status.success?, "#{stdout}\n#{stderr}")

lockfile = File.read(File.join(application, "Gemfile.lock"))
A.truth(lockfile.include?("PATH"))
A.truth(lockfile.include?("polyglot_ruby_fixture (0.1.0)"))
A.truth(lockfile.include?("BUNDLED WITH"))

stdout, stderr, status = P.run_tool(
  "bundle",
  "install",
  "--local",
  chdir: application,
  environment:
)
A.truth(status.success?, "#{stdout}\n#{stderr}")

A.done
