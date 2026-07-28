# polyglot-covers: julia.runtime.task-schedule-fetch-and-states

using Test

@testset "Task 显式经历 schedule、完成和结果获取" begin
    task = Task(() -> 21 * 2)
    @test !istaskstarted(task)
    schedule(task)
    @test fetch(task) == 42
    @test istaskstarted(task)
    @test istaskdone(task)
    @test !istaskfailed(task)
end
