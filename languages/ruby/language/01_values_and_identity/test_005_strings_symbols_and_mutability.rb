# frozen_string_literal: true
# polyglot-covers: ruby.values.strings-symbols-and-mutability

require "assertions"

A = PolyglotAssertions

mutable = String.new("ruby")
same = mutable
mutable << "!"
A.equal("ruby!", same)
A.truth(:ruby.equal?(:ruby))
A.equal("ruby", :ruby.to_s)
A.equal(:ruby, "ruby".to_sym)
A.falsey(mutable.frozen?)
mutable.freeze
A.truth(mutable.frozen?)
A.raises(FrozenError) { mutable << "?" }

A.done
