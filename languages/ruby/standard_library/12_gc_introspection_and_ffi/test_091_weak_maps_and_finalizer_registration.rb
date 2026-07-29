# frozen_string_literal: true
# polyglot-covers: ruby.runtime.weak-map-interface

require "assertions"
require "objspace"

A = PolyglotAssertions

map = ObjectSpace::WeakMap.new
key = Object.new
value = +"value"
map[key] = value
A.truth(map.key?(key))
A.same(value, map[key])
A.nil_value(map[Object.new])

events = []
object = Object.new
finalizer = proc { |object_id| events << object_id }
returned = ObjectSpace.define_finalizer(object, finalizer)
A.equal([0, finalizer], returned)
A.equal([], events)
A.same(object, ObjectSpace.undefine_finalizer(object))
A.equal([], events)

# 弱引用可消失，finalizer 的时机和顺序也不确定；课程只断言可达对象与显式撤销。
A.includes(map.keys, key)
A.includes(map.values, value)

A.done
