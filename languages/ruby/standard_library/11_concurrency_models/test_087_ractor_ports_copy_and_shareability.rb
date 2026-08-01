# frozen_string_literal: true
# polyglot-covers: ruby.concurrency.ractor-ports-copy-and-shareability

require "assertions"

A = PolyglotAssertions

A.case("Ractor::Port carries messages separately from the producer termination value") do
  port = Ractor::Port.new
  producer = Ractor.new(port) do |output|
    output << 42
    :finished
  end
  A.equal(42, port.receive)
  A.equal(:finished, producer.value)
end

A.case("sending an unshareable object copies it and leaves the sender's object usable") do
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
end

A.case("make_shareable recursively freezes a mutable object graph") do
  shareable = Ractor.make_shareable(["ruby"])
  A.truth(Ractor.shareable?(shareable))
  A.truth(shareable.frozen?)
  A.truth(shareable.first.frozen?)
end

A.done
