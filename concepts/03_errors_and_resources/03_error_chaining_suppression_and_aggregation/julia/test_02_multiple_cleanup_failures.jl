# polyglot-family: errors_and_resources
# polyglot-concept: error_chaining_suppression_and_aggregation
# polyglot-related: languages/julia/tooling_and_runtime/12_tasks_channels_and_cooperative_concurrency/
# polyglot-related+: test_093_task_failure_and_composite_exception.jl
#
# 共同问题：并发或多个 cleanup 同时失败时是否丢失错误。
# 对照观察：@sync 等待其词法子任务，并以 CompositeException 聚合多个 TaskFailedException。

using Test

@testset "结构化并发聚合多个失败" begin
    exception = try
        @sync begin
            @async error("first")
            @async throw(ArgumentError("second"))
        end
        nothing
    catch caught
        caught
    end
    @test exception isa CompositeException
    @test length(exception.exceptions) == 2
    @test all(item -> item isa TaskFailedException, exception.exceptions)
end
