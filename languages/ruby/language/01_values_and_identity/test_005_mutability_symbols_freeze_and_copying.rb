# frozen_string_literal: true
# polyglot-covers: ruby.values.strings-symbols-and-mutability

require "assertions"

A = PolyglotAssertions

A.case("assignment aliases mutable objects while symbols represent interned names") do
  mutable = String.new("ruby")
  alias_to_mutable = mutable
  mutable << "!"

  A.equal("ruby!", alias_to_mutable)
  A.truth(:ruby.equal?(:ruby))
  A.equal("ruby", :ruby.to_s)
  A.equal(:ruby, "ruby".to_sym)
end

A.case("dup and clone are shallow copies with different frozen-state handling") do
  original = ["nested"].freeze
  duplicate = original.dup
  clone = original.clone

  A.falsey(duplicate.equal?(original))
  A.falsey(duplicate.frozen?)
  A.truth(clone.frozen?)
  A.same(original.first, duplicate.first)
  A.same(original.first, clone.first)
  duplicate << "new"
  A.equal(2, duplicate.length)
  A.raises(FrozenError) { clone << "new" }
end

A.case("freeze prevents later mutation without changing object identity") do
  mutable = String.new("ruby")
  identity = mutable.object_id
  mutable.freeze

  A.truth(mutable.frozen?)
  A.raises(FrozenError) { mutable << "?" }
  A.equal(identity, mutable.__id__)
end

A.done
