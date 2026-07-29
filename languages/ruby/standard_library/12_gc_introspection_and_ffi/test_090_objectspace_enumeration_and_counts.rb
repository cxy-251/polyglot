# frozen_string_literal: true
# polyglot-covers: ruby.runtime.objectspace-enumeration-and-counts

require "assertions"
require "objspace"

A = PolyglotAssertions

marker_class = Class.new
first = marker_class.new
second = marker_class.new
observed = ObjectSpace.each_object(marker_class).to_a

A.includes(observed, first)
A.includes(observed, second)
A.equal(first.object_id, first.__id__)

counts = ObjectSpace.count_objects
A.truth(counts[:TOTAL].is_a?(Integer))
A.truth(counts[:T_OBJECT].is_a?(Integer))
A.truth(ObjectSpace.memsize_of(first).positive?)

A.done
