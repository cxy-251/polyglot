# polyglot-covers: r.tooling.base-and-recommended-package-inventory

base_description <- utils::packageDescription("base")
mass_description <- utils::packageDescription("MASS")

stopifnot(
    identical(base_description$Priority, "base"),
    identical(mass_description$Priority, "recommended"),
    nzchar(system.file(package = "methods")),
    nzchar(system.file(package = "Matrix"))
)
