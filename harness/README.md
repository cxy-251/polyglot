# Harness and integration

This layer contains executable checks for toolchain bootstrap, exact versions, runner isolation, repository
configuration, offline package fixtures, native builds, and container integration. Shared entry points and
implementations remain in `tools/`.

Language semantics, standard-library contracts, and development workflow concepts belong in `languages/`.
Harness files do not use course numbering or `polyglot-covers`, and their results do not count toward language
curriculum completion.

Each language moves into this layer only during its file-level audit, so the repository never performs a
cross-language template migration.
