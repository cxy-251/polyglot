# frozen_string_literal: true
# polyglot-covers: ruby.c-extension.typed-data-gc-and-compaction

require "assertions"
require "polyglot_native"

A = PolyglotAssertions

A.case("TypedData publishes an ordinary Ruby class whose methods are C-defined") do
  A.equal("PolyglotNative::Box", PolyglotNative::Box.name)
  A.same(Object, PolyglotNative::Box.superclass)
  A.same(PolyglotNative::Box, PolyglotNative::Box.instance_method(:label).owner)
  A.nil_value(PolyglotNative::Box.instance_method(:append).source_location)
end

A.case("the native wrapper copies input and mutates only through its owning methods") do
  source = +"ruby"
  box = PolyglotNative::Box.new(source)
  source << "-caller"
  A.equal("ruby", box.label)
  A.equal(0, box.count)
  A.same(box, box.append("-native"))
  A.equal("ruby-native", box.label)
  A.equal(1, box.count)
end

A.case("marked TypedData survives GC and returns copies rather than its internal VALUE") do
  box = PolyglotNative::Box.new(+"ruby")
  box.append("-native")
  GC.start
  GC.compact if GC.respond_to?(:compact)
  A.equal("ruby-native", box.label)
  A.equal(1, box.count)
  A.falsey(box.label.equal?(box.label))
end

A.done
