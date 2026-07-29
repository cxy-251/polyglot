# 共同问题：执行单元是共享内存 thread、隔离 worker 还是协作 coroutine。
# 输入：Thread、Fiber、Ractor 和可变对象；观察：Thread 共享、Fiber 协作、Ractor copy/isolation。
# polyglot-family: async_and_concurrency
# polyglot-concept: threads_workers_and_process_isolation
# polyglot-related: languages/ruby/standard_library/11_concurrency_models/test_087_ractor_ports_copy_and_shareability.rb

require "assertions"

A = PolyglotAssertions

shared = []
thread = Thread.new { shared << :thread }
thread.join
A.equal([:thread], shared)

fiber = Fiber.new { Fiber.yield(:paused); :done }
A.equal(:paused, fiber.resume)
A.equal(:done, fiber.resume)

original = +"ruby"
worker = Ractor.new { value = Ractor.receive; value << "-ractor" }
worker.send(original)
A.equal("ruby-ractor", worker.value)
A.equal("ruby", original)

A.done
