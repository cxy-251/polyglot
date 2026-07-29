# frozen_string_literal: true
# polyglot-covers: ruby.values.freeze-dup-clone-and-object-identity

require "assertions"

A = PolyglotAssertions

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
A.equal(original.object_id, original.__id__)

A.done
