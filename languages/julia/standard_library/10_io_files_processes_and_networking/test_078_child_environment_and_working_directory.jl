# polyglot-covers: julia.stdlib.child-environment-and-working-directory

using Test

function child_julia(expression)
    return `$(Base.julia_cmd()) --startup-file=no --history-file=no --project=@stdlib
        --depwarn=error --check-bounds=yes --threads=1 --color=no -e $expression`
end

@testset "child Cmd 可拥有独立 env 和 cwd 而不修改父进程" begin
    parent_value = get(ENV, "POLYGLOT_CHILD_VALUE", nothing)
    command = addenv(
        child_julia("print(ENV[\"POLYGLOT_CHILD_VALUE\"])"),
        "POLYGLOT_CHILD_VALUE" => "child",
    )
    @test read(command, String) == "child"
    @test get(ENV, "POLYGLOT_CHILD_VALUE", nothing) === parent_value
    mktempdir(prefix = "polyglot-julia-") do directory
        cwd_command = Cmd(child_julia("print(pwd())"); dir = directory)
        @test read(cwd_command, String) == directory
        @test pwd() != directory
    end
end
