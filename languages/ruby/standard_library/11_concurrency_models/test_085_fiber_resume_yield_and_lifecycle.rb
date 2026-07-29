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

# Fiber 是协作式控制流：只有 resume/transfer 或 scheduler hook 才推进执行。
events = []
dormant = Fiber.new { events << :ran }
A.equal([], events)
dormant.resume
A.equal([:ran], events)

A.done
