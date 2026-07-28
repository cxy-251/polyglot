# polyglot-covers: julia.tooling.relative-modules-and-imports

using Test

module ParentModule
export public_value
const public_value = 10

module ChildModule
using ..ParentModule: public_value
value() = public_value + 1
end
end

@testset "relative module path 显式绑定父 namespace 的名称" begin
    @test ParentModule.ChildModule.value() == 11
    @test ParentModule.public_value == 10
    @test :public_value in names(ParentModule)
    @test :ChildModule in names(ParentModule; all = true)
end
