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

pointer = Fiddle::Pointer.malloc(4)
begin
  pointer[0, 4] = "ruby"
  A.equal("ruby", pointer[0, 4])
  A.truth(pointer.to_i.positive?)
ensure
  Fiddle.free(pointer.to_i)
end

A.truth(Fiddle::SIZEOF_VOIDP >= 4)
# Fiddle 不验证声明是否匹配真实 C ABI；错误签名、悬空指针和越界访问会越过 Ruby 安全边界，
# 因而课程只执行具有已知签名和明确所有权的调用。
A.done
