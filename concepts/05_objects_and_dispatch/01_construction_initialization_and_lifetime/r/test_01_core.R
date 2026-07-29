# polyglot-family: objects_and_dispatch
# polyglot-concept: construction_initialization_and_lifetime
# polyglot-related: languages/r/language/10_s4_and_reference_classes/
# polyglot-related+: test_073_s4_classes_slots_and_new.R
#
# 共同问题：构造、验证和生命周期钩子如何分工。
# 对照观察：S4 `new` 初始化 slots 并运行 validity；普通对象生命周期由 GC 管理，不保证 finalizer 时机。

methods::setClass(
    "ConceptRange",
    slots = c(lower = "numeric", upper = "numeric"),
    validity = function(object) if (object@lower <= object@upper) TRUE else "invalid range"
)
valid <- methods::new("ConceptRange", lower = 1, upper = 2)
invalid <- tryCatch(methods::new("ConceptRange", lower = 2, upper = 1), error = identity)

stopifnot(methods::validObject(valid), inherits(invalid, "error"))
