# 共同问题：用户类型可定制哪些运算符和语言协议。
# 输入：+、==、eql? 和 hash；观察：运算符的方法分派及 Hash 协议一致性。
# polyglot-family: objects_and_dispatch
# polyglot-concept: operator_and_protocol_customization
# polyglot-related: languages/ruby/language/01_values_and_identity/test_004_numeric_models_conversion_and_coercion.rb
# polyglot-related: languages/ruby/language/01_values_and_identity/test_003_equality_identity_and_hash_keys.rb

require "assertions"
require "set"

A = PolyglotAssertions

value_class = Class.new do
  attr_reader :value

  def initialize(value) = @value = value
  def +(other) = self.class.new(value + other.value)
  def ==(other) = other.is_a?(self.class) && value == other.value
  def eql?(other) = self == other
  def hash = [self.class, value].hash
end

left = value_class.new(2)
A.equal(value_class.new(5), left + value_class.new(3))
A.equal(:present, {left => :present}[value_class.new(2)])
A.equal(1, Set.new([left, value_class.new(2)]).length)

A.done
