# frozen_string_literal: true
# polyglot-covers: ruby.concurrency.ractor-move-remote-error-and-process-isolation

require "assertions"

A = PolyglotAssertions

A.case("move transfers ownership and makes the sender-side object inaccessible") do
  moved = +"owned"
  move_worker = Ractor.new do
    value = Ractor.receive
    value << "-worker"
  end
  move_worker.send(moved, move: true)
  A.equal("owned-worker", move_worker.value)
  A.raises(Ractor::MovedError) { moved.length }
end

A.case("a failing Ractor reports RemoteError at collection with the remote cause") do
  failing = Ractor.new do
    Thread.current.report_on_exception = false
    raise ArgumentError, "remote"
  end
  remote = A.raises(Ractor::RemoteError) { failing.value }
  A.same(ArgumentError, remote.cause.class)
  A.equal("remote", remote.cause.message)
end
A.done
