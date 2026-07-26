#include "support_020_odr.hpp"

namespace odr_examples {

const int* internal_address_from_b() { return &internal_object; }
int* inline_address_from_b() { return &inline_object; }
int* function_static_address_from_b() { return &inline_function_static(); }
int* external_address_from_b() { return &external_object; }

}  // namespace odr_examples
