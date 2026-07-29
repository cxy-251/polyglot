# frozen_string_literal: true
# polyglot-covers: ruby.concurrency.fiber-resume-yield-and-transfer

require "assertions"

A = PolyglotAssertions

fiber = Fiber.new do |first|
  second = Fiber.yield(first * 2)
  second + 1
end

A.truth(fiber.alive?)
A.equal(6, fiber.resume(3))
A.truth(fiber.alive?)
A.equal(11, fiber.resume(10))
A.falsey(fiber.alive?)
A.raises(FiberError) { fiber.resume }

enumerator = [1, 2].each
A.equal(1, enumerator.next)
A.equal(2, enumerator.next)
A.raises(StopIteration) { enumerator.next }

A.done
