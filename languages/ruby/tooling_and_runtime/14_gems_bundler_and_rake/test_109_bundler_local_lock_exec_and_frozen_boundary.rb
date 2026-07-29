# frozen_string_literal: true
# polyglot-covers: ruby.packages.bundler-path-dependency-and-lock

require "assertions"
require "package_helpers"

A = PolyglotAssertions
P = PolyglotRubyPackages

application = P.write_bundler_app("bundle-workflow")
environment = P.bundler_environment(application)
%w[lock install].each do |command|
  stdout, stderr, status = P.run_tool(
    "bundle",
    command,
    "--local",
    chdir: application,
    environment:
  )
  A.truth(status.success?, "#{stdout}\n#{stderr}")
end

lockfile_path = File.join(application, "Gemfile.lock")
lockfile = File.read(lockfile_path)
A.truth(lockfile.include?("PATH"))
A.truth(lockfile.include?("polyglot_ruby_fixture (0.1.0)"))
A.truth(lockfile.include?("BUNDLED WITH"))

stdout, stderr, status = P.run_tool(
  "bundle",
  "exec",
  "ruby",
  "-rpolyglot_ruby_fixture",
  "-e",
  "print PolyglotRubyFixture::VERSION",
  chdir: application,
  environment: environment.merge("BUNDLE_FROZEN" => "true")
)
A.equal("0.1.0", stdout)
A.equal("", stderr)
A.truth(status.success?)

unlocked_application = P.write_bundler_app("bundle-frozen-without-lock")
unlocked_environment = P.bundler_environment(unlocked_application)
_stdout, _stderr, frozen_status = P.run_tool(
  "bundle",
  "install",
  "--local",
  chdir: unlocked_application,
  environment: unlocked_environment.merge("BUNDLE_FROZEN" => "true")
)
A.falsey(frozen_status.success?)
A.equal(lockfile, File.read(lockfile_path))

A.done
