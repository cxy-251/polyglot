# polyglot-covers: julia.runtime.task-failure-and-composite-exception

using Test

@testset "失败 Task 由 fetch/wait 传播，@sync 聚合多个子任务失败" begin
    failed = @async error("single")
    @test_throws TaskFailedException fetch(failed)
    @test istaskfailed(failed)
    aggregate = try
        @sync begin
            @async error("first")
            @async error("second")
        end
        nothing
    catch error
        error
    end
    @test aggregate isa CompositeException
    @test length(aggregate.exceptions) == 2
end
