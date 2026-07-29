# 共同问题：可调用对象怎样适配为 block、固定部分参数或改变 arity。
# 输入：Method、Proc、lambda、curry 和 symbol-to-proc；观察：适配后的调用、严格度与结果。
# polyglot-family: functions_and_calls
# polyglot-concept: callable_adaptation_and_partial_application
# polyglot-related: languages/ruby/language/03_methods_blocks_and_procs/
# polyglot-related+: test_024_method_binding_callable_objects_and_currying.rb

require "assertions"

A = PolyglotAssertions

add = ->(left, right) { left + right }
add_ten = add.curry.call(10)
A.equal(15, add_ten.call(5))
A.equal([2, 4, 6], [1, 2, 3].map(&2.method(:*)))
A.equal(["RUBY", "LANGUAGE"], %w[ruby language].map(&:upcase))

loose = proc { |left, right| [left, right] }
strict = ->(left, right) { [left, right] }
A.equal([1, nil], loose.call(1))
A.raises(ArgumentError) { strict.call(1) }

A.done
