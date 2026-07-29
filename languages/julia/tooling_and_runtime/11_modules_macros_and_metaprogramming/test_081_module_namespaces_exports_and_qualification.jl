# polyglot-covers: julia.tooling.modules-exports-relative-imports-and-qualification

using Test

module CourseGeometry
export area
const unit = :centimeter
area(width, height) = width * height

module Detail
using ..CourseGeometry: unit
label() = "unit=$unit"
end
end

@testset "module 建立 namespace；export 与 relative import 选择不同 binding 路径" begin
    @test CourseGeometry.area(3, 4) == 12
    @test CourseGeometry.unit === :centimeter
    @test CourseGeometry.Detail.label() == "unit=centimeter"
    @test :area in names(CourseGeometry)
    @test :unit in names(CourseGeometry; all = true)
    @test :Detail in names(CourseGeometry; all = true)
end
