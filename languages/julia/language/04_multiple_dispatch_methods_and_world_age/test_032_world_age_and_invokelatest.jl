# polyglot-covers: julia.language.world-age-and-invokelatest

using Test

module WorldAgeExample
function define_fresh()
    @eval fresh() = 42
    try
        return fresh()
    catch error
        return error
    end
end
end

@testset "动态新方法受 world age 限制并由 invokelatest 调用" begin
    direct_result = WorldAgeExample.define_fresh()
    # Julia 1.12 将 global binding table 也纳入 world age；旧世界尚看不到 fresh binding。
    @test direct_result isa UndefVarError
    fresh = Base.invokelatest(getglobal, WorldAgeExample, :fresh)
    @test Base.invokelatest(fresh) == 42
    @test WorldAgeExample.fresh() == 42
    # world counter 的具体表示属于实现观察；课程只依赖稳定入口 invokelatest。
    @test applicable(Base.invokelatest, fresh)
end
