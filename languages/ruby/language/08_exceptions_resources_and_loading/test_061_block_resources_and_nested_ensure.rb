# frozen_string_literal: true
# polyglot-covers: ruby.resources.block-resources-and-nested-ensure

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

path = H.temporary_path("resource.txt")
handle = nil
File.open(path, "w") do |file|
  handle = file
  file.write("content")
  A.falsey(file.closed?)
end
A.truth(handle.closed?)
A.equal("content", File.read(path))

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

A.done
