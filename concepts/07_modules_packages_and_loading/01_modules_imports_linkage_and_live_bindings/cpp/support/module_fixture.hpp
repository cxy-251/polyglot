#pragma once

namespace module_fixture {

extern int shared_value;

int read_shared();
int initialization_count();

inline int doubled(int value) {
  return value * 2;
}

}  // namespace module_fixture

