# 共同问题：惰性生产者何时执行，消费者提前停止后哪些值未被生产。
# 输入：Enumerator::Lazy、副作用 map、take 和无限 Range；观察：按需执行、状态保留及早停。
# polyglot-family: collections_and_iteration
# polyglot-concept: generators_laziness_and_early_termination
# polyglot-related: languages/ruby/language/06_collections_and_enumeration/test_047_lazy_and_infinite_enumeration.rb

require "assertions"

A = PolyglotAssertions

produced = []
lazy = (1..).lazy.map do |value|
  produced << value
  value * 2
end
A.equal([], produced)
A.equal([2, 4, 6], lazy.take(3).force)
A.equal([1, 2, 3], produced)

iterator = [10, 20].each
A.equal(10, iterator.next)
A.equal(20, iterator.next)
A.raises(StopIteration) { iterator.next }

A.done
