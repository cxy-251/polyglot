#include <node_api.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>

// 教学 fixture 只封装错误检查；失败会抛进 JavaScript，不让调用方收到未定义的 napi_value。
#define NAPI_CALL(env, expression)                                            \
  do {                                                                        \
    napi_status status__ = (expression);                                      \
    if (status__ != napi_ok) {                                                \
      const napi_extended_error_info *info__ = NULL;                          \
      napi_get_last_error_info((env), &info__);                               \
      napi_throw_error((env), NULL,                                           \
                       info__ != NULL && info__->error_message != NULL         \
                           ? info__->error_message                            \
                           : "Node-API call failed");                         \
      return NULL;                                                            \
    }                                                                         \
  } while (0)

static napi_value SetNamed(napi_env env, napi_value object, const char *name,
                           napi_value value) {
  NAPI_CALL(env, napi_set_named_property(env, object, name, value));
  return object;
}

static napi_value CreateValues(napi_env env, napi_callback_info info) {
  (void)info;
  napi_value result;
  napi_value value;
  napi_value description;
  NAPI_CALL(env, napi_create_object(env, &result));

  NAPI_CALL(env, napi_get_undefined(env, &value));
  if (SetNamed(env, result, "undefinedValue", value) == NULL) return NULL;
  NAPI_CALL(env, napi_get_null(env, &value));
  if (SetNamed(env, result, "nullValue", value) == NULL) return NULL;
  NAPI_CALL(env, napi_get_boolean(env, true, &value));
  if (SetNamed(env, result, "booleanValue", value) == NULL) return NULL;
  NAPI_CALL(env, napi_create_double(env, 1.25, &value));
  if (SetNamed(env, result, "numberValue", value) == NULL) return NULL;
  NAPI_CALL(env, napi_create_bigint_int64(env, INT64_C(9007199254740993), &value));
  if (SetNamed(env, result, "bigintValue", value) == NULL) return NULL;
  NAPI_CALL(env, napi_create_string_utf8(env, "native text", NAPI_AUTO_LENGTH, &value));
  if (SetNamed(env, result, "stringValue", value) == NULL) return NULL;
  NAPI_CALL(env, napi_create_string_utf8(env, "native-symbol", NAPI_AUTO_LENGTH,
                                         &description));
  NAPI_CALL(env, napi_create_symbol(env, description, &value));
  if (SetNamed(env, result, "symbolValue", value) == NULL) return NULL;
  return result;
}

static napi_value InspectCall(napi_env env, napi_callback_info info) {
  size_t argc = 8;
  napi_value argv[8];
  napi_value this_arg;
  NAPI_CALL(env, napi_get_cb_info(env, info, &argc, argv, &this_arg, NULL));

  bool same_receiver = false;
  if (argc > 0) {
    NAPI_CALL(env, napi_strict_equals(env, this_arg, argv[0], &same_receiver));
  }
  double sum = 0;
  for (size_t index = 1; index < argc; index += 1) {
    double number;
    NAPI_CALL(env, napi_get_value_double(env, argv[index], &number));
    sum += number;
  }

  napi_value result;
  napi_value value;
  NAPI_CALL(env, napi_create_object(env, &result));
  NAPI_CALL(env, napi_create_uint32(env, (uint32_t)argc, &value));
  if (SetNamed(env, result, "argc", value) == NULL) return NULL;
  NAPI_CALL(env, napi_get_boolean(env, same_receiver, &value));
  if (SetNamed(env, result, "sameReceiver", value) == NULL) return NULL;
  NAPI_CALL(env, napi_create_double(env, sum, &value));
  if (SetNamed(env, result, "sum", value) == NULL) return NULL;
  return result;
}

static napi_value CallWith(napi_env env, napi_callback_info info) {
  size_t argc = 2;
  napi_value argv[2];
  NAPI_CALL(env, napi_get_cb_info(env, info, &argc, argv, NULL, NULL));
  if (argc < 2) {
    napi_throw_type_error(env, NULL, "callback and value are required");
    return NULL;
  }
  napi_value receiver;
  napi_value result;
  NAPI_CALL(env, napi_get_undefined(env, &receiver));
  NAPI_CALL(env, napi_call_function(env, receiver, argv[0], 1, &argv[1], &result));
  return result;
}

