# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.tempfile-and-stringio

require "assertions"
require "stringio"
require "tempfile"

A = PolyglotAssertions

A.case("Tempfile.create yields an open file and unlinks it after block exit") do
  path = nil
  Tempfile.create(["polyglot-ruby-", ".txt"], ENV.fetch("POLYGLOT_RUBY_TEST_TMP")) do |file|
    path = file.path
    file.write("temporary")
    file.rewind
    A.equal("temporary", file.read)
    A.falsey(file.closed?)
  end
  A.falsey(File.exist?(path))
end

A.case("StringIO implements line-oriented IO state over an owned String") do
  stream = StringIO.new(+"one\ntwo\n")
  A.equal("one\n", stream.gets)
  A.equal("two\n", stream.gets)
  A.nil_value(stream.gets)
  stream.rewind
  A.equal(["one\n", "two\n"], stream.readlines)
end

A.done
