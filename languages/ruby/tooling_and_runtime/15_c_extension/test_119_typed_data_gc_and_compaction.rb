# frozen_string_literal: true
# polyglot-covers: ruby.c-extension.typed-data-gc-and-compaction

require "assertions"
require "polyglot_native"

A = PolyglotAssertions

source = +"ruby"
box = PolyglotNative::Box.new(source)
source << "-caller"
A.equal("ruby", box.label)
A.equal(0, box.count)

A.same(box, box.append("-native"))
A.equal("ruby-native", box.label)
A.equal(1, box.count)

GC.start
GC.compact if GC.respond_to?(:compact)
A.equal("ruby-native", box.label)
A.equal(1, box.count)
A.falsey(box.label.equal?(box.label))

A.done
