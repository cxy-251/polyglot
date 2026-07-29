# 共同问题：存储字段、计算属性和缺失成员怎样解析。
# 输入：实例变量、reader/writer、继承方法和 method_missing；观察：方法查找、setter 调用及反射一致性。
# polyglot-family: objects_and_dispatch
# polyglot-concept: member_attribute_lookup_and_properties
# polyglot-related: languages/ruby/language/04_classes_modules_and_lookup/
# polyglot-related+: test_030_method_missing_and_respond_to_missing.rb

require "assertions"

A = PolyglotAssertions

model_class = Class.new do
  attr_reader :value

  def initialize(value) = @value = value

  def value=(value)
    @value = Integer(value)
  end

  def method_missing(name, ...)
    return @value * 2 if name == :double

    super
  end

  def respond_to_missing?(name, include_private = false)
    name == :double || super
  end
end

model = model_class.new(3)
A.equal(3, model.value)
model.value = "4"
A.equal(4, model.value)
A.equal(8, model.double)
A.truth(model.respond_to?(:double))
A.raises(NoMethodError) { model.missing }

A.done
