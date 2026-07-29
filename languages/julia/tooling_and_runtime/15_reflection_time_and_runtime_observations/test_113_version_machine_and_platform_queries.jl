# polyglot-covers: julia.runtime.structured-capability-and-platform-queries

using Test

@testset "运行时能力使用结构化查询，不从版本字符串或路径猜测" begin
    @test VERSION isa VersionNumber
    @test Sys.WORD_SIZE in (32, 64)
    @test Sys.ARCH isa Symbol
    @test Sys.KERNEL isa Symbol
    @test Sys.CPU_THREADS >= 1
    @test count(identity, (Sys.isunix(), Sys.iswindows())) == 1
    @test isdefined(Base, :ScopedValues)
    @test hasmethod(Base.invokelatest, Tuple{Any})
    @test Base.find_package("Sockets") !== nothing
    @test Threads.nthreads(:default) >= 1
end
