# polyglot-covers: julia.runtime.libdl-handles-and-symbol-lookup

using Test
using Libdl

@testset "Libdl handle 与 symbol pointer 具有显式生命周期" begin
    candidates = Sys.iswindows() ? ["msvcrt.dll"] : ["libc.so.6", "libc.dylib", "libc"]
    library = Libdl.find_library(candidates)
    @test !isempty(library)
    handle = Libdl.dlopen(library)
    try
        symbol = Libdl.dlsym(handle, :strlen)
        @test symbol != C_NULL
        @test ccall(symbol, Csize_t, (Cstring,), "Julia") == 5
    finally
        Libdl.dlclose(handle)
    end
end
