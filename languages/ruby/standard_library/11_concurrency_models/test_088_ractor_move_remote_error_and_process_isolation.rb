# frozen_string_literal: true
# polyglot-covers: ruby.concurrency.ractor-move-remote-error-and-process-isolation

require "assertions"

A = PolyglotAssertions

moved = +"owned"
move_worker = Ractor.new do
  value = Ractor.receive
  value << "-worker"
end
move_worker.send(moved, move: true)
A.equal("owned-worker", move_worker.value)
A.raises(Ractor::MovedError) { moved.length }

failing = Ractor.new do
  Thread.current.report_on_exception = false
  raise ArgumentError, "remote"
end
remote = A.raises(Ractor::RemoteError) { failing.value }
A.same(ArgumentError, remote.cause.class)
A.equal("remote", remote.cause.message)

reader, writer = IO.pipe
pid = fork do
  reader.close
  writer.write(Process.pid.to_s)
  writer.close
  exit! 0
end
writer.close
child_pid = Integer(reader.read)
reader.close
_waited, status = Process.wait2(pid)
A.equal(pid, child_pid)
A.falsey(child_pid == Process.pid)
A.truth(status.success?)

A.done
