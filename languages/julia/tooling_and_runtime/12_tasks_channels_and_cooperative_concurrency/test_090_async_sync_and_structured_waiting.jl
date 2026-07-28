# polyglot-covers: julia.runtime.async-sync-and-structured-waiting

using Test

@testset "@sync 等待词法范围内注册的 @async 子任务" begin
    results = Channel{Int}(2)
    @sync begin
        @async put!(results, 1)
        @async put!(results, 2)
    end
    close(results)
    @test sort(collect(results)) == [1, 2]
    @test !isopen(results)
end
