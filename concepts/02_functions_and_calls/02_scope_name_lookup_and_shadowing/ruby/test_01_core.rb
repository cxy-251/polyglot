# 共同问题：局部、实例、全局、常量和同名方法怎样解析与遮蔽。
# 输入：嵌套 block、局部赋值、实例变量及常量；观察：词法捕获、解析期局部判定和对象状态。
# polyglot-family: functions_and_calls
# polyglot-concept: scope_name_lookup_and_shadowing
# polyglot-related: languages/ruby/language/02_scope_and_constants/test_009_variable_kinds_and_assignment_resolution.rb

require "assertions"

A = PolyglotAssertions

outer = :outer
observed = 1.times.map do
  inner = :inner
  [outer, inner]
end
A.equal([[:outer, :inner]], observed)

receiver = Object.new
receiver.define_singleton_method(:name) { :method }
result = receiver.instance_eval do
  before_assignment = name
  name = :local
  [before_assignment, name, self]
end
A.equal(:method, result[0])
A.equal(:local, result[1])
A.same(receiver, result[2])

A.done
