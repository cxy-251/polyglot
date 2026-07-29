# frozen_string_literal: true
# polyglot-covers: ruby.calls.positional-default-and-rest-arguments

require "assertions"

A = PolyglotAssertions

def collect_arguments(first, second = 2, *rest, required:, optional: 4, **extra, &block)
  block_value = block&.call(first)
  [first, second, rest, required, optional, extra, block_value]
end

A.equal([1, 2, [], 3, 4, {}, nil], collect_arguments(1, required: 3))
A.equal(
  [1, 5, [6], 3, 7, {flag: true}, 10],
  collect_arguments(1, 5, 6, required: 3, optional: 7, flag: true) { |value| value * 10 }
)
A.raises(ArgumentError) { collect_arguments(1) }
# Ruby 3+ 不再把位置 Hash 自动转换为关键字参数。
A.raises(ArgumentError) { collect_arguments(1, {required: 3}) }

positional = [1, 5, 6]
keywords = {required: 3, optional: 7}
A.equal([1, 5, [6], 3, 7, {}, nil], collect_arguments(*positional, **keywords))

convertible = Object.new
def convertible.to_a = [2, 3]
A.equal([1, 2, 3, 4], [1, *convertible, 4])
A.equal([], [*nil])
plain_object = Object.new
A.equal([plain_object], [*plain_object])
# 没有 to_a 的对象被当作单个元素；声明了协议却返回非 Array 才是协议错误。
A.equal(plain_object, collect_arguments(*plain_object, required: 3).first)
malformed = Object.new
def malformed.to_a = :not_an_array
A.raises(TypeError) { [*malformed] }

def forwarding_relay(...)
  collect_arguments(...)
end
A.equal(
  [1, 2, [], 3, 4, {}, 2],
  forwarding_relay(1, required: 3) { |value| value * 2 }
)
A.equal([[:rest, :*], [:keyrest, :**], [:block, :&]], method(:forwarding_relay).parameters)

A.done
