# frozen_string_literal: true
# polyglot-covers: ruby.metaprogramming.send-public-send-and-visibility

require "assertions"

A = PolyglotAssertions

receiver = Class.new do
  def public_value(value)
    value * 2
  end

  private

  def secret
    :secret
  end
end.new

A.equal(6, receiver.public_send(:public_value, 3))
A.equal(:secret, receiver.send(:secret))
A.raises(NoMethodError) { receiver.public_send(:secret) }
A.truth(receiver.respond_to?(:public_value))
A.falsey(receiver.respond_to?(:secret))
A.truth(receiver.respond_to?(:secret, true))

A.done
