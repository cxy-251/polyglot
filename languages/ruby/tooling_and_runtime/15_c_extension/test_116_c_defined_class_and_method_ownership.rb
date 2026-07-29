# frozen_string_literal: true
# polyglot-covers: ruby.c-extension.c-defined-class-and-method-ownership

require "assertions"
require "polyglot_native"

A = PolyglotAssertions

A.equal("PolyglotNative::Box", PolyglotNative::Box.name)
A.same(Object, PolyglotNative::Box.superclass)
A.same(PolyglotNative::Box, PolyglotNative::Box.instance_method(:label).owner)
A.nil_value(PolyglotNative::Box.instance_method(:append).source_location)

box = PolyglotNative::Box.new("ruby")
A.truth(box.is_a?(PolyglotNative::Box))
A.equal("ruby", box.label)
A.equal(0, box.count)

A.done
