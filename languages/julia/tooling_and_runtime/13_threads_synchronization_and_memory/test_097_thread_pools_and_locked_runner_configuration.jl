# polyglot-covers: julia.runtime.thread-pools-and-runner-configuration

using Test
using Base.Threads

@testset "运行器固定 default thread pool，不依赖 Julia 1.12 默认池推断" begin
    @test nthreads(:default) == 2
    @test nthreads(:interactive) == 0
    @test threadpool() === :default
    @test 1 <= threadid() <= Threads.maxthreadid()
end
