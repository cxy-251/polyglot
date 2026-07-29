# polyglot-covers: julia.runtime.timers-and-predicate-timeouts

using Test

@testset "Timer 和 timedwait 等待事件或 predicate 而不是猜测调度" begin
    timer = Timer(0)
    try
        wait(timer)
        @test true
    finally
        close(timer)
    end
    @test timedwait(() -> true, 0.1) === :ok
    @test timedwait(() -> false, 0.0) === :timed_out
    completed = @async :done
    @test fetch(completed) === :done
    @test istaskdone(completed)
    # timedwait 只报告 predicate 状态，不取得被观察任务的所有权，也不隐式取消任务。
end
