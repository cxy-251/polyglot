#include "support_020_odr.hpp"

namespace odr_examples {

int external_object = 23;

const int* internal_address_from_a() { return &internal_object; }
int* inline_address_from_a() { return &inline_object; }
int* function_static_address_from_a() { return &inline_function_static(); }
int* external_address_from_a() { return &external_object; }

}  // namespace odr_examples
