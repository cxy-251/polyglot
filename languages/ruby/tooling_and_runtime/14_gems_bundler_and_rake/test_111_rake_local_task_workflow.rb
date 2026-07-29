# frozen_string_literal: true
# polyglot-covers: ruby.packages.rake-local-task-workflow

require "assertions"
require "package_helpers"

A = PolyglotAssertions
P = PolyglotRubyPackages

source = P.prepare_fixture("rake")
stdout, stderr, status = P.run_tool("rake", "-T", chdir: source)
A.truth(status.success?, stderr)
A.truth(stdout.include?("rake verify"))

stdout, stderr, status = P.run_tool("rake", "verify", chdir: source)
A.equal("fixture verified\n", stdout)
A.equal("", stderr)
A.truth(status.success?)

stdout, stderr, status = P.run_tool("rake", chdir: source)
A.equal("fixture verified\n", stdout)
A.equal("", stderr)
A.truth(status.success?)

A.done
