# frozen_string_literal: true
# polyglot-covers: ruby.packages.rdoc-local-generation

require "assertions"
require "package_helpers"

A = PolyglotAssertions
P = PolyglotRubyPackages

source = P.prepare_fixture("rdoc")
output = File.join(source, "docs")
stdout, stderr, status = P.run_tool(
  "rdoc",
  "--quiet",
  "--op",
  output,
  "lib",
  chdir: source
)
A.truth(status.success?, "#{stdout}\n#{stderr}")
A.truth(File.file?(File.join(output, "index.html")))
A.truth(File.file?(File.join(output, "PolyglotRubyFixture.html")))
A.truth(File.read(File.join(output, "index.html")).include?("Polyglot"))

A.done
