#include <R.h>
#include <Rinternals.h>
#include <R_ext/Rdynload.h>
#include <R_ext/Visibility.h>

SEXP C_polyglot_double(SEXP values) {
    R_xlen_t length = XLENGTH(values);
    SEXP result = PROTECT(allocVector(REALSXP, length));

    for (R_xlen_t index = 0; index < length; ++index) {
        REAL(result)[index] = REAL(values)[index] * 2.0;
    }

    UNPROTECT(1);
    return result;
}

static const R_CallMethodDef call_methods[] = {
    {"C_polyglot_double", (DL_FUNC) &C_polyglot_double, 1},
    {NULL, NULL, 0}
};

void attribute_visible R_init_polyglotrfixture(DllInfo *dll) {
    R_registerRoutines(dll, NULL, call_methods, NULL, NULL);
    R_useDynamicSymbols(dll, FALSE);
    R_forceSymbols(dll, TRUE);
}
