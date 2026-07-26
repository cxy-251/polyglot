#include "module_fixture.hpp"

namespace module_fixture {
namespace {

int count = 1;

}  // namespace

int shared_value = 3;

int read_shared() {
  return shared_value;
}

int initialization_count() {
  return count;
}

}  // namespace module_fixture
