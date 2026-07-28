#include <ruby.h>
#include <ruby/thread.h>

#include <stddef.h>
#include <stdint.h>

typedef struct {
  VALUE label;
  long count;
} polyglot_box_t;

typedef struct {
  long limit;
  long result;
} polyglot_sum_args_t;

static VALUE polyglot_module;
static VALUE polyglot_box_class;

static void polyglot_box_mark(void *pointer) {
  polyglot_box_t *box = pointer;
  if (box != NULL) {
    rb_gc_mark_movable(box->label);
  }
}

static void polyglot_box_compact(void *pointer) {
  polyglot_box_t *box = pointer;
  if (box != NULL) {
    box->label = rb_gc_location(box->label);
  }
}

static void polyglot_box_free(void *pointer) {
  ruby_xfree(pointer);
}

static size_t polyglot_box_size(const void *pointer) {
  return pointer == NULL ? 0U : sizeof(polyglot_box_t);
}

static const rb_data_type_t polyglot_box_type = {
  .wrap_struct_name = "PolyglotNative::Box",
  .function = {
    .dmark = polyglot_box_mark,
    .dfree = polyglot_box_free,
    .dsize = polyglot_box_size,
    .dcompact = polyglot_box_compact,
  },
  .parent = NULL,
  .data = NULL,
  .flags = RUBY_TYPED_FREE_IMMEDIATELY,
};

static VALUE polyglot_box_allocate(VALUE klass) {
  polyglot_box_t *box = NULL;
  VALUE object = TypedData_Make_Struct(klass, polyglot_box_t, &polyglot_box_type, box);
  box->label = Qnil;
  box->count = 0;
  return object;
}

static VALUE polyglot_box_initialize(VALUE self, VALUE label) {
  polyglot_box_t *box = NULL;
  StringValue(label);
  TypedData_Get_Struct(self, polyglot_box_t, &polyglot_box_type, box);
  box->label = rb_str_dup(label);
  return self;
}

static VALUE polyglot_box_label(VALUE self) {
  polyglot_box_t *box = NULL;
  TypedData_Get_Struct(self, polyglot_box_t, &polyglot_box_type, box);
  return rb_str_dup(box->label);
}

static VALUE polyglot_box_append(VALUE self, VALUE suffix) {
  polyglot_box_t *box = NULL;
  StringValue(suffix);
  TypedData_Get_Struct(self, polyglot_box_t, &polyglot_box_type, box);
  rb_str_concat(box->label, suffix);
  box->count += 1;
  return self;
}

static VALUE polyglot_box_count(VALUE self) {
  polyglot_box_t *box = NULL;
  TypedData_Get_Struct(self, polyglot_box_t, &polyglot_box_type, box);
  return LONG2NUM(box->count);
}

static VALUE polyglot_add(VALUE self, VALUE left, VALUE right) {
  (void)self;
  return LONG2NUM(NUM2LONG(left) + NUM2LONG(right));
}

static VALUE polyglot_string_bytesize(VALUE self, VALUE string) {
  (void)self;
  StringValue(string);
  return LONG2NUM(RSTRING_LEN(string));
}

static VALUE polyglot_pair(VALUE self, VALUE left, VALUE right) {
  VALUE result;
  (void)self;
  result = rb_ary_new_capa(2);
  rb_ary_push(result, left);
  rb_ary_push(result, right);
  return result;
}

static VALUE polyglot_hash_fetch(VALUE self, VALUE hash, VALUE key) {
  (void)self;
  Check_Type(hash, T_HASH);
  return rb_hash_aref(hash, key);
}

static VALUE polyglot_fail(VALUE self, VALUE message) {
  (void)self;
  StringValue(message);
  rb_raise(rb_eArgError, "%s", StringValueCStr(message));
  return Qnil;
}

static VALUE polyglot_yield_twice(VALUE self, VALUE value) {
  VALUE result;
  (void)self;
  if (!rb_block_given_p()) {
    rb_raise(rb_eArgError, "block required");
  }
  rb_yield(value);
  result = rb_yield(value);
  return result;
}

static VALUE polyglot_call_ruby(VALUE self, VALUE receiver, VALUE method_name) {
  ID method_id;
  (void)self;
  method_id = rb_to_id(method_name);
  return rb_funcall(receiver, method_id, 0);
}

static void *polyglot_sum_without_gvl(void *pointer) {
  polyglot_sum_args_t *arguments = pointer;
  long index;
  arguments->result = 0;
  for (index = 1; index <= arguments->limit; index += 1) {
    arguments->result += index;
  }
  return NULL;
}

static VALUE polyglot_without_gvl_sum(VALUE self, VALUE limit) {
  polyglot_sum_args_t arguments;
  (void)self;
  arguments.limit = NUM2LONG(limit);
  arguments.result = 0;
  if (arguments.limit < 0) {
    rb_raise(rb_eArgError, "limit must be non-negative");
  }
  rb_thread_call_without_gvl(polyglot_sum_without_gvl, &arguments, RUBY_UBF_IO, NULL);
  return LONG2NUM(arguments.result);
}

void Init_polyglot_native(void) {
  polyglot_module = rb_define_module("PolyglotNative");
  rb_define_const(polyglot_module, "RELEASE", rb_str_new_cstr("CRuby 4.0.6"));
  rb_define_singleton_method(polyglot_module, "add", polyglot_add, 2);
  rb_define_singleton_method(polyglot_module, "string_bytesize", polyglot_string_bytesize, 1);
  rb_define_singleton_method(polyglot_module, "pair", polyglot_pair, 2);
  rb_define_singleton_method(polyglot_module, "hash_fetch", polyglot_hash_fetch, 2);
  rb_define_singleton_method(polyglot_module, "fail!", polyglot_fail, 1);
  rb_define_singleton_method(polyglot_module, "yield_twice", polyglot_yield_twice, 1);
  rb_define_singleton_method(polyglot_module, "call_ruby", polyglot_call_ruby, 2);
  rb_define_singleton_method(polyglot_module, "without_gvl_sum", polyglot_without_gvl_sum, 1);

  polyglot_box_class = rb_define_class_under(polyglot_module, "Box", rb_cObject);
  rb_define_alloc_func(polyglot_box_class, polyglot_box_allocate);
  rb_define_method(polyglot_box_class, "initialize", polyglot_box_initialize, 1);
  rb_define_method(polyglot_box_class, "label", polyglot_box_label, 0);
  rb_define_method(polyglot_box_class, "append", polyglot_box_append, 1);
  rb_define_method(polyglot_box_class, "count", polyglot_box_count, 0);
}
