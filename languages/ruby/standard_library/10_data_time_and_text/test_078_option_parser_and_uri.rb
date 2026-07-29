# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.option-parser-and-uri

require "assertions"
require "optparse"
require "uri"

A = PolyglotAssertions

options = {count: 1}
parser = OptionParser.new do |configuration|
  configuration.on("--count N", Integer) { |value| options[:count] = value }
  configuration.on("--verbose") { options[:verbose] = true }
end
remaining = parser.parse(%w[--count 3 --verbose input.txt])
A.equal({count: 3, verbose: true}, options)
A.equal(["input.txt"], remaining)
A.raises(OptionParser::InvalidArgument) { parser.parse(%w[--count nope]) }

uri = URI("https://example.test:8443/path?q=ruby#part")
A.equal("https", uri.scheme)
A.equal("example.test", uri.host)
A.equal(8443, uri.port)
A.equal("/path", uri.path)
A.equal("q=ruby", uri.query)

A.done