static napi_value ReverseBufferEdges(napi_env env, napi_callback_info info) {
  size_t argc = 1;
  napi_value argv[1];
  NAPI_CALL(env, napi_get_cb_info(env, info, &argc, argv, NULL, NULL));
  bool is_buffer = false;
  NAPI_CALL(env, napi_is_buffer(env, argv[0], &is_buffer));
  if (!is_buffer) {
    napi_throw_type_error(env, NULL, "Buffer required");
    return NULL;
  }
  uint8_t *data;
  size_t length;
  NAPI_CALL(env, napi_get_buffer_info(env, argv[0], (void **)&data, &length));
  if (length > 1) {
    uint8_t first = data[0];
    data[0] = data[length - 1];
    data[length - 1] = first;
  }
  napi_value result;
  NAPI_CALL(env, napi_create_uint32(env, (uint32_t)length, &result));
  return result;
}

static napi_value TypedArrayInfo(napi_env env, napi_callback_info info) {
  size_t argc = 1;
  napi_value argv[1];
  NAPI_CALL(env, napi_get_cb_info(env, info, &argc, argv, NULL, NULL));
  napi_typedarray_type type;
  size_t length;
  void *data;
  napi_value array_buffer;
  size_t byte_offset;
  NAPI_CALL(env, napi_get_typedarray_info(env, argv[0], &type, &length, &data,
                                          &array_buffer, &byte_offset));
  void *buffer_data;
  size_t byte_length;
  NAPI_CALL(env, napi_get_arraybuffer_info(env, array_buffer, &buffer_data, &byte_length));
  (void)data;
  (void)buffer_data;

  napi_value result;
  napi_value value;
  NAPI_CALL(env, napi_create_object(env, &result));
  NAPI_CALL(env, napi_create_uint32(env, (uint32_t)type, &value));
  if (SetNamed(env, result, "type", value) == NULL) return NULL;
  NAPI_CALL(env, napi_create_uint32(env, (uint32_t)length, &value));
  if (SetNamed(env, result, "length", value) == NULL) return NULL;
  NAPI_CALL(env, napi_create_uint32(env, (uint32_t)byte_offset, &value));
  if (SetNamed(env, result, "byteOffset", value) == NULL) return NULL;
  NAPI_CALL(env, napi_create_uint32(env, (uint32_t)byte_length, &value));
  if (SetNamed(env, result, "bufferByteLength", value) == NULL) return NULL;
  return result;
}

static napi_value ThrowCode(napi_env env, napi_callback_info info) {
  (void)info;
  napi_value message;
  napi_value code;
  napi_value error;
  NAPI_CALL(env, napi_create_string_utf8(env, "native failure", NAPI_AUTO_LENGTH,
                                         &message));
  NAPI_CALL(env, napi_create_string_utf8(env, "ERR_NATIVE_EXAMPLE", NAPI_AUTO_LENGTH,
                                         &code));
  NAPI_CALL(env, napi_create_error(env, code, message, &error));
  NAPI_CALL(env, napi_throw(env, error));
  return NULL;
}

typedef struct {
  int64_t value;
} Counter;

static void FinalizeCounter(napi_env env, void *data, void *hint) {
  (void)env;
  (void)hint;
  free(data);
}

static napi_value CounterConstructor(napi_env env, napi_callback_info info) {
  size_t argc = 1;
  napi_value argv[1];
  napi_value this_arg;
  NAPI_CALL(env, napi_get_cb_info(env, info, &argc, argv, &this_arg, NULL));
  Counter *counter = calloc(1, sizeof(*counter));
  if (counter == NULL) {
    napi_throw_error(env, NULL, "allocation failed");
    return NULL;
  }
  if (argc > 0) {
    NAPI_CALL(env, napi_get_value_int64(env, argv[0], &counter->value));
  }
  napi_status status = napi_wrap(env, this_arg, counter, FinalizeCounter, NULL, NULL);
  if (status != napi_ok) {
    free(counter);
    NAPI_CALL(env, status);
  }
  return this_arg;
}

static napi_value CounterIncrement(napi_env env, napi_callback_info info) {
  napi_value this_arg;
  NAPI_CALL(env, napi_get_cb_info(env, info, NULL, NULL, &this_arg, NULL));
  Counter *counter;
  NAPI_CALL(env, napi_unwrap(env, this_arg, (void **)&counter));
  counter->value += 1;
  napi_value result;
  NAPI_CALL(env, napi_create_int64(env, counter->value, &result));
  return result;
}

