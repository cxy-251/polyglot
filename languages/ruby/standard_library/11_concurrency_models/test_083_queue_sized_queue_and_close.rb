# frozen_string_literal: true
# polyglot-covers: ruby.concurrency.queue-sized-queue-and-close

require "assertions"

A = PolyglotAssertions

queue = Queue.new
queue << 1 << 2
A.equal(2, queue.size)
A.equal(1, queue.pop)
A.equal(2, queue.pop)
A.truth(queue.empty?)
queue.close
A.truth(queue.closed?)
A.nil_value(queue.pop)
A.raises(ClosedQueueError) { queue << 3 }

bounded = SizedQueue.new(1)
bounded << :value
A.equal(1, bounded.length)
A.equal(:value, bounded.pop)
A.equal(1, bounded.max)

A.done
