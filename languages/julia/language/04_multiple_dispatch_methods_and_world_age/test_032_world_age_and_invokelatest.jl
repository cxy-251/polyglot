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
    @test direct_result isa Exception
    fresh = Base.invokelatest(getglobal, WorldAgeExample, :fresh)
    @test Base.invokelatest(fresh) == 42
end