static napi_value CounterValue(napi_env env, napi_callback_info info) {
  napi_value this_arg;
  NAPI_CALL(env, napi_get_cb_info(env, info, NULL, NULL, &this_arg, NULL));
  Counter *counter;
  NAPI_CALL(env, napi_unwrap(env, this_arg, (void **)&counter));
  napi_value result;
  NAPI_CALL(env, napi_create_int64(env, counter->value, &result));
  return result;
}

typedef struct {
  napi_async_work work;
  napi_deferred deferred;
  double input;
  double output;
} DoubleWork;

static void ExecuteDouble(napi_env env, void *data) {
  (void)env;
  DoubleWork *work = data;
  work->output = work->input * 2;
}

static void CompleteDouble(napi_env env, napi_status status, void *data) {
  DoubleWork *work = data;
  napi_value result;
  if (status == napi_ok && napi_create_double(env, work->output, &result) == napi_ok) {
    napi_resolve_deferred(env, work->deferred, result);
  } else {
    napi_value message;
    napi_value error;
    napi_create_string_utf8(env, "async work failed", NAPI_AUTO_LENGTH, &message);
    napi_create_error(env, NULL, message, &error);
    napi_reject_deferred(env, work->deferred, error);
  }
  napi_delete_async_work(env, work->work);
  free(work);
}

static napi_value DoubleAsync(napi_env env, napi_callback_info info) {
  size_t argc = 1;
  napi_value argv[1];
  NAPI_CALL(env, napi_get_cb_info(env, info, &argc, argv, NULL, NULL));
  DoubleWork *work = calloc(1, sizeof(*work));
  if (work == NULL) {
    napi_throw_error(env, NULL, "allocation failed");
    return NULL;
  }
  napi_status status = napi_get_value_double(env, argv[0], &work->input);
  if (status != napi_ok) {
    free(work);
    NAPI_CALL(env, status);
  }
  napi_value promise;
  napi_value resource_name;
  NAPI_CALL(env, napi_create_promise(env, &work->deferred, &promise));
  NAPI_CALL(env, napi_create_string_utf8(env, "polyglot:double", NAPI_AUTO_LENGTH,
                                         &resource_name));
  NAPI_CALL(env, napi_create_async_work(env, NULL, resource_name, ExecuteDouble,
                                        CompleteDouble, work, &work->work));
  NAPI_CALL(env, napi_queue_async_work(env, work->work));
  return promise;
}

NAPI_MODULE_INIT() {
  napi_property_descriptor functions[] = {
      {"createValues", NULL, CreateValues, NULL, NULL, NULL, napi_default, NULL},
      {"inspectCall", NULL, InspectCall, NULL, NULL, NULL, napi_default, NULL},
      {"callWith", NULL, CallWith, NULL, NULL, NULL, napi_default, NULL},
      {"reverseBufferEdges", NULL, ReverseBufferEdges, NULL, NULL, NULL,
       napi_default, NULL},
      {"typedArrayInfo", NULL, TypedArrayInfo, NULL, NULL, NULL, napi_default,
       NULL},
      {"throwCode", NULL, ThrowCode, NULL, NULL, NULL, napi_default, NULL},
      {"doubleAsync", NULL, DoubleAsync, NULL, NULL, NULL, napi_default, NULL},
  };
  NAPI_CALL(env, napi_define_properties(
                     env, exports, sizeof(functions) / sizeof(functions[0]), functions));

  napi_property_descriptor methods[] = {
      {"increment", NULL, CounterIncrement, NULL, NULL, NULL, napi_default, NULL},
      {"value", NULL, NULL, CounterValue, NULL, NULL, napi_default, NULL},
  };
  napi_value counter_class;
  NAPI_CALL(env, napi_define_class(env, "Counter", NAPI_AUTO_LENGTH,
                                   CounterConstructor, NULL,
                                   sizeof(methods) / sizeof(methods[0]), methods,
                                   &counter_class));
  if (SetNamed(env, exports, "Counter", counter_class) == NULL) return NULL;

  uint32_t version;
  napi_value version_value;
  NAPI_CALL(env, napi_get_version(env, &version));
  NAPI_CALL(env, napi_create_uint32(env, version, &version_value));
  if (SetNamed(env, exports, "runtimeNapiVersion", version_value) == NULL) return NULL;
  return exports;
}
