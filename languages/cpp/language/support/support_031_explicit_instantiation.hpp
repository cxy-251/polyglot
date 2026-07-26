#pragma once

#include <cstddef>

namespace explicit_instantiation_examples {

template <typename Value>
class Accumulator {
 public:
  void add(Value value) {
    total_ += value;
    ++count_;
  }

  Value total() const { return total_; }
  std::size_t count() const { return count_; }

 private:
  Value total_{};
  std::size_t count_{};
};

template <typename Value>
Value twice(Value value) {
  return value + value;
}

// extern template 是 explicit instantiation declaration：使用方不再隐式生成 int 版本，
// 程序必须在某个翻译单元提供对应 explicit instantiation definition。
extern template class Accumulator<int>;
extern template int twice<int>(int);

using TwiceFunction = int (*)(int);

int accumulate_in_a(int first, int second);
int accumulate_in_b(int first, int second);
int twice_in_a(int value);
int twice_in_b(int value);
TwiceFunction twice_address_from_a();
TwiceFunction twice_address_from_b();

}  // namespace explicit_instantiation_examples
