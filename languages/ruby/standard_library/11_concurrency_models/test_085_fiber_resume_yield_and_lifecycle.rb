# frozen_string_literal: true
# polyglot-covers: ruby.concurrency.fiber-resume-yield-and-transfer

require "assertions"

A = PolyglotAssertions

A.case("resume and yield exchange values across the Fiber lifecycle") do
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
end

A.case("a Fiber is cooperative and remains dormant until explicitly resumed") do
  events = []
  dormant = Fiber.new { events << :ran }
  A.equal([], events)
  dormant.resume
  A.equal([:ran], events)
end

A.done
