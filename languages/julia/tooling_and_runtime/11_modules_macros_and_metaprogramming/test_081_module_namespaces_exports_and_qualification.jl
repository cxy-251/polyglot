# polyglot-covers: julia.tooling.modules-exports-and-qualification

using Test

module CourseGeometry
export area
const unit = :centimeter
area(width, height) = width * height
end

@testset "module 建立 namespace，export 不隐藏 qualified binding" begin
    @test CourseGeometry.area(3, 4) == 12
    @test CourseGeometry.unit === :centimeter
    @test :area in names(CourseGeometry)
    @test :unit in names(CourseGeometry; all = true)
end
