# frozen_string_literal: true
# polyglot-covers: ruby.tooling.ruby-e-stdin-and-argv

require "assertions"
require "helpers"
require "optparse"

A = PolyglotAssertions
H = PolyglotRubyHelpers

stdout, stderr, status = H.ruby_command(
  "-e",
  "print [ARGV, STDIN.read].inspect",
  "one",
  "two",
  stdin_data: "input"
)
A.equal('[["one", "two"], "input"]', stdout)
A.equal("", stderr)
A.truth(status.success?)

root = H.temporary_path("include-option")
Dir.mkdir(root)
File.write(File.join(root, "course_feature.rb"), "COURSE_FEATURE = 42\n")
stdout, stderr, status = H.ruby_command("-I", root, "-r", "course_feature", "-e", "print COURSE_FEATURE")
A.equal("42", stdout)
A.equal("", stderr)
A.truth(status.success?)

_stdout, syntax_error, syntax_status = H.ruby_command("-c", "-e", "class Broken")
A.falsey(syntax_status.success?)
A.matches(/syntax error/i, syntax_error)

stdout, _stderr, status = H.ruby_command("-W0", "-e", "print $VERBOSE.inspect")
A.equal("nil", stdout)
A.truth(status.success?)
stdout, _stderr, status = H.ruby_command("-W2", "-e", "print $VERBOSE.inspect")
A.equal("true", stdout)
A.truth(status.success?)
stdout, _stderr, status = H.ruby_command("--enable-frozen-string-literal", "-e", "print 'ruby'.frozen?")
A.equal("true", stdout)
A.truth(status.success?)

options = {count: 1}
parser = OptionParser.new do |configuration|
  configuration.on("--count N", Integer) { |value| options[:count] = value }
  configuration.on("--verbose") { options[:verbose] = true }
end
remaining = parser.parse(%w[--count 3 --verbose input.txt])
A.equal({count: 3, verbose: true}, options)
A.equal(["input.txt"], remaining)
A.raises(OptionParser::InvalidArgument) { parser.parse(%w[--count nope]) }

A.done
