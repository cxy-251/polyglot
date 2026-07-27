#pragma once

namespace module_fixture {

extern int shared_value;

int read_shared();
int initialization_count();
int* inline_value_address_from_other_unit();

inline int inline_value = 7;

constexpr int doubled(int value) {
  return value * 2;
}

}  // namespace module_fixture
