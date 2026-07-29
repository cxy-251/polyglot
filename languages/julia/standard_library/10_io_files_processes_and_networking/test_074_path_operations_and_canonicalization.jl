# polyglot-covers: julia.stdlib.paths-metadata-links-and-directory-lifetime

using Test

@testset "词法路径、metadata/link 与临时目录生命周期明确分层" begin
    @test normpath(joinpath("a", "..", "b", ".")) == joinpath("b", "")
    @test basename(joinpath("a", "value.txt")) == "value.txt"
    @test dirname(joinpath("a", "value.txt")) == "a"
    remembered_path = Ref("")
    mktempdir(prefix = "polyglot-julia-") do directory
        remembered_path[] = directory
        target = joinpath(directory, "target.txt")
        link = joinpath(directory, "link.txt")
        nested = joinpath(directory, "nested")
        mkpath(nested)
        write(target, "value")
        write(joinpath(nested, "other.txt"), "other")
        symlink(target, link)
        @test realpath(target) == abspath(target)
        @test islink(link)
        @test readlink(link) == target
        @test stat(link).size == 5
        @test lstat(link).size > 0
        files = String[]
        for (root, _, names) in walkdir(directory)
            append!(files, joinpath.(root, names))
        end
        @test sort(basename.(files)) == ["link.txt", "other.txt", "target.txt"]
    end
    @test !ispath(remembered_path[])
end
