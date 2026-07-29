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

# Ractor 失败通过 RemoteError 在收集点传播；它不是 OS 子进程，fork 工作流另见进程课程。
A.done
