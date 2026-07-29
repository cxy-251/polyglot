# 共同问题：隔离 worker 怎样传递结果、所有权和失败。
# 输入：Ractor copy、move、shareable object 和远端异常；观察：身份边界、MovedError 及 RemoteError cause。
# polyglot-family: async_and_concurrency
# polyglot-concept: threads_workers_and_process_isolation
# polyglot-related: languages/ruby/standard_library/11_concurrency_models/
# polyglot-related+: test_088_ractor_move_and_remote_failure.rb

require "assertions"

A = PolyglotAssertions

shareable = Ractor.make_shareable(["ruby"])
A.truth(Ractor.shareable?(shareable))
A.truth(shareable.frozen?)

moved = +"owned"
worker = Ractor.new { Ractor.receive << "-worker" }
worker.send(moved, move: true)
A.equal("owned-worker", worker.value)
A.raises(Ractor::MovedError) { moved.length }

failing = Ractor.new do
  Thread.current.report_on_exception = false
  raise ArgumentError, "remote"
end
remote = A.raises(Ractor::RemoteError) { failing.value }
A.same(ArgumentError, remote.cause.class)
A.equal("remote", remote.cause.message)

A.done
