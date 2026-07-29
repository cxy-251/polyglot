# 共同问题：空值、缺失键、显式 false 和可选结果怎样区分。
# 输入：nil、false、存在键和缺失键；观察：nil?、fetch、key?、默认值及删除语义。
# polyglot-family: values_and_comparison
# polyglot-concept: null_missing_and_optional_values
# polyglot-related: languages/ruby/language/01_values_and_identity/test_002_truthiness_and_nil.rb

require "assertions"

A = PolyglotAssertions

mapping = {present_nil: nil, present_false: false}
A.truth(mapping.key?(:present_nil))
A.nil_value(mapping[:present_nil])
A.truth(mapping.key?(:present_false))
A.falsey(mapping[:present_false])
A.falsey(mapping.key?(:missing))
A.nil_value(mapping[:missing])
A.equal(:fallback, mapping.fetch(:missing, :fallback))
A.raises(KeyError) { mapping.fetch(:missing) }
A.nil_value(mapping.delete(:present_nil))
A.falsey(mapping.key?(:present_nil))

A.done
