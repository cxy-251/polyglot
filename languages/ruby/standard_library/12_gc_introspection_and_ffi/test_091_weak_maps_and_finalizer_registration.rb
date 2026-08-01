# frozen_string_literal: true
# polyglot-covers: ruby.runtime.weak-map-interface

require "assertions"
require "objspace"

A = PolyglotAssertions

A.case("WeakMap returns values while both key and value remain strongly reachable") do
  map = ObjectSpace::WeakMap.new
  key = Object.new
  value = +"value"
  map[key] = value
  A.truth(map.key?(key))
  A.same(value, map[key])
  A.nil_value(map[Object.new])
  A.includes(map.keys, key)
  A.includes(map.values, value)
end

A.case("a finalizer can be registered and explicitly removed without forcing GC timing") do
  events = []
  object = Object.new
  finalizer = proc { |object_id| events << object_id }
  returned = ObjectSpace.define_finalizer(object, finalizer)
  A.equal([0, finalizer], returned)
  A.equal([], events)
  A.same(object, ObjectSpace.undefine_finalizer(object))
  A.equal([], events)
end

A.done
