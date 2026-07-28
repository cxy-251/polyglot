# polyglot-covers: julia.tooling.macroexpansion-documentation-and-names

using Test
using Base.Docs

@testset "macroexpand、Docs 和 names 提供结构化元数据入口" begin
    expanded = macroexpand(Main, :(@assert value > 0))
    @test expanded isa Expr
    @test (@doc sin) !== nothing
    @test nameof(sin) === :sin
    @test parentmodule(sin) === Base
    @test :sin in names(Base; all = true)
end
