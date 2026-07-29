# frozen_string_literal: true
# polyglot-covers: ruby.calls.anonymous-argument-forwarding

require "assertions"

A = PolyglotAssertions

def forwarding_target(first, *rest, enabled:, **extra)
  block_value = block_given? ? yield(first) : nil
  [first, rest, enabled, extra, block_value]
end

def forwarding_relay(...)
  forwarding_target(...)
end

result = forwarding_relay(2, 3, enabled: true, note: :kept) { |value| value * 10 }
A.equal([2, [3], true, {note: :kept}, 20], result)
A.raises(ArgumentError) { forwarding_relay(1) }
A.equal([[:rest, :*], [:keyrest, :**], [:block, :&]], method(:forwarding_relay).parameters)

A.done
