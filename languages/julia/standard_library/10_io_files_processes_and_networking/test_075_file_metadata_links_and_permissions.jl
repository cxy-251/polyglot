# polyglot-covers: julia.stdlib.file-metadata-links-and-permissions

using Test

@testset "stat、lstat 和 symbolic link 观察不同对象层" begin
    mktempdir(prefix = "polyglot-julia-") do directory
        target = joinpath(directory, "target.txt")
        link = joinpath(directory, "link.txt")
        write(target, "value")
        symlink(target, link)
        @test islink(link)
        @test readlink(link) == target
        @test stat(link).size == 5
        @test lstat(link).size > 0
        @test read(link, String) == "value"
    end
end
