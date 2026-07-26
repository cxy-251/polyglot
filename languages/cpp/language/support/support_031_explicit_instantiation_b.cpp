#include "support_031_explicit_instantiation.hpp"

namespace explicit_instantiation_examples {

int accumulate_in_b(int first, int second) {
  Accumulator<int> accumulator;
  accumulator.add(first);
  accumulator.add(second);
  return accumulator.total();
}

int twice_in_b(int value) { return twice(value); }

TwiceFunction twice_address_from_b() { return &twice<int>; }

}  // namespace explicit_instantiation_examples
