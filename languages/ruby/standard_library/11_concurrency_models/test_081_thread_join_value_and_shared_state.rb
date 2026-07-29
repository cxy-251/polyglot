# frozen_string_literal: true
# polyglot-covers: ruby.concurrency.thread-join-value-and-shared-state

require "assertions"

A = PolyglotAssertions

shared = []
commands = Queue.new
worker = Thread.new do
  value = commands.pop
  shared << value
  value * 2
end

commands << 21
A.equal(42, worker.value)
A.equal([21], shared)
A.falsey(worker.alive?)
A.same(Thread.current.group, worker.group)
A.falsey(worker == Thread.current)

A.done
