# frozen_string_literal: true
# polyglot-covers: ruby.ffi.fiddle-dynamic-library-boundary

require "assertions"
require "fiddle"

A = PolyglotAssertions

handle = Fiddle::Handle::DEFAULT
abs = Fiddle::Function.new(
  handle["abs"],
  [Fiddle::TYPE_INT],
  Fiddle::TYPE_INT
)
strlen = Fiddle::Function.new(
  handle["strlen"],
  [Fiddle::TYPE_VOIDP],
  Fiddle::TYPE_SIZE_T
)

A.equal(7, abs.call(-7))
A.equal(4, strlen.call("ruby"))
A.raises(Fiddle::DLError) { handle["polyglot_missing_symbol"] }
A.truth(Fiddle::SIZEOF_VOIDP >= 4)

A.done
