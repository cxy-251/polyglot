# polyglot-covers: julia.runtime.task-lifecycle-results-and-structured-waiting

using Test

@testset "Task 结果、状态与 @sync 的词法所有权相互配合" begin
    task = Task(() -> 21 * 2)
    @test !istaskstarted(task)
    schedule(task)
    @test fetch(task) == 42
    @test istaskstarted(task)
    @test istaskdone(task)
    @test !istaskfailed(task)
    results = Channel{Int}(2)
    @sync begin
        @async put!(results, 1)
        @async put!(results, 2)
    end
    close(results)
    @test sort(collect(results)) == [1, 2]
    @test !isopen(results)
end
