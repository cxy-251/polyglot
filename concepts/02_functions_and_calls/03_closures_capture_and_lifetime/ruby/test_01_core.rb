# 共同问题：闭包捕获什么，捕获状态存活多久，多个闭包是否共享同一绑定。
# 输入：可变局部、同工厂的 sibling closure 和独立工厂；观察：按绑定捕获、生命周期及工厂隔离。
# polyglot-family: functions_and_calls
# polyglot-concept: closures_capture_and_lifetime
# polyglot-related: languages/ruby/language/02_scope_and_constants/test_012_closure_capture_and_lifetime.rb

require "assertions"

A = PolyglotAssertions

def counter_pair
  count = 0
  increment = -> { count += 1 }
  read = -> { count }
  [increment, read]
end

increment, read = counter_pair
other_increment, other_read = counter_pair
A.equal(1, increment.call)
A.equal(1, read.call)
A.equal(2, increment.call)
A.equal(0, other_read.call)
A.equal(1, other_increment.call)
A.equal(2, read.call)

A.done
