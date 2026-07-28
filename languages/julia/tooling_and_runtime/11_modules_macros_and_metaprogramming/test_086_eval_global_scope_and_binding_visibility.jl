# polyglot-covers: julia.tooling.eval-global-scope-and-binding-visibility

using Test

@testset "Core.eval 修改目标 module 的 global scope 而不是局部 scope" begin
    target = Module(:EvaluationTarget)
    local_value = 1
    Core.eval(target, :(const local_value = 41))
    evaluated = Core.eval(target, :(local_value + 1))
    @test evaluated == 42
    @test local_value == 1
    target_value = Base.invokelatest(getglobal, target, :local_value)
    @test target_value == 41
end
