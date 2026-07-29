# frozen_string_literal: true
# polyglot-covers: ruby.c-extension.typed-data-gc-and-compaction

require "assertions"
require "polyglot_native"

A = PolyglotAssertions

A.equal("PolyglotNative::Box", PolyglotNative::Box.name)
A.same(Object, PolyglotNative::Box.superclass)
A.same(PolyglotNative::Box, PolyglotNative::Box.instance_method(:label).owner)
A.nil_value(PolyglotNative::Box.instance_method(:append).source_location)

source = +"ruby"
box = PolyglotNative::Box.new(source)
source << "-caller"
# fixture 在 initialize 中复制字符串，因此 C 持有值不与调用者的可变 String 共享。
A.equal("ruby", box.label)
A.equal(0, box.count)
A.same(box, box.append("-native"))
A.equal("ruby-native", box.label)
A.equal(1, box.count)

GC.start
GC.compact if GC.respond_to?(:compact)
A.equal("ruby-native", box.label)
A.equal(1, box.count)
# label getter 返回副本；调用者不能绕过 native object 的所有权边界直接改内部 VALUE。
A.falsey(box.label.equal?(box.label))

A.done
