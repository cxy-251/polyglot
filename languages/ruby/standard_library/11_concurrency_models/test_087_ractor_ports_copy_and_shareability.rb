# frozen_string_literal: true
# polyglot-covers: ruby.concurrency.ractor-ports-copy-and-shareability

require "assertions"

A = PolyglotAssertions

port = Ractor::Port.new
producer = Ractor.new(port) do |output|
  output << 42
  :finished
end
A.equal(42, port.receive)
A.equal(:finished, producer.value)

original = +"mutable"
copy_worker = Ractor.new do
  received = Ractor.receive
  [received, received.object_id]
end
copy_worker.send(original)
copied_value, copied_id = copy_worker.value
A.equal("mutable", copied_value)
A.falsey(original.object_id == copied_id)
A.equal("mutable", original)

shareable = Ractor.make_shareable(["ruby"])
A.truth(Ractor.shareable?(shareable))
A.truth(shareable.frozen?)
A.truth(shareable.first.frozen?)

A.done
