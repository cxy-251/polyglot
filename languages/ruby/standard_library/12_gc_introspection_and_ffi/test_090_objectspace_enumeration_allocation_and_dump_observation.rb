# frozen_string_literal: true
# polyglot-covers: ruby.runtime.objectspace-enumeration-and-counts

require "assertions"
require "json"
require "objspace"

A = PolyglotAssertions

marker_class = Class.new
first = marker_class.new
second = marker_class.new
observed = ObjectSpace.each_object(marker_class).to_a
A.includes(observed, first)
A.includes(observed, second)

counts = ObjectSpace.count_objects
A.truth(counts[:TOTAL].is_a?(Integer))
A.truth(ObjectSpace.memsize_of(first).positive?)

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

document = JSON.parse(ObjectSpace.dump(+"runtime"))
A.equal("STRING", document.fetch("type"))
A.equal(7, document.fetch("bytesize"))
# address、shape、memsize 和 dump 字段集合是 CRuby 诊断格式，不是 Ruby 对象模型保证。
A.truth(document.key?("address"))

A.done
