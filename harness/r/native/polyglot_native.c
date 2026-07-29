#include <R.h>
#include <Rinternals.h>
#include <R_ext/Rdynload.h>
#include <R_ext/Visibility.h>
#include <stdlib.h>

void polyglot_scale(double *values, int *length, double *factor) {
    for (int index = 0; index < *length; ++index) {
        values[index] *= *factor;
    }
}

SEXP C_polyglot_double(SEXP values) {
    if (TYPEOF(values) != REALSXP) {
        error("values must be double");
    }
    R_xlen_t length = XLENGTH(values);
    SEXP result = PROTECT(allocVector(REALSXP, length));
    for (R_xlen_t index = 0; index < length; ++index) {
        REAL(result)[index] = REAL(values)[index] * 2.0;
    }
    UNPROTECT(1);
    return result;
}

SEXP C_polyglot_length(SEXP value) {
    return ScalarReal((double) XLENGTH(value));
}

SEXP C_polyglot_missing_kind(SEXP value) {
    if (TYPEOF(value) != REALSXP || XLENGTH(value) != 1) {
        error("value must be one double");
    }
    double current = REAL(value)[0];
    return ScalarInteger(ISNA(current) ? 1 : (ISNAN(current) ? 2 : 0));
}

static void polyglot_pointer_finalizer(SEXP pointer) {
    int *value = (int *) R_ExternalPtrAddr(pointer);
    if (value != NULL) {
        free(value);
        R_ClearExternalPtr(pointer);
    }
}

SEXP C_polyglot_make_pointer(SEXP value) {
    int *stored = (int *) malloc(sizeof(int));
    if (stored == NULL) {
        error("allocation failed");
    }
    *stored = asInteger(value);
    SEXP pointer = PROTECT(R_MakeExternalPtr(stored, install("polyglot_pointer"), R_NilValue));
    R_RegisterCFinalizerEx(pointer, polyglot_pointer_finalizer, TRUE);
    UNPROTECT(1);
    return pointer;
}

SEXP C_polyglot_read_pointer(SEXP pointer) {
    int *stored = (int *) R_ExternalPtrAddr(pointer);
    if (stored == NULL) {
        error("pointer has been released");
    }
    return ScalarInteger(*stored);
}

SEXP C_polyglot_release_pointer(SEXP pointer) {
    polyglot_pointer_finalizer(pointer);
    return R_NilValue;
}

static const R_CMethodDef c_methods[] = {
    {"polyglot_scale", (DL_FUNC) &polyglot_scale, 3},
    {NULL, NULL, 0}
};

static const R_CallMethodDef call_methods[] = {
    {"C_polyglot_double", (DL_FUNC) &C_polyglot_double, 1},
    {"C_polyglot_length", (DL_FUNC) &C_polyglot_length, 1},
    {"C_polyglot_missing_kind", (DL_FUNC) &C_polyglot_missing_kind, 1},
    {"C_polyglot_make_pointer", (DL_FUNC) &C_polyglot_make_pointer, 1},
    {"C_polyglot_read_pointer", (DL_FUNC) &C_polyglot_read_pointer, 1},
    {"C_polyglot_release_pointer", (DL_FUNC) &C_polyglot_release_pointer, 1},
    {NULL, NULL, 0}
};

void attribute_visible R_init_polyglotnative(DllInfo *dll) {
    R_registerRoutines(dll, c_methods, call_methods, NULL, NULL);
    R_useDynamicSymbols(dll, FALSE);
    R_forceSymbols(dll, FALSE);
}
