# 共同问题：哪些值可作条件，哪些值为假。
# 输入：nil、false、零、空字符串和空集合；观察：分支选择、短路表达式返回值和不可重载的真值规则。
# polyglot-family: values_and_comparison
# polyglot-concept: truthiness
# polyglot-related: languages/ruby/language/01_values_and_identity/test_002_truthiness_and_nil.rb

require "assertions"

A = PolyglotAssertions

[0, "", [], {}].each { |value| A.equal(:taken, value ? :taken : :skipped) }
A.equal(:skipped, nil ? :taken : :skipped)
A.equal(:skipped, false ? :taken : :skipped)
A.equal("fallback", nil || "fallback")
A.equal(0, 0 && 0)

object = Object.new
object.define_singleton_method(:!) { true }
A.truth(object)
A.truth(!object)

A.done
