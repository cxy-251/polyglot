# 共同问题：自定义 iterable、外部 iterator 状态和协议 fallback 怎样表示。
# 输入：只实现 each 的对象、Enumerator 和无 each 对象；观察：Enumerable mixin、next 状态及错误边界。
# polyglot-family: collections_and_iteration
# polyglot-concept: iteration_protocol
# polyglot-related: languages/ruby/language/06_collections_and_enumeration/
# polyglot-related+: test_045_each_enumerable_and_external_enumerators.rb

require "assertions"

A = PolyglotAssertions

sequence_class = Class.new do
  include Enumerable

  def each
    return enum_for(__method__) unless block_given?

    yield 1
    yield 2
  end
end

sequence = sequence_class.new
A.equal([2, 4], sequence.map { _1 * 2 })
iterator = sequence.each
A.same(Enumerator, iterator.class)
A.equal(1, iterator.next)
A.equal(2, iterator.next)
A.raises(StopIteration) { iterator.next }
A.raises(NoMethodError) { Object.new.each { nil } }

A.done
