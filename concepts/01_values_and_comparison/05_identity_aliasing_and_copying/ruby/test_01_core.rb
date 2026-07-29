# 共同问题：赋值何时共享对象，浅复制和冻结在哪一层生效。
# 输入：数组、嵌套字符串、alias、dup 和 clone；观察：object_id、突变可见性、共享子对象和冻结状态。
# polyglot-family: values_and_comparison
# polyglot-concept: identity_aliasing_and_copying
# polyglot-related: languages/ruby/language/01_values_and_identity/test_005_mutability_symbols_freeze_and_copying.rb

require "assertions"

A = PolyglotAssertions

original = [+"nested"]
alias_value = original
copy = original.dup
alias_value << "shared"
A.equal(2, original.length)
A.equal(1, copy.length)
A.same(original, alias_value)
A.falsey(original.equal?(copy))
A.same(original.first, copy.first)
copy.first << "-changed"
A.equal("nested-changed", original.first)

frozen = original.freeze
A.truth(frozen.clone.frozen?)
A.falsey(frozen.dup.frozen?)

A.done
