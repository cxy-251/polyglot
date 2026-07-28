# polyglot-covers: julia.runtime.cooperative-cancellation-protocol

using Test

@testset "Task 没有通用强制取消协议，协作任务显式接收停止信号" begin
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
