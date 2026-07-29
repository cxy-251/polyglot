# polyglot-covers: julia.runtime.events-and-cooperative-cancellation

using Test

@testset "Event 发布完成；停止协议需要任务主动确认 cleanup" begin
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
    stop = Channel{Nothing}(1)
    events = Channel{Symbol}(1)
    worker = @async begin
        take!(stop)
        put!(events, :cleaned)
        return :stopped
    end
    put!(stop, nothing)
    @test fetch(worker) === :stopped
    @test take!(events) === :cleaned
    close(stop)
    close(events)
end
