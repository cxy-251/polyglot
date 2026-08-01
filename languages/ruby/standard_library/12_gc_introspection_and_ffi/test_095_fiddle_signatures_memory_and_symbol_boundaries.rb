# frozen_string_literal: true
# polyglot-covers: ruby.ffi.fiddle-dynamic-library-boundary

require "assertions"
require "fiddle"

A = PolyglotAssertions

A.case("Fiddle::Function calls known C symbols through explicit signatures") do
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
end

A.case("dynamic symbol lookup reports a missing symbol before any call") do
  A.raises(Fiddle::DLError) { Fiddle::Handle::DEFAULT["polyglot_missing_symbol"] }
end

A.case("explicitly allocated native memory remains valid only until its matching free") do
  pointer = Fiddle::Pointer.malloc(4)
  begin
    pointer[0, 4] = "ruby"
    A.equal("ruby", pointer[0, 4])
    A.truth(pointer.to_i.positive?)
  ensure
    Fiddle.free(pointer.to_i)
  end
end

A.case("the runtime exposes pointer width but cannot validate a caller-supplied C signature") do
  A.truth(Fiddle::SIZEOF_VOIDP >= 4)
end
A.done
