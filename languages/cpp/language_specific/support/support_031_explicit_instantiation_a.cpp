#include "support_031_explicit_instantiation.hpp"

namespace explicit_instantiation_examples {

template class Accumulator<int>;
template int twice<int>(int);

int accumulate_in_a(int first, int second) {
  Accumulator<int> accumulator;
  accumulator.add(first);
  accumulator.add(second);
  return accumulator.total();
}

int twice_in_a(int value) { return twice(value); }

TwiceFunction twice_address_from_a() { return &twice<int>; }

}  // namespace explicit_instantiation_examples
