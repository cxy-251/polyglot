# 共同问题：继承查找、override 动态分派和 super 怎样工作。
# 输入：基类、子类 override、模块 prepend 和 super；观察：receiver 保留、祖先顺序及下一方法查找。
# polyglot-family: objects_and_dispatch
# polyglot-concept: inheritance_dynamic_dispatch_and_super
# polyglot-related: languages/ruby/language/04_classes_modules_and_lookup/
# polyglot-related+: test_025_construction_inheritance_and_super.rb

require "assertions"

A = PolyglotAssertions

base = Class.new do
  def describe(value) = "base:#{value}"
end
child = Class.new(base) do
  def describe(value) = "child(#{super})"
end
decorator = Module.new do
  def describe(value) = "decorated(#{super})"
end
child.prepend(decorator)

object = child.new
A.equal("decorated(child(base:ruby))", object.describe("ruby"))
A.truth(object.is_a?(base))
A.equal([decorator, child, base], child.ancestors.take(3))

A.done
