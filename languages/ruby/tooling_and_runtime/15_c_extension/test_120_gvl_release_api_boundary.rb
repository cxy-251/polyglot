# frozen_string_literal: true
# polyglot-covers: ruby.c-extension.gvl-release-api-boundary

require "assertions"
require "polyglot_native"

A = PolyglotAssertions

A.case("the no-GVL wrapper validates Ruby arguments before running its integer loop") do
  A.equal(0, PolyglotNative.without_gvl_sum(0))
  A.equal(55, PolyglotNative.without_gvl_sum(10))
  A.equal(5_000_050_000, PolyglotNative.without_gvl_sum(100_000))
  A.raises(ArgumentError, "non-negative") { PolyglotNative.without_gvl_sum(-1) }
  A.raises(TypeError) { PolyglotNative.without_gvl_sum("10") }
end

A.case("a Thread publishes the native result after the C function reacquires the GVL") do
  values = Queue.new
  worker = Thread.new do
    value = PolyglotNative.without_gvl_sum(1_000)
    values << value
    value
  end
  A.equal(500_500, values.pop)
  A.equal(500_500, worker.value)
end

A.done
