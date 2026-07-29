# frozen_string_literal: true
# polyglot-covers: ruby.c-extension.gvl-release-api-boundary

require "assertions"
require "polyglot_native"

A = PolyglotAssertions

A.equal(0, PolyglotNative.without_gvl_sum(0))
A.equal(55, PolyglotNative.without_gvl_sum(10))
A.equal(5_000_050_000, PolyglotNative.without_gvl_sum(100_000))
A.raises(ArgumentError, "non-negative") { PolyglotNative.without_gvl_sum(-1) }
A.raises(TypeError) { PolyglotNative.without_gvl_sum("10") }

# C 函数只在不访问 Ruby 对象的整数循环期间释放 GVL；返回 VALUE 前已重新取得 GVL。
values = Queue.new
worker = Thread.new do
  value = PolyglotNative.without_gvl_sum(1_000)
  values << value
  value
end
A.equal(500_500, values.pop)
A.equal(500_500, worker.value)

A.done
