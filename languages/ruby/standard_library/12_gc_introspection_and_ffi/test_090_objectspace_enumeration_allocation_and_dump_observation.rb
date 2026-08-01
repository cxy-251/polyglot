# frozen_string_literal: true
# polyglot-covers: ruby.runtime.objectspace-enumeration-and-counts

require "assertions"
require "json"
require "objspace"

A = PolyglotAssertions

A.case("ObjectSpace enumerates reachable instances and exposes diagnostic counts") do
  marker_class = Class.new
  first = marker_class.new
  second = marker_class.new
  observed = ObjectSpace.each_object(marker_class).to_a
  A.includes(observed, first)
  A.includes(observed, second)

  counts = ObjectSpace.count_objects
  A.truth(counts[:TOTAL].is_a?(Integer))
  A.truth(ObjectSpace.memsize_of(first).positive?)
end

A.case("allocation tracing records source metadata and is explicitly stopped and cleared") do
  ObjectSpace.trace_object_allocations_start
  begin
    traced = Object.new
    source = ObjectSpace.allocation_sourcefile(traced)
    line = ObjectSpace.allocation_sourceline(traced)
    A.truth(source.end_with?(File.basename(__FILE__)))
    A.truth(line.is_a?(Integer) && line.positive?)
  ensure
    ObjectSpace.trace_object_allocations_stop
    ObjectSpace.trace_object_allocations_clear
  end
end

A.case("ObjectSpace.dump is a CRuby diagnostic shape rather than a language guarantee") do
  document = JSON.parse(ObjectSpace.dump(+"runtime"))
  A.equal("STRING", document.fetch("type"))
  A.equal(7, document.fetch("bytesize"))
  A.truth(document.key?("address"))
end

A.done
