# frozen_string_literal: true
# polyglot-covers: ruby.values.strings-symbols-and-mutability

require "assertions"

A = PolyglotAssertions

mutable = String.new("ruby")
alias_to_mutable = mutable
mutable << "!"
A.equal("ruby!", alias_to_mutable)
A.truth(:ruby.equal?(:ruby))
A.equal("ruby", :ruby.to_s)
A.equal(:ruby, "ruby".to_sym)

original = ["nested"].freeze
duplicate = original.dup
clone = original.clone
A.falsey(duplicate.equal?(original))
A.falsey(duplicate.frozen?)
A.truth(clone.frozen?)
# dup 与 clone 都是浅复制；嵌套字符串仍然共享。
A.same(original.first, duplicate.first)
A.same(original.first, clone.first)
duplicate << "new"
A.equal(2, duplicate.length)
A.raises(FrozenError) { clone << "new" }

mutable.freeze
A.truth(mutable.frozen?)
A.raises(FrozenError) { mutable << "?" }
A.equal(original.object_id, original.__id__)

A.done
