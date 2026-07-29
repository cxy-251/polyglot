# frozen_string_literal: true
# polyglot-covers: ruby.concurrency.queue-sized-queue-and-close

require "assertions"

A = PolyglotAssertions

queue = Queue.new
queue << 1 << 2
A.equal([1, 2], [queue.pop, queue.pop])
A.truth(queue.empty?)
A.raises(ThreadError) { queue.pop(true) }
queue.close
A.truth(queue.closed?)
A.nil_value(queue.pop)
A.raises(ClosedQueueError) { queue << 3 }

bounded = SizedQueue.new(1)
bounded << :first
A.raises(ThreadError) { bounded.push(:second, true) }
A.equal(:first, bounded.pop)
bounded.push(:second, true)
A.equal(:second, bounded.pop)
A.equal(1, bounded.max)

A.done
