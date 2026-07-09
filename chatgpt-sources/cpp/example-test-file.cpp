// Style reference for future generated C++ example files.
//
// The repository is currently checklist-first, so this file documents the
// desired shape for future generated examples rather than acting as a compiled
// test module.

#include <algorithm>
#include <cassert>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

void test_vector_push_back_and_checked_access() {
    std::vector<int> values;
    values.reserve(3);

    values.push_back(10);
    values.push_back(20);

    assert(values.size() == 2);
    assert(values.capacity() >= 3);
    assert(values[0] == 10);
    assert(values.at(1) == 20);
}

void test_string_view_observes_without_owning() {
    std::string text = "prefix:value";
    std::string_view view{text};

    view.remove_prefix(7);

    assert(view == "value");
    assert(text == "prefix:value");
}

void test_algorithm_sort_uses_iterator_range() {
    std::vector<int> values{4, 1, 3, 2};

    std::sort(values.begin(), values.end());

    assert((values == std::vector<int>{1, 2, 3, 4}));
}

void test_documented_exception_boundary() {
    bool caught = false;

    try {
        (void)std::stoi("not-a-number");
    } catch (const std::invalid_argument&) {
        caught = true;
    }

    assert(caught);
}

void test_move_only_ownership_transfer() {
    std::vector<std::string> source;
    source.push_back("payload");

    std::vector<std::string> target = std::move(source);

    assert(target.size() == 1);
    assert(target.front() == "payload");
}

int main() {
    test_vector_push_back_and_checked_access();
    test_string_view_observes_without_owning();
    test_algorithm_sort_uses_iterator_range();
    test_documented_exception_boundary();
    test_move_only_ownership_transfer();
}
