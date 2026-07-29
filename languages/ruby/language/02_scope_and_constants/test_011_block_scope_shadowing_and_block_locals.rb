# frozen_string_literal: true
# polyglot-covers: ruby.scope.nested-scope-and-shadowing

require "assertions"

A = PolyglotAssertions

shared = 1
shadowed = 10
outside_only = :outside
result = [2].map do |shadowed; outside_only|
  shared += shadowed
  outside_only = shadowed * 10
  [shared, outside_only]
end

A.equal([[3, 20]], result)
A.equal(3, shared)
A.equal(10, shadowed)
A.equal(:outside, outside_only)
A.raises(NameError) { eval("outside_only_from_block", binding) }

# 不在分号后的普通外部局部变量由 block 捕获；赋值会修改同一个捕获槽。
captured = :outer
1.times { captured = :changed }
A.equal(:changed, captured)

A.done
