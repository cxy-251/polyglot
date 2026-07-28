# polyglot-covers: julia.runtime.events-and-explicit-wakeup

using Test

@testset "Event 把完成条件和唤醒事件分离" begin
    event = Base.Event()
    waiter = @async begin
        wait(event)
        return :released
    end
    notify(event)
    @test fetch(waiter) === :released
    @test istaskdone(waiter)
    later_waiter = @async (wait(event); :released_again)
    @test fetch(later_waiter) === :released_again
end
