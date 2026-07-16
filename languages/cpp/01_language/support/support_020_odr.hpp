#pragma once

namespace odr_examples {

inline int inline_object = 41;

inline int& inline_function_static() {
  static int value = 17;
  return value;
}

// 头文件中的普通 const 命名空间变量默认具有内部链接，每个翻译单元各有一个对象。
const int internal_object = 7;

extern int external_object;

const int* internal_address_from_a();
const int* internal_address_from_b();
int* inline_address_from_a();
int* inline_address_from_b();
int* function_static_address_from_a();
int* function_static_address_from_b();
int* external_address_from_a();
int* external_address_from_b();

}  // namespace odr_examples
