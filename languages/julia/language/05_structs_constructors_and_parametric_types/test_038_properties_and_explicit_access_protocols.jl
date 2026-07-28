# polyglot-covers: julia.language.properties-and-access-protocols

using Test

struct Rectangle
    width::Int
    height::Int
end

function Base.getproperty(rectangle::Rectangle, name::Symbol)
    name === :area && return getfield(rectangle, :width) * getfield(rectangle, :height)
    return getfield(rectangle, name)
end

Base.propertynames(::Rectangle, private::Bool = false) = (:width, :height, :area)

@testset "property 语法可由协议扩展，原始字段仍由 getfield 访问" begin
    rectangle = Rectangle(3, 4)
    @test rectangle.area == 12
    @test getfield(rectangle, :width) == 3
    @test propertynames(rectangle) == (:width, :height, :area)
    @test hasproperty(rectangle, :area)
end
