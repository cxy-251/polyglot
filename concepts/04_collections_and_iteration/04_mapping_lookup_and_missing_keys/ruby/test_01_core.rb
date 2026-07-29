# 共同问题：映射查找怎样区分缺失、默认值、false 值和插入。
# 输入：Hash#[]、fetch、key?、default_proc 和 delete；观察：非插入 fallback、严格查找及状态变化。
# polyglot-family: collections_and_iteration
# polyglot-concept: mapping_lookup_and_missing_keys
# polyglot-related: languages/ruby/language/06_collections_and_enumeration/test_042_hash_defaults_and_missing_keys.rb

require "assertions"

A = PolyglotAssertions

mapping = Hash.new { |_hash, key| "missing:#{key}" }
mapping[:false_value] = false
A.falsey(mapping[:false_value])
A.truth(mapping.key?(:false_value))
A.equal("missing:unknown", mapping[:unknown])
A.falsey(mapping.key?(:unknown))
A.equal(:fallback, mapping.fetch(:unknown, :fallback))
A.raises(KeyError) { mapping.fetch(:unknown) }
A.falsey(mapping.delete(:false_value))
A.falsey(mapping.key?(:false_value))

A.done
