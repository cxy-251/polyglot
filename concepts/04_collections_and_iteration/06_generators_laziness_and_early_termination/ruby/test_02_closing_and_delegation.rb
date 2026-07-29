# 共同问题：提前停止时谁拥有生产者清理，嵌套迭代怎样委托。
# 输入：带 ensure 的 each、break、外部 Enumerator 和 flat_map；观察：栈内清理确定性及外部状态边界。
# polyglot-family: collections_and_iteration
# polyglot-concept: generators_laziness_and_early_termination
# polyglot-related: languages/ruby/language/06_collections_and_enumeration/
# polyglot-related+: test_045_each_enumerable_and_external_enumerators.rb

require "assertions"

A = PolyglotAssertions

trace = []
iterable = Object.new
iterable.define_singleton_method(:each) do |&consumer|
  return enum_for(__method__) unless consumer

  begin
    consumer.call(1)
    consumer.call(2)
  ensure
    trace << :closed
  end
end

A.equal(1, iterable.each { |value| break value })
A.equal([:closed], trace)

trace.clear
external = iterable.each
A.falsey(external.respond_to?(:close))
A.equal(1, external.next)
A.equal(2, external.next)
A.raises(StopIteration) { external.next }
A.equal([:closed], trace)

delegated = [[1, 2], [3]].lazy.flat_map(&:itself)
A.equal([1, 2, 3], delegated.force)

A.done
