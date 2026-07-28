# polyglot-family: objects_and_dispatch
# polyglot-concept: inheritance_dynamic_dispatch_and_super
# polyglot-related: languages/r/language/09_s3_object_system/
# polyglot-related+: test_066_nextmethod_and_class_inheritance.R
#
# 共同问题：继承层次怎样选择动态方法，如何调用下一实现。
# 对照观察：S3 沿 class vector 查找方法，`NextMethod` 继续到后续 class 或 default。

render <- function(x) UseMethod("render")
render.default <- function(x) "default"
render.parent <- function(x) paste0("parent:", NextMethod())
render.child <- function(x) paste0("child:", NextMethod())
value <- structure(1L, class = c("child", "parent"))

stopifnot(identical(render(value), "child:parent:default"))
