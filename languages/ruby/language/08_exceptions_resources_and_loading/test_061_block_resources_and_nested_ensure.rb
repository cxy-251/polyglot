# frozen_string_literal: true
# polyglot-covers: ruby.resources.block-resources-and-nested-ensure

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

A.case("File.open with a block closes the handle after normal completion") do
  path = H.temporary_path("resource.txt")
  handle = nil
  File.open(path, "w") do |file|
    handle = file
    file.write("content")
    A.falsey(file.closed?)
  end
  A.truth(handle.closed?)
  A.equal("content", File.read(path))
end

A.case("ensure releases acquired state while preserving the body failure") do
  events = []
  A.raises(RuntimeError, "body") do
    begin
      events << :acquired
      raise "body"
    ensure
      events << :released
    end
  end
  A.equal(%i[acquired released], events)
end

A.done
