#include "initialization_fixture.hpp"

namespace initialization_fixture {
namespace {

int count = 0;

struct State {
  State() {
    ++count;
  }
};

State state;

}  // namespace

int construction_count() {
  return count;
}

const void* state_address() {
  return &state;
}

}  // namespace initialization_fixture
