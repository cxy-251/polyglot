# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.timeout-monitor-and-delegation

require "assertions"
require "timeout"

A = PolyglotAssertions

A.equal(:done, Timeout.timeout(nil) { :done })

events = []
error = A.raises(Timeout::Error) do
  Timeout.timeout(0.02) do
    begin
      events << :entered
      Queue.new.pop
    ensure
      events << :cleanup
    end
  end
end
A.equal(%i[entered cleanup], events)
A.truth(error.is_a?(Timeout::Error))

custom_timeout = Class.new(StandardError)
A.raises(custom_timeout) { Timeout.timeout(0.02, custom_timeout) { Queue.new.pop } }

# Timeout 以异步异常中断 block；不能把它当作底层操作已取消或外部资源已回收的证明。
A.done
