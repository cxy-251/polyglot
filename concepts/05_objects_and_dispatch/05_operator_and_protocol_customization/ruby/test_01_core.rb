# 共同问题：用户类型可定制哪些运算符和语言协议。
# 输入：+、==、hash、each、to_s 和 call；观察：普通方法分派、Enumerable 组合及协议一致性。
# polyglot-family: objects_and_dispatch
# polyglot-concept: operator_and_protocol_customization
# polyglot-related: languages/ruby/language/04_classes_modules_and_lookup/test_026_singleton_class_methods_and_extend.rb

require "assertions"

A = PolyglotAssertions

value_class = Class.new do
  include Enumerable
  attr_reader :value

  def initialize(value) = @value = value
  def +(other) = self.class.new(value + other.value)
  def ==(other) = other.is_a?(self.class) && value == other.value
  def eql?(other) = self == other
  def hash = [self.class, value].hash
  def each = block_given? ? yield(value) : enum_for(__method__)
  def call(multiplier) = value * multiplier
  def to_s = "Value(#{value})"
end

left = value_class.new(2)
A.equal(value_class.new(5), left + value_class.new(3))
A.equal([4], left.map { _1 * 2 })
A.equal(6, left.call(3))
A.equal("Value(2)", left.to_s)
A.equal(1, {left => :present}.length)

A.done
