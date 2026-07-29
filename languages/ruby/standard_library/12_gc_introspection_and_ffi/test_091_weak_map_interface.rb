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
A.includes(map.keys, key)
A.includes(map.values, value)
A.equal(1, map.size)
A.nil_value(map[Object.new])
A.same(ObjectSpace::WeakMap, map.class)

A.done
