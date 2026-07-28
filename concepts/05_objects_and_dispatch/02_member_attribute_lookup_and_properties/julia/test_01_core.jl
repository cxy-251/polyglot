# polyglot-family: objects_and_dispatch
# polyglot-concept: member_attribute_lookup_and_properties
# polyglot-related: languages/julia/language/05_structs_constructors_and_parametric_types/
# polyglot-related+: test_038_properties_and_explicit_access_protocols.jl
#
# 共同问题：成员语法怎样映射到存储和计算属性；如何绕过定制查原始字段。
# 对照观察：Julia 的 x.name 调用 getproperty，可扩展虚拟属性；getfield 与 fieldnames 提供原始结构入口。

using Test

struct Rectangle
    width::Int
    height::Int
end

Base.getproperty(value::Rectangle, name::Symbol) =
    name === :area ? getfield(value, :width) * getfield(value, :height) : getfield(value, name)

@testset "property 协议不改变字段集合" begin
    rectangle = Rectangle(3, 4)
    @test rectangle.area == 12
    @test rectangle.width == 3
    @test getfield(rectangle, :height) == 4
    @test fieldnames(Rectangle) == (:width, :height)
end
