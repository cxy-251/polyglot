# 共同问题：运行期怎样查询类型、祖先、成员和对象状态。
# 输入：class、is_a?、ancestors、methods、instance_variables 和 respond_to?；观察：开放式反射与可见性。
# polyglot-family: objects_and_dispatch
# polyglot-concept: introspection_reflection_and_runtime_type
# polyglot-related: languages/ruby/language/05_metaprogramming_and_refinements/
# polyglot-related+: test_039_tracepoint_and_cruby_observation.rb

require "assertions"

A = PolyglotAssertions

module_value = Module.new
klass = Class.new do
  attr_reader :value
  def initialize = @value = 42
end
klass.include(module_value)
object = klass.new

A.same(klass, object.class)
A.truth(object.is_a?(klass))
A.truth(object.is_a?(module_value))
A.includes(klass.ancestors, module_value)
A.includes(object.methods, :value)
A.equal([:@value], object.instance_variables)
A.truth(object.respond_to?(:value))
A.falsey(object.respond_to?(:missing))

A.done
