# frozen_string_literal: true
# polyglot-covers: ruby.packages.bundler-exec-and-frozen-lock

require "assertions"
require "package_helpers"

A = PolyglotAssertions
P = PolyglotRubyPackages

application = P.write_bundler_app("bundle-exec")
environment = P.bundler_environment(application)
%w[lock install].each do |command|
  arguments = command == "lock" ? [command, "--local"] : [command, "--local"]
  stdout, stderr, status = P.run_tool(
    "bundle",
    *arguments,
    chdir: application,
    environment:
  )
  A.truth(status.success?, "#{stdout}\n#{stderr}")
end

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

A.done
