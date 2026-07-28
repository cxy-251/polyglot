# polyglot-covers: julia.runtime.capability-detection-over-version-parsing

using Test

@testset "能力检测优先查询 binding、method 和平台 predicate" begin
    @test isdefined(Base, :ScopedValues)
    @test hasmethod(Base.invokelatest, Tuple{Any})
    @test Base.find_package("Sockets") !== nothing
    @test Sys.isunix()
    @test Threads.nthreads(:default) >= 1
end
