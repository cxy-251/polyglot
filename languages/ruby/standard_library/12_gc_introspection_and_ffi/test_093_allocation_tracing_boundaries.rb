# frozen_string_literal: true
# polyglot-covers: ruby.runtime.allocation-tracing-boundaries

require "assertions"
require "objspace"

A = PolyglotAssertions

ObjectSpace.trace_object_allocations_start
begin
  object = Object.new
  source = ObjectSpace.allocation_sourcefile(object)
  line = ObjectSpace.allocation_sourceline(object)
  generation = ObjectSpace.allocation_generation(object)
  A.truth(source.end_with?(File.basename(__FILE__)))
  A.truth(line.is_a?(Integer))
  A.truth(line.positive?)
  A.truth(generation.is_a?(Integer))
  A.truth(generation >= 0)
ensure
  ObjectSpace.trace_object_allocations_stop
  ObjectSpace.trace_object_allocations_clear
end

A.done
