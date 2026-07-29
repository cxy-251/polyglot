# frozen_string_literal: true
# polyglot-covers: ruby.c-extension.blocks-and-callbacks-across-c

require "assertions"
require "polyglot_native"

A = PolyglotAssertions

observed = []
result = PolyglotNative.yield_twice(21) do |value|
  observed << value
  value * observed.length
end
A.equal([21, 21], observed)
A.equal(42, result)
A.raises(ArgumentError, "block required") { PolyglotNative.yield_twice(1) }

receiver = Object.new
receiver.define_singleton_method(:answer) { 42 }
A.equal(42, PolyglotNative.call_ruby(receiver, :answer))
A.raises(NoMethodError) { PolyglotNative.call_ruby(receiver, :missing) }

error = A.raises(ArgumentError, "native failure") do
  PolyglotNative.fail!("native failure")
end
A.equal("native failure", error.message)
A.raises(TypeError) { PolyglotNative.fail!(:not_a_string) }

# rb_yield、rb_funcall 与 rb_raise 都重新进入 Ruby 控制流；C 帧不能吞掉 block 失败或异常。
A.done
