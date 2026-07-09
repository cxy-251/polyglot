#!/usr/bin/env python3
"""Audit and regenerate the C++ standard-library baseline.

The baseline is intentionally larger than the curated task list.  It is a
header/symbol inventory used to validate task `covers` entries, not a learning
plan by itself.  Symbols collapse overload sets to one stable name.
"""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
CPP_ROOT = ROOT / "checklists" / "cpp"
BASELINE_PATH = CPP_ROOT / "stdlib.baseline.json"
OBJECTS_PATH = CPP_ROOT / "stdlib.objects.json"
CHECKLIST_PATH = CPP_ROOT / "stdlib.checklist.json"
TASKS_PATH = CPP_ROOT / "stdlib.tasks.json"
CPPREF_WEB_BASE = "https://en.cppreference.com/w/"


def uniq(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def ns(namespace: str, names: Iterable[str]) -> list[str]:
    return [f"{namespace}::{name}" for name in names]


def members(type_name: str, names: Iterable[str]) -> list[str]:
    return [f"{type_name}::{name}" for name in names]


def header(
    name: str,
    title: str,
    area: str,
    symbols: Iterable[str],
    *,
    since: str = "C++98",
    availability: str = "active",
    page: str | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": "header:" + name.replace(".", "_"),
        "header": f"<{name}>",
        "title": title,
        "area": area,
        "since": since,
        "availability": availability,
        "doc_url": page or f"https://en.cppreference.com/w/cpp/header/{name}",
        "symbols": sorted(uniq(symbols)),
        **({"notes": notes} if notes else {}),
    }


CONTAINER_COMMON = [
    "begin",
    "end",
    "cbegin",
    "cend",
    "rbegin",
    "rend",
    "crbegin",
    "crend",
    "empty",
    "size",
    "max_size",
    "front",
    "back",
    "swap",
]

SEQUENCE_MODIFIERS = [
    "assign",
    "assign_range",
    "clear",
    "emplace",
    "erase",
    "insert",
    "insert_range",
    "push_back",
    "emplace_back",
    "pop_back",
    "resize",
]

ORDERED_ASSOCIATIVE = [
    "begin",
    "end",
    "empty",
    "size",
    "clear",
    "insert",
    "emplace",
    "erase",
    "swap",
    "extract",
    "merge",
    "find",
    "contains",
    "count",
    "lower_bound",
    "upper_bound",
    "equal_range",
]

UNORDERED_ASSOCIATIVE = [
    "begin",
    "end",
    "empty",
    "size",
    "clear",
    "insert",
    "emplace",
    "erase",
    "swap",
    "extract",
    "merge",
    "find",
    "contains",
    "count",
    "equal_range",
    "bucket_count",
    "load_factor",
    "max_load_factor",
    "rehash",
    "reserve",
]

STRING_MEMBERS = [
    "assign",
    "append",
    "at",
    "back",
    "begin",
    "capacity",
    "clear",
    "compare",
    "contains",
    "copy",
    "c_str",
    "data",
    "empty",
    "end",
    "ends_with",
    "erase",
    "find",
    "find_first_not_of",
    "find_first_of",
    "find_last_not_of",
    "find_last_of",
    "front",
    "insert",
    "length",
    "max_size",
    "operator+",
    "operator+=",
    "operator[]",
    "pop_back",
    "push_back",
    "replace",
    "reserve",
    "resize",
    "rfind",
    "shrink_to_fit",
    "size",
    "starts_with",
    "substr",
    "swap",
]

STRING_VIEW_MEMBERS = [
    "at",
    "back",
    "begin",
    "compare",
    "contains",
    "copy",
    "data",
    "empty",
    "end",
    "ends_with",
    "find",
    "find_first_not_of",
    "find_first_of",
    "find_last_not_of",
    "find_last_of",
    "front",
    "length",
    "max_size",
    "operator[]",
    "remove_prefix",
    "remove_suffix",
    "rfind",
    "size",
    "starts_with",
    "substr",
    "swap",
]


def build_headers() -> list[dict[str, Any]]:
    return [
        header(
            "cstdlib",
            "General-purpose C library utilities",
            "general",
            [
                "std::abort",
                "std::abs",
                "std::aligned_alloc",
                "std::atexit",
                "std::at_quick_exit",
                "std::atof",
                "std::atoi",
                "std::atol",
                "std::atoll",
                "std::bsearch",
                "std::calloc",
                "std::div",
                "std::exit",
                "std::free",
                "std::getenv",
                "std::labs",
                "std::ldiv",
                "std::llabs",
                "std::lldiv",
                "std::malloc",
                "std::mblen",
                "std::mbstowcs",
                "std::mbtowc",
                "std::qsort",
                "std::quick_exit",
                "std::rand",
                "std::realloc",
                "std::srand",
                "std::strtod",
                "std::strtof",
                "std::strtol",
                "std::strtold",
                "std::strtoll",
                "std::strtoul",
                "std::strtoull",
                "std::system",
                "std::wcstombs",
                "std::wctomb",
                "EXIT_FAILURE",
                "EXIT_SUCCESS",
                "MB_CUR_MAX",
                "NULL",
                "RAND_MAX",
            ],
        ),
        header(
            "execution",
            "Execution policies and execution control",
            "general",
            [
                "std::execution::seq",
                "std::execution::par",
                "std::execution::par_unseq",
                "std::execution::unseq",
                "std::execution::scheduler",
                "std::execution::sender",
                "std::execution::receiver",
            ],
            since="C++17",
        ),
        header(
            "cfloat",
            "Floating-point limits macros",
            "language-support",
            [
                "DECIMAL_DIG",
                "FLT_DIG",
                "FLT_EPSILON",
                "FLT_MAX",
                "FLT_MIN",
                "FLT_RADIX",
                "DBL_DIG",
                "DBL_EPSILON",
                "DBL_MAX",
                "DBL_MIN",
                "LDBL_DIG",
                "LDBL_EPSILON",
                "LDBL_MAX",
                "LDBL_MIN",
            ],
        ),
        header(
            "climits",
            "Integral limits macros",
            "language-support",
            [
                "CHAR_BIT",
                "CHAR_MAX",
                "CHAR_MIN",
                "INT_MAX",
                "INT_MIN",
                "LLONG_MAX",
                "LLONG_MIN",
                "LONG_MAX",
                "LONG_MIN",
                "MB_LEN_MAX",
                "SCHAR_MAX",
                "SCHAR_MIN",
                "SHRT_MAX",
                "SHRT_MIN",
                "UCHAR_MAX",
                "UINT_MAX",
                "ULLONG_MAX",
                "ULONG_MAX",
                "USHRT_MAX",
            ],
        ),
        header(
            "compare",
            "Three-way comparison support",
            "language-support",
            [
                "std::common_comparison_category_t",
                "std::compare_strong_order_fallback",
                "std::compare_three_way",
                "std::compare_weak_order_fallback",
                "std::is_eq",
                "std::is_gt",
                "std::is_gteq",
                "std::is_lt",
                "std::is_lteq",
                "std::is_neq",
                "std::partial_ordering",
                "std::strong_order",
                "std::strong_ordering",
                "std::weak_order",
                "std::weak_ordering",
            ],
            since="C++20",
        ),
        header(
            "contracts",
            "Contracts support",
            "language-support",
            ["std::contracts::contract_violation"],
            since="C++26",
            availability="gated",
        ),
        header(
            "coroutine",
            "Coroutine support",
            "language-support",
            [
                "std::coroutine_handle",
                "std::coroutine_traits",
                "std::noop_coroutine",
                "std::noop_coroutine_handle",
                "std::suspend_always",
                "std::suspend_never",
            ],
            since="C++20",
        ),
        header(
            "csetjmp",
            "Non-local jumps",
            "language-support",
            ["std::jmp_buf", "std::longjmp", "setjmp"],
        ),
        header(
            "csignal",
            "Signal handling",
            "language-support",
            [
                "std::raise",
                "std::sig_atomic_t",
                "std::signal",
                "SIGABRT",
                "SIG_DFL",
                "SIG_ERR",
                "SIGFPE",
                "SIGILL",
                "SIGINT",
                "SIG_IGN",
                "SIGSEGV",
                "SIGTERM",
            ],
        ),
        header(
            "cstdarg",
            "Variable argument lists",
            "language-support",
            ["std::va_list", "va_arg", "va_copy", "va_end", "va_start"],
        ),
        header(
            "cstddef",
            "Standard macros and typedefs",
            "language-support",
            [
                "std::byte",
                "std::max_align_t",
                "std::nullptr_t",
                "std::ptrdiff_t",
                "std::size_t",
                "std::to_integer",
                "NULL",
                "offsetof",
            ],
        ),
        header(
            "cstdint",
            "Fixed-width integer types",
            "language-support",
            [
                "std::int8_t",
                "std::int16_t",
                "std::int32_t",
                "std::int64_t",
                "std::int_fast8_t",
                "std::int_fast16_t",
                "std::int_fast32_t",
                "std::int_fast64_t",
                "std::int_least8_t",
                "std::int_least16_t",
                "std::int_least32_t",
                "std::int_least64_t",
                "std::intmax_t",
                "std::intptr_t",
                "std::uint8_t",
                "std::uint16_t",
                "std::uint32_t",
                "std::uint64_t",
                "std::uint_fast8_t",
                "std::uint_fast16_t",
                "std::uint_fast32_t",
                "std::uint_fast64_t",
                "std::uint_least8_t",
                "std::uint_least16_t",
                "std::uint_least32_t",
                "std::uint_least64_t",
                "std::uintmax_t",
                "std::uintptr_t",
            ],
            since="C++11",
        ),
        header(
            "exception",
            "Exception handling utilities",
            "language-support",
            [
                "std::bad_exception",
                "std::current_exception",
                "std::exception",
                "std::exception_ptr",
                "std::get_terminate",
                "std::make_exception_ptr",
                "std::nested_exception",
                "std::rethrow_exception",
                "std::rethrow_if_nested",
                "std::set_terminate",
                "std::terminate",
                "std::terminate_handler",
                "std::throw_with_nested",
                "std::uncaught_exception",
                "std::uncaught_exceptions",
            ],
        ),
        header(
            "initializer_list",
            "Initializer list support",
            "language-support",
            [
                "std::initializer_list",
                "std::initializer_list::begin",
                "std::initializer_list::end",
                "std::initializer_list::size",
            ],
            since="C++11",
        ),
        header(
            "limits",
            "Numeric limits",
            "language-support",
            [
                "std::numeric_limits",
                "std::numeric_limits::digits",
                "std::numeric_limits::epsilon",
                "std::numeric_limits::infinity",
                "std::numeric_limits::lowest",
                "std::numeric_limits::max",
                "std::numeric_limits::min",
                "std::numeric_limits::quiet_NaN",
            ],
        ),
        header(
            "new",
            "Low-level memory allocation support",
            "language-support",
            [
                "std::align_val_t",
                "std::bad_alloc",
                "std::bad_array_new_length",
                "std::destroying_delete_t",
                "std::get_new_handler",
                "std::hardware_constructive_interference_size",
                "std::hardware_destructive_interference_size",
                "std::launder",
                "std::new_handler",
                "std::nothrow",
                "std::nothrow_t",
                "std::set_new_handler",
                "operator delete",
                "operator new",
            ],
        ),
        header(
            "source_location",
            "Source code location",
            "language-support",
            [
                "std::source_location",
                "std::source_location::column",
                "std::source_location::current",
                "std::source_location::file_name",
                "std::source_location::function_name",
                "std::source_location::line",
            ],
            since="C++20",
        ),
        header(
            "stdfloat",
            "Fixed-width floating-point types",
            "language-support",
            [
                "std::bfloat16_t",
                "std::float16_t",
                "std::float32_t",
                "std::float64_t",
                "std::float128_t",
            ],
            since="C++23",
        ),
        header(
            "typeinfo",
            "Run-time type information",
            "language-support",
            ["std::bad_cast", "std::bad_typeid", "std::type_info"],
        ),
        header(
            "version",
            "Feature test macros",
            "language-support",
            [
                "__cpp_lib_algorithm_default_value_type",
                "__cpp_lib_any",
                "__cpp_lib_chrono",
                "__cpp_lib_concepts",
                "__cpp_lib_containers_ranges",
                "__cpp_lib_expected",
                "__cpp_lib_filesystem",
                "__cpp_lib_format",
                "__cpp_lib_optional",
                "__cpp_lib_ranges",
                "__cpp_lib_span",
                "__cpp_lib_string_view",
                "__cpp_lib_variant",
            ],
            since="C++20",
        ),
        header(
            "concepts",
            "Fundamental library concepts",
            "concepts",
            ns(
                "std",
                [
                    "assignable_from",
                    "common_reference_with",
                    "common_with",
                    "constructible_from",
                    "convertible_to",
                    "copy_constructible",
                    "copyable",
                    "default_initializable",
                    "derived_from",
                    "destructible",
                    "equality_comparable",
                    "equality_comparable_with",
                    "floating_point",
                    "integral",
                    "invocable",
                    "movable",
                    "move_constructible",
                    "predicate",
                    "regular",
                    "same_as",
                    "semiregular",
                    "signed_integral",
                    "strict_weak_order",
                    "swappable",
                    "swappable_with",
                    "totally_ordered",
                    "totally_ordered_with",
                    "unsigned_integral",
                ],
            ),
            since="C++20",
        ),
        header(
            "cassert",
            "Runtime assertions",
            "diagnostics",
            ["assert", "static_assert"],
        ),
        header("cerrno", "C errno macro", "diagnostics", ["errno", "E2BIG", "EDOM", "EILSEQ", "ERANGE"]),
        header(
            "debugging",
            "Debugging support",
            "diagnostics",
            ["std::breakpoint", "std::breakpoint_if_debugging", "std::is_debugger_present"],
            since="C++26",
            availability="gated",
        ),
        header(
            "stacktrace",
            "Stacktrace support",
            "diagnostics",
            [
                "std::basic_stacktrace",
                "std::stacktrace",
                "std::stacktrace_entry",
                "std::to_string",
            ],
            since="C++23",
        ),
        header(
            "stdexcept",
            "Standard exception types",
            "diagnostics",
            ns(
                "std",
                [
                    "domain_error",
                    "invalid_argument",
                    "length_error",
                    "logic_error",
                    "out_of_range",
                    "overflow_error",
                    "range_error",
                    "runtime_error",
                    "underflow_error",
                ],
            ),
        ),
        header(
            "system_error",
            "System error codes",
            "diagnostics",
            [
                "std::errc",
                "std::error_category",
                "std::error_code",
                "std::error_condition",
                "std::generic_category",
                "std::is_error_code_enum",
                "std::is_error_condition_enum",
                "std::make_error_code",
                "std::make_error_condition",
                "std::system_category",
                "std::system_error",
            ],
            since="C++11",
        ),
        header(
            "memory",
            "Memory management and smart pointers",
            "memory",
            [
                "std::addressof",
                "std::align",
                "std::allocate_shared",
                "std::allocator",
                "std::allocator_arg",
                "std::allocator_arg_t",
                "std::allocator_traits",
                "std::assume_aligned",
                "std::construct_at",
                "std::default_delete",
                "std::destroy",
                "std::destroy_at",
                "std::destroy_n",
                "std::enable_shared_from_this",
                "std::get_deleter",
                "std::make_obj_using_allocator",
                "std::make_shared",
                "std::make_unique",
                "std::make_unique_for_overwrite",
                "std::owner_less",
                "std::pointer_traits",
                "std::shared_ptr",
                "std::static_pointer_cast",
                "std::to_address",
                "std::uninitialized_copy",
                "std::uninitialized_default_construct",
                "std::uninitialized_fill",
                "std::uninitialized_move",
                "std::unique_ptr",
                "std::uses_allocator",
                "std::weak_ptr",
            ]
            + members("std::shared_ptr", ["get", "operator bool", "reset", "swap", "use_count", "unique"])
            + members("std::unique_ptr", ["get", "get_deleter", "operator bool", "release", "reset", "swap"])
            + members("std::weak_ptr", ["expired", "lock", "reset", "swap", "use_count"]),
        ),
        header(
            "memory_resource",
            "Polymorphic allocators and memory resources",
            "memory",
            [
                "std::pmr::get_default_resource",
                "std::pmr::memory_resource",
                "std::pmr::monotonic_buffer_resource",
                "std::pmr::new_delete_resource",
                "std::pmr::null_memory_resource",
                "std::pmr::polymorphic_allocator",
                "std::pmr::pool_options",
                "std::pmr::set_default_resource",
                "std::pmr::synchronized_pool_resource",
                "std::pmr::unsynchronized_pool_resource",
            ],
            since="C++17",
        ),
        header(
            "scoped_allocator",
            "Nested allocator adaptor",
            "memory",
            ["std::scoped_allocator_adaptor"],
            since="C++11",
        ),
        header(
            "ratio",
            "Compile-time rational arithmetic",
            "metaprogramming",
            ns(
                "std",
                [
                    "atto",
                    "centi",
                    "deca",
                    "deci",
                    "exa",
                    "femto",
                    "giga",
                    "hecto",
                    "kilo",
                    "mega",
                    "micro",
                    "milli",
                    "nano",
                    "peta",
                    "pico",
                    "ratio",
                    "ratio_add",
                    "ratio_divide",
                    "ratio_equal",
                    "ratio_greater",
                    "ratio_greater_equal",
                    "ratio_less",
                    "ratio_less_equal",
                    "ratio_multiply",
                    "ratio_not_equal",
                    "ratio_subtract",
                    "tera",
                ],
            ),
            since="C++11",
        ),
        header(
            "type_traits",
            "Compile-time type traits",
            "metaprogramming",
            ns(
                "std",
                [
                    "add_const",
                    "add_cv",
                    "add_lvalue_reference",
                    "add_pointer",
                    "add_rvalue_reference",
                    "add_volatile",
                    "aligned_storage",
                    "aligned_union",
                    "alignment_of",
                    "common_reference",
                    "common_reference_t",
                    "common_type",
                    "common_type_t",
                    "conditional",
                    "conditional_t",
                    "conjunction",
                    "decay",
                    "decay_t",
                    "disjunction",
                    "enable_if",
                    "enable_if_t",
                    "extent",
                    "false_type",
                    "has_unique_object_representations",
                    "integral_constant",
                    "invoke_result",
                    "invoke_result_t",
                    "is_abstract",
                    "is_aggregate",
                    "is_arithmetic",
                    "is_array",
                    "is_assignable",
                    "is_base_of",
                    "is_class",
                    "is_compound",
                    "is_const",
                    "is_constructible",
                    "is_convertible",
                    "is_copy_assignable",
                    "is_copy_constructible",
                    "is_default_constructible",
                    "is_destructible",
                    "is_empty",
                    "is_enum",
                    "is_final",
                    "is_floating_point",
                    "is_function",
                    "is_fundamental",
                    "is_integral",
                    "is_integral_v",
                    "is_invocable",
                    "is_invocable_r",
                    "is_literal_type",
                    "is_lvalue_reference",
                    "is_member_function_pointer",
                    "is_member_object_pointer",
                    "is_move_assignable",
                    "is_move_constructible",
                    "is_nothrow_constructible",
                    "is_nothrow_invocable",
                    "is_null_pointer",
                    "is_object",
                    "is_pointer",
                    "is_polymorphic",
                    "is_reference",
                    "is_rvalue_reference",
                    "is_same",
                    "is_same_v",
                    "is_scalar",
                    "is_signed",
                    "is_standard_layout",
                    "is_swappable",
                    "is_trivial",
                    "is_trivially_copyable",
                    "is_union",
                    "is_unsigned",
                    "is_void",
                    "is_volatile",
                    "make_signed",
                    "make_signed_t",
                    "make_unsigned",
                    "make_unsigned_t",
                    "negation",
                    "rank",
                    "remove_all_extents",
                    "remove_const",
                    "remove_cv",
                    "remove_cvref",
                    "remove_cvref_t",
                    "remove_extent",
                    "remove_pointer",
                    "remove_reference",
                    "remove_reference_t",
                    "remove_volatile",
                    "result_of",
                    "true_type",
                    "type_identity",
                    "type_identity_t",
                    "underlying_type",
                    "underlying_type_t",
                    "void_t",
                ],
            ),
            since="C++11",
        ),
        header(
            "any",
            "Type-erased single values",
            "utilities",
            ["std::any", "std::any_cast"] + members("std::any", ["emplace", "has_value", "reset", "swap", "type"]),
            since="C++17",
        ),
        header(
            "bit",
            "Bit manipulation functions",
            "utilities",
            ns(
                "std",
                [
                    "bit_cast",
                    "bit_ceil",
                    "bit_floor",
                    "bit_width",
                    "byteswap",
                    "countl_one",
                    "countl_zero",
                    "countr_one",
                    "countr_zero",
                    "endian",
                    "has_single_bit",
                    "popcount",
                    "rotl",
                    "rotr",
                ],
            ),
            since="C++20",
        ),
        header(
            "bitset",
            "Fixed-size bitsets",
            "utilities",
            ["std::bitset"]
            + members(
                "std::bitset",
                [
                    "all",
                    "any",
                    "count",
                    "flip",
                    "none",
                    "operator&=",
                    "operator<<",
                    "operator<<=",
                    "operator[]",
                    "operator|=",
                    "operator~",
                    "operator^=",
                    "reset",
                    "set",
                    "size",
                    "test",
                    "to_string",
                    "to_ullong",
                    "to_ulong",
                ],
            ),
        ),
        header(
            "charconv",
            "Primitive numeric conversions",
            "utilities",
            ["std::chars_format", "std::from_chars", "std::from_chars_result", "std::to_chars", "std::to_chars_result"],
            since="C++17",
        ),
        header(
            "expected",
            "Expected values",
            "utilities",
            [
                "std::bad_expected_access",
                "std::expected",
                "std::unexpect",
                "std::unexpect_t",
                "std::unexpected",
            ]
            + members(
                "std::expected",
                [
                    "and_then",
                    "emplace",
                    "error",
                    "has_value",
                    "or_else",
                    "operator bool",
                    "swap",
                    "transform",
                    "transform_error",
                    "value",
                    "value_or",
                ],
            ),
            since="C++23",
        ),
        header(
            "format",
            "Modern formatting",
            "utilities",
            ns(
                "std",
                [
                    "basic_format_args",
                    "basic_format_context",
                    "basic_format_parse_context",
                    "format",
                    "format_arg",
                    "format_args",
                    "format_error",
                    "format_to",
                    "format_to_n",
                    "format_to_n_result",
                    "formatted_size",
                    "formatter",
                    "make_format_args",
                    "runtime_format",
                    "vformat",
                    "vformat_to",
                    "visit_format_arg",
                    "wformat_args",
                ],
            ),
            since="C++20",
        ),
        header(
            "functional",
            "Callable wrappers and invocation",
            "utilities",
            ns(
                "std",
                [
                    "bad_function_call",
                    "bind",
                    "bind_back",
                    "bind_front",
                    "bit_and",
                    "bit_not",
                    "bit_or",
                    "bit_xor",
                    "cref",
                    "divides",
                    "equal_to",
                    "function",
                    "greater",
                    "greater_equal",
                    "hash",
                    "identity",
                    "invoke",
                    "invoke_r",
                    "less",
                    "less_equal",
                    "logical_and",
                    "logical_not",
                    "logical_or",
                    "mem_fn",
                    "minus",
                    "modulus",
                    "multiplies",
                    "negate",
                    "not_equal_to",
                    "not_fn",
                    "plus",
                    "ranges::equal_to",
                    "ranges::greater",
                    "ranges::greater_equal",
                    "ranges::less",
                    "ranges::less_equal",
                    "ranges::not_equal_to",
                    "ref",
                    "reference_wrapper",
                    "unwrap_ref_decay",
                ],
            ),
        ),
        header(
            "optional",
            "Optional values",
            "utilities",
            ["std::bad_optional_access", "std::make_optional", "std::nullopt", "std::nullopt_t", "std::optional"]
            + members(
                "std::optional",
                [
                    "and_then",
                    "emplace",
                    "has_value",
                    "or_else",
                    "operator bool",
                    "reset",
                    "swap",
                    "transform",
                    "value",
                    "value_or",
                ],
            ),
            since="C++17",
        ),
        header(
            "tuple",
            "Tuples and tuple protocol",
            "utilities",
            ns(
                "std",
                [
                    "apply",
                    "forward_as_tuple",
                    "get",
                    "ignore",
                    "make_from_tuple",
                    "make_tuple",
                    "tie",
                    "tuple",
                    "tuple_cat",
                    "tuple_element",
                    "tuple_element_t",
                    "tuple_size",
                    "tuple_size_v",
                    "uses_allocator",
                ],
            ),
            since="C++11",
        ),
        header(
            "typeindex",
            "type_info wrapper",
            "utilities",
            ["std::type_index"],
            since="C++11",
        ),
        header(
            "utility",
            "General utility components",
            "utilities",
            ns(
                "std",
                [
                    "as_const",
                    "cmp_equal",
                    "cmp_greater",
                    "cmp_greater_equal",
                    "cmp_less",
                    "cmp_less_equal",
                    "cmp_not_equal",
                    "declval",
                    "exchange",
                    "forward",
                    "forward_like",
                    "in_place",
                    "in_place_index",
                    "in_place_index_t",
                    "in_place_t",
                    "in_place_type",
                    "in_place_type_t",
                    "integer_sequence",
                    "make_index_sequence",
                    "make_integer_sequence",
                    "make_pair",
                    "move",
                    "move_if_noexcept",
                    "pair",
                    "piecewise_construct",
                    "piecewise_construct_t",
                    "rel_ops::operator!=",
                    "rel_ops::operator<",
                    "rel_ops::operator<=",
                    "rel_ops::operator>",
                    "rel_ops::operator>=",
                    "swap",
                    "to_underlying",
                    "unreachable",
                ],
            ),
        ),
        header(
            "variant",
            "Variant values",
            "utilities",
            [
                "std::bad_variant_access",
                "std::get",
                "std::get_if",
                "std::holds_alternative",
                "std::monostate",
                "std::variant",
                "std::variant_alternative",
                "std::variant_alternative_t",
                "std::variant_npos",
                "std::variant_size",
                "std::variant_size_v",
                "std::visit",
            ]
            + members("std::variant", ["emplace", "index", "swap", "valueless_by_exception"]),
            since="C++17",
        ),
        header(
            "array",
            "Fixed-size array container",
            "containers",
            ["std::array", "std::to_array"]
            + members("std::array", CONTAINER_COMMON + ["at", "data", "fill", "operator[]"]),
            since="C++11",
        ),
        header(
            "deque",
            "Double-ended sequence container",
            "containers",
            ["std::deque", "std::erase", "std::erase_if"]
            + members(
                "std::deque",
                CONTAINER_COMMON
                + SEQUENCE_MODIFIERS
                + ["at", "emplace_front", "operator[]", "pop_front", "push_front", "shrink_to_fit"],
            ),
        ),
        header(
            "flat_map",
            "Flat ordered map containers",
            "containers",
            ["std::flat_map", "std::flat_multimap", "std::sorted_equivalent", "std::sorted_unique"],
            since="C++23",
        ),
        header(
            "flat_set",
            "Flat ordered set containers",
            "containers",
            ["std::flat_set", "std::flat_multiset", "std::sorted_equivalent", "std::sorted_unique"],
            since="C++23",
        ),
        header(
            "forward_list",
            "Singly-linked sequence container",
            "containers",
            ["std::forward_list", "std::erase", "std::erase_if"]
            + members(
                "std::forward_list",
                [
                    "assign",
                    "assign_range",
                    "before_begin",
                    "begin",
                    "cbefore_begin",
                    "cbegin",
                    "cend",
                    "clear",
                    "emplace_after",
                    "emplace_front",
                    "empty",
                    "end",
                    "erase_after",
                    "front",
                    "insert_after",
                    "insert_range_after",
                    "max_size",
                    "merge",
                    "pop_front",
                    "push_front",
                    "remove",
                    "remove_if",
                    "resize",
                    "reverse",
                    "sort",
                    "splice_after",
                    "swap",
                    "unique",
                ],
            ),
            since="C++11",
        ),
        header(
            "hive",
            "Hive sequence container",
            "containers",
            ["std::hive"] + members("std::hive", CONTAINER_COMMON + ["clear", "emplace", "erase", "insert", "splice"]),
            since="C++26",
            availability="gated",
        ),
        header(
            "inplace_vector",
            "Fixed-capacity contiguous sequence container",
            "containers",
            ["std::inplace_vector"]
            + members(
                "std::inplace_vector",
                CONTAINER_COMMON
                + SEQUENCE_MODIFIERS
                + ["at", "capacity", "data", "operator[]", "reserve", "shrink_to_fit"],
            ),
            since="C++26",
            availability="gated",
        ),
        header(
            "list",
            "Doubly-linked sequence container",
            "containers",
            ["std::erase", "std::erase_if", "std::list"]
            + members(
                "std::list",
                CONTAINER_COMMON
                + SEQUENCE_MODIFIERS
                + ["merge", "remove", "remove_if", "reverse", "sort", "splice", "unique"],
            ),
        ),
        header(
            "map",
            "Ordered map containers",
            "containers",
            ["std::map", "std::multimap"]
            + members("std::map", ORDERED_ASSOCIATIVE + ["at", "insert_or_assign", "operator[]", "try_emplace"])
            + members("std::multimap", ORDERED_ASSOCIATIVE),
        ),
        header(
            "mdspan",
            "Multidimensional non-owning array views",
            "containers",
            ns(
                "std",
                [
                    "default_accessor",
                    "dextents",
                    "extents",
                    "layout_left",
                    "layout_right",
                    "layout_stride",
                    "mdspan",
                ],
            )
            + members("std::mdspan", ["data_handle", "empty", "extent", "mapping", "operator[]", "rank", "rank_dynamic", "size"]),
            since="C++23",
        ),
        header(
            "queue",
            "Container adaptors for FIFO and priority queues",
            "containers",
            ["std::priority_queue", "std::queue"]
            + members("std::queue", ["back", "emplace", "empty", "front", "pop", "push", "push_range", "size", "swap"])
            + members("std::priority_queue", ["emplace", "empty", "pop", "push", "push_range", "size", "swap", "top"]),
        ),
        header(
            "set",
            "Ordered set containers",
            "containers",
            ["std::multiset", "std::set"]
            + members("std::set", ORDERED_ASSOCIATIVE)
            + members("std::multiset", ORDERED_ASSOCIATIVE),
        ),
        header(
            "span",
            "Contiguous non-owning views",
            "containers",
            ["std::as_bytes", "std::as_writable_bytes", "std::dynamic_extent", "std::span"]
            + members(
                "std::span",
                ["at", "back", "begin", "data", "empty", "end", "first", "front", "last", "operator[]", "size", "size_bytes", "subspan"],
            ),
            since="C++20",
        ),
        header(
            "stack",
            "Stack container adaptor",
            "containers",
            ["std::stack"] + members("std::stack", ["emplace", "empty", "pop", "push", "push_range", "size", "swap", "top"]),
        ),
        header(
            "unordered_map",
            "Unordered map containers",
            "containers",
            ["std::unordered_map", "std::unordered_multimap"]
            + members(
                "std::unordered_map",
                UNORDERED_ASSOCIATIVE + ["at", "insert_or_assign", "operator[]", "try_emplace"],
            )
            + members("std::unordered_multimap", UNORDERED_ASSOCIATIVE),
            since="C++11",
        ),
        header(
            "unordered_set",
            "Unordered set containers",
            "containers",
            ["std::unordered_multiset", "std::unordered_set"]
            + members("std::unordered_set", UNORDERED_ASSOCIATIVE)
            + members("std::unordered_multiset", UNORDERED_ASSOCIATIVE),
            since="C++11",
        ),
        header(
            "vector",
            "Contiguous dynamic sequence container",
            "containers",
            ["std::erase", "std::erase_if", "std::vector", "std::vector<bool>"]
            + members(
                "std::vector",
                CONTAINER_COMMON
                + SEQUENCE_MODIFIERS
                + ["at", "capacity", "data", "operator[]", "reserve", "shrink_to_fit"],
            )
            + members("std::vector<bool>::reference", ["flip", "operator bool", "operator="]),
        ),
        header(
            "iterator",
            "Iterator utilities",
            "iterators",
            ns(
                "std",
                [
                    "advance",
                    "back_insert_iterator",
                    "back_inserter",
                    "basic_const_iterator",
                    "begin",
                    "bidirectional_iterator_tag",
                    "cbegin",
                    "cend",
                    "common_iterator",
                    "contiguous_iterator_tag",
                    "counted_iterator",
                    "crbegin",
                    "crend",
                    "data",
                    "default_sentinel",
                    "default_sentinel_t",
                    "distance",
                    "empty",
                    "end",
                    "forward_iterator_tag",
                    "front_insert_iterator",
                    "front_inserter",
                    "input_iterator_tag",
                    "inserter",
                    "istream_iterator",
                    "istreambuf_iterator",
                    "iter_common_reference_t",
                    "iter_difference_t",
                    "iter_reference_t",
                    "iter_rvalue_reference_t",
                    "iter_value_t",
                    "iterator",
                    "iterator_traits",
                    "make_const_iterator",
                    "make_move_iterator",
                    "move_iterator",
                    "next",
                    "ostream_iterator",
                    "ostreambuf_iterator",
                    "prev",
                    "random_access_iterator_tag",
                    "ranges::advance",
                    "ranges::distance",
                    "ranges::next",
                    "ranges::prev",
                    "rbegin",
                    "rend",
                    "reverse_iterator",
                    "size",
                    "ssize",
                    "unreachable_sentinel",
                    "unreachable_sentinel_t",
                ],
            ),
        ),
        header(
            "generator",
            "Coroutine generator",
            "ranges",
            ["std::generator"],
            since="C++23",
        ),
        header(
            "ranges",
            "Ranges and views",
            "ranges",
            ns(
                "std",
                [
                    "ranges::borrowed_range",
                    "ranges::common_range",
                    "ranges::contiguous_range",
                    "ranges::dangling",
                    "ranges::empty_view",
                    "ranges::enable_borrowed_range",
                    "ranges::filter_view",
                    "ranges::forward_range",
                    "ranges::input_range",
                    "ranges::iota_view",
                    "ranges::iterator_t",
                    "ranges::join_view",
                    "ranges::owning_view",
                    "ranges::random_access_range",
                    "ranges::range",
                    "ranges::range_difference_t",
                    "ranges::range_reference_t",
                    "ranges::range_size_t",
                    "ranges::range_value_t",
                    "ranges::ref_view",
                    "ranges::reverse_view",
                    "ranges::sized_range",
                    "ranges::subrange",
                    "ranges::subrange_kind",
                    "ranges::transform_view",
                    "ranges::view",
                    "ranges::view_interface",
                    "views::all",
                    "views::chunk",
                    "views::common",
                    "views::counted",
                    "views::drop",
                    "views::drop_while",
                    "views::elements",
                    "views::enumerate",
                    "views::filter",
                    "views::iota",
                    "views::join",
                    "views::keys",
                    "views::lazy_split",
                    "views::reverse",
                    "views::single",
                    "views::split",
                    "views::stride",
                    "views::take",
                    "views::take_while",
                    "views::transform",
                    "views::values",
                    "views::zip",
                ],
            ),
            since="C++20",
        ),
        header(
            "algorithm",
            "Non-modifying, modifying, partitioning, sorting, heap, and set algorithms",
            "algorithms",
            ns(
                "std",
                [
                    "adjacent_find",
                    "all_of",
                    "any_of",
                    "binary_search",
                    "clamp",
                    "copy",
                    "copy_backward",
                    "copy_if",
                    "copy_n",
                    "count",
                    "count_if",
                    "equal",
                    "equal_range",
                    "fill",
                    "fill_n",
                    "find",
                    "find_end",
                    "find_first_of",
                    "find_if",
                    "find_if_not",
                    "for_each",
                    "for_each_n",
                    "generate",
                    "generate_n",
                    "includes",
                    "inplace_merge",
                    "is_heap",
                    "is_heap_until",
                    "is_partitioned",
                    "is_permutation",
                    "is_sorted",
                    "is_sorted_until",
                    "iter_swap",
                    "lexicographical_compare",
                    "lexicographical_compare_three_way",
                    "lower_bound",
                    "make_heap",
                    "max",
                    "max_element",
                    "merge",
                    "min",
                    "min_element",
                    "minmax",
                    "minmax_element",
                    "mismatch",
                    "move",
                    "move_backward",
                    "next_permutation",
                    "none_of",
                    "nth_element",
                    "partial_sort",
                    "partial_sort_copy",
                    "partition",
                    "partition_copy",
                    "partition_point",
                    "pop_heap",
                    "prev_permutation",
                    "push_heap",
                    "ranges::all_of",
                    "ranges::any_of",
                    "ranges::copy",
                    "ranges::copy_if",
                    "ranges::count",
                    "ranges::count_if",
                    "ranges::equal",
                    "ranges::find",
                    "ranges::find_if",
                    "ranges::for_each",
                    "ranges::is_sorted",
                    "ranges::lower_bound",
                    "ranges::max",
                    "ranges::min",
                    "ranges::sort",
                    "ranges::transform",
                    "ranges::upper_bound",
                    "remove",
                    "remove_copy",
                    "remove_copy_if",
                    "remove_if",
                    "replace",
                    "replace_copy",
                    "replace_copy_if",
                    "replace_if",
                    "reverse",
                    "reverse_copy",
                    "rotate",
                    "rotate_copy",
                    "sample",
                    "search",
                    "search_n",
                    "set_difference",
                    "set_intersection",
                    "set_symmetric_difference",
                    "set_union",
                    "shift_left",
                    "shift_right",
                    "shuffle",
                    "sort",
                    "sort_heap",
                    "stable_partition",
                    "stable_sort",
                    "swap",
                    "swap_ranges",
                    "transform",
                    "unique",
                    "unique_copy",
                    "upper_bound",
                ],
            ),
        ),
        header(
            "numeric",
            "Numeric algorithms",
            "algorithms",
            ns(
                "std",
                [
                    "accumulate",
                    "adjacent_difference",
                    "exclusive_scan",
                    "gcd",
                    "inclusive_scan",
                    "inner_product",
                    "iota",
                    "lcm",
                    "midpoint",
                    "partial_sum",
                    "reduce",
                    "saturate_cast",
                    "transform_exclusive_scan",
                    "transform_inclusive_scan",
                    "transform_reduce",
                ],
            ),
        ),
        header(
            "cctype",
            "Narrow character classification",
            "strings",
            ns("std", ["isalnum", "isalpha", "isblank", "iscntrl", "isdigit", "isgraph", "islower", "isprint", "ispunct", "isspace", "isupper", "isxdigit", "tolower", "toupper"]),
        ),
        header(
            "cstring",
            "Byte string handling",
            "strings",
            ns(
                "std",
                [
                    "memchr",
                    "memcmp",
                    "memcpy",
                    "memmove",
                    "memset",
                    "strcat",
                    "strchr",
                    "strcmp",
                    "strcoll",
                    "strcpy",
                    "strcspn",
                    "strerror",
                    "strlen",
                    "strncat",
                    "strncmp",
                    "strncpy",
                    "strpbrk",
                    "strrchr",
                    "strspn",
                    "strstr",
                    "strtok",
                    "strxfrm",
                ],
            ),
        ),
        header(
            "cuchar",
            "Unicode character conversions",
            "strings",
            ["std::c16rtomb", "std::c32rtomb", "std::mbrtoc16", "std::mbrtoc32", "std::mbstate_t"],
            since="C++11",
        ),
        header(
            "cwchar",
            "Wide string handling",
            "strings",
            ns(
                "std",
                [
                    "btowc",
                    "fgetwc",
                    "fgetws",
                    "fputwc",
                    "fputws",
                    "fwide",
                    "fwprintf",
                    "fwscanf",
                    "getwc",
                    "getwchar",
                    "mbrlen",
                    "mbrtowc",
                    "mbsinit",
                    "mbsrtowcs",
                    "putwc",
                    "putwchar",
                    "swprintf",
                    "swscanf",
                    "ungetwc",
                    "vfwprintf",
                    "vfwscanf",
                    "vswprintf",
                    "vswscanf",
                    "vwprintf",
                    "vwscanf",
                    "wcrtomb",
                    "wcscat",
                    "wcschr",
                    "wcscmp",
                    "wcscoll",
                    "wcscpy",
                    "wcscspn",
                    "wcsftime",
                    "wcslen",
                    "wcsncat",
                    "wcsncmp",
                    "wcsncpy",
                    "wcspbrk",
                    "wcsrchr",
                    "wcsrtombs",
                    "wcsspn",
                    "wcsstr",
                    "wcstod",
                    "wcstof",
                    "wcstok",
                    "wcstol",
                    "wcstold",
                    "wcstoll",
                    "wcstoul",
                    "wcstoull",
                    "wcsxfrm",
                    "wctob",
                    "wmemchr",
                    "wmemcmp",
                    "wmemcpy",
                    "wmemmove",
                    "wmemset",
                    "wprintf",
                    "wscanf",
                ],
            ),
        ),
        header(
            "cwctype",
            "Wide character classification",
            "strings",
            ns("std", ["iswalnum", "iswalpha", "iswblank", "iswcntrl", "iswctype", "iswdigit", "iswgraph", "iswlower", "iswprint", "iswpunct", "iswspace", "iswupper", "iswxdigit", "towctrans", "towlower", "towupper", "wctrans", "wctype"]),
        ),
        header(
            "string",
            "Owning strings and string conversions",
            "strings",
            [
                "std::basic_string",
                "std::getline",
                "std::pmr::string",
                "std::stod",
                "std::stof",
                "std::stoi",
                "std::stol",
                "std::stold",
                "std::stoll",
                "std::stoul",
                "std::stoull",
                "std::string",
                "std::to_string",
                "std::to_wstring",
                "std::u16string",
                "std::u32string",
                "std::u8string",
                "std::wstring",
            ]
            + members("std::string", STRING_MEMBERS)
            + members("std::basic_string", STRING_MEMBERS),
        ),
        header(
            "string_view",
            "Non-owning string views",
            "strings",
            [
                "std::basic_string_view",
                "std::string_view",
                "std::u16string_view",
                "std::u32string_view",
                "std::u8string_view",
                "std::wstring_view",
            ]
            + members("std::string_view", STRING_VIEW_MEMBERS)
            + members("std::basic_string_view", STRING_VIEW_MEMBERS),
            since="C++17",
        ),
        header(
            "clocale",
            "C locale support",
            "text",
            ["std::lconv", "std::localeconv", "std::setlocale", "LC_ALL", "LC_COLLATE", "LC_CTYPE", "LC_MONETARY", "LC_NUMERIC", "LC_TIME", "NULL"],
        ),
        header(
            "codecvt",
            "Code conversion facets",
            "text",
            ["std::codecvt", "std::codecvt_base", "std::codecvt_byname", "std::codecvt_mode", "std::codecvt_utf16", "std::codecvt_utf8", "std::codecvt_utf8_utf16"],
            since="C++11",
            availability="deprecated",
            notes=["Deprecated in C++17 and removed in C++26 according to cppreference."],
        ),
        header(
            "locale",
            "Localization library",
            "text",
            ns(
                "std",
                [
                    "bad_cast",
                    "collate",
                    "ctype",
                    "ctype_base",
                    "ctype_byname",
                    "has_facet",
                    "isalnum",
                    "isalpha",
                    "isblank",
                    "iscntrl",
                    "isdigit",
                    "isgraph",
                    "islower",
                    "isprint",
                    "ispunct",
                    "isspace",
                    "isupper",
                    "isxdigit",
                    "locale",
                    "messages",
                    "money_base",
                    "money_get",
                    "money_put",
                    "moneypunct",
                    "num_get",
                    "num_put",
                    "numpunct",
                    "time_base",
                    "time_get",
                    "time_put",
                    "tolower",
                    "toupper",
                    "use_facet",
                    "wbuffer_convert",
                    "wstring_convert",
                ],
            ),
        ),
        header(
            "regex",
            "Regular expressions",
            "text",
            ns(
                "std",
                [
                    "basic_regex",
                    "cmatch",
                    "csub_match",
                    "match_results",
                    "regex",
                    "regex_constants::error_type",
                    "regex_error",
                    "regex_iterator",
                    "regex_match",
                    "regex_replace",
                    "regex_search",
                    "regex_token_iterator",
                    "regex_traits",
                    "smatch",
                    "ssub_match",
                    "sub_match",
                    "wregex",
                    "wsmatch",
                ],
            ),
            since="C++11",
        ),
        header(
            "text_encoding",
            "Text encoding identification",
            "text",
            ["std::text_encoding"],
            since="C++26",
            availability="gated",
        ),
        header(
            "cfenv",
            "Floating-point environment",
            "numerics",
            ns("std", ["feclearexcept", "fegetenv", "fegetexceptflag", "fegetround", "feholdexcept", "feraiseexcept", "fesetenv", "fesetexceptflag", "fesetround", "fetestexcept", "feupdateenv", "fenv_t", "fexcept_t"]),
            since="C++11",
        ),
        header(
            "cmath",
            "Common mathematical functions",
            "numerics",
            ns(
                "std",
                [
                    "abs",
                    "acos",
                    "acosh",
                    "asin",
                    "asinh",
                    "atan",
                    "atan2",
                    "atanh",
                    "cbrt",
                    "ceil",
                    "copysign",
                    "cos",
                    "cosh",
                    "erf",
                    "erfc",
                    "exp",
                    "exp2",
                    "expm1",
                    "fabs",
                    "fdim",
                    "floor",
                    "fma",
                    "fmax",
                    "fmin",
                    "fmod",
                    "fpclassify",
                    "frexp",
                    "hypot",
                    "ilogb",
                    "isfinite",
                    "isgreater",
                    "isgreaterequal",
                    "isinf",
                    "isless",
                    "islessequal",
                    "islessgreater",
                    "isnan",
                    "isnormal",
                    "isunordered",
                    "ldexp",
                    "lgamma",
                    "llrint",
                    "llround",
                    "log",
                    "log10",
                    "log1p",
                    "log2",
                    "logb",
                    "lrint",
                    "lround",
                    "modf",
                    "nan",
                    "nearbyint",
                    "nextafter",
                    "nexttoward",
                    "pow",
                    "remainder",
                    "remquo",
                    "rint",
                    "round",
                    "scalbln",
                    "scalbn",
                    "signbit",
                    "sin",
                    "sinh",
                    "sqrt",
                    "tan",
                    "tanh",
                    "tgamma",
                    "trunc",
                ],
            ),
        ),
        header(
            "complex",
            "Complex numbers",
            "numerics",
            ["std::complex", "std::complex_literals::operator\"\"i", "std::complex_literals::operator\"\"if", "std::complex_literals::operator\"\"il"]
            + ns(
                "std",
                [
                    "abs",
                    "acos",
                    "acosh",
                    "arg",
                    "asin",
                    "asinh",
                    "atan",
                    "atanh",
                    "conj",
                    "cos",
                    "cosh",
                    "exp",
                    "imag",
                    "log",
                    "log10",
                    "norm",
                    "polar",
                    "pow",
                    "proj",
                    "real",
                    "sin",
                    "sinh",
                    "sqrt",
                    "tan",
                    "tanh",
                ],
            ),
        ),
        header(
            "linalg",
            "Linear algebra algorithms",
            "numerics",
            ["std::linalg::conjugated", "std::linalg::scaled", "std::linalg::transposed", "std::linalg::vector_abs_sum", "std::linalg::vector_idx_abs_max"],
            since="C++26",
            availability="gated",
        ),
        header(
            "numbers",
            "Mathematical constants",
            "numerics",
            ns(
                "std::numbers",
                [
                    "e",
                    "egamma",
                    "inv_pi",
                    "inv_sqrt3",
                    "inv_sqrtpi",
                    "ln10",
                    "ln2",
                    "log10e",
                    "log2e",
                    "phi",
                    "pi",
                    "sqrt2",
                    "sqrt3",
                ],
            ),
            since="C++20",
        ),
        header(
            "random",
            "Random engines and distributions",
            "numerics",
            ns(
                "std",
                [
                    "bernoulli_distribution",
                    "binomial_distribution",
                    "cauchy_distribution",
                    "chi_squared_distribution",
                    "default_random_engine",
                    "discrete_distribution",
                    "discard_block_engine",
                    "exponential_distribution",
                    "extreme_value_distribution",
                    "fisher_f_distribution",
                    "gamma_distribution",
                    "generate_canonical",
                    "geometric_distribution",
                    "independent_bits_engine",
                    "knuth_b",
                    "linear_congruential_engine",
                    "lognormal_distribution",
                    "mersenne_twister_engine",
                    "minstd_rand",
                    "minstd_rand0",
                    "mt19937",
                    "mt19937_64",
                    "negative_binomial_distribution",
                    "normal_distribution",
                    "piecewise_constant_distribution",
                    "piecewise_linear_distribution",
                    "poisson_distribution",
                    "random_device",
                    "ranlux24",
                    "ranlux24_base",
                    "ranlux48",
                    "ranlux48_base",
                    "seed_seq",
                    "shuffle_order_engine",
                    "student_t_distribution",
                    "subtract_with_carry_engine",
                    "uniform_int_distribution",
                    "uniform_real_distribution",
                    "weibull_distribution",
                ],
            ),
            since="C++11",
        ),
        header(
            "simd",
            "Data-parallel types",
            "numerics",
            ["std::simd", "std::simd_mask", "std::where_expression"],
            since="C++26",
            availability="gated",
        ),
        header(
            "stdckdint.h",
            "Checked integer arithmetic",
            "numerics",
            ["ckd_add", "ckd_mul", "ckd_sub"],
            since="C++26",
            availability="gated",
        ),
        header(
            "valarray",
            "Numeric arrays",
            "numerics",
            ["std::gslice", "std::gslice_array", "std::indirect_array", "std::mask_array", "std::slice", "std::slice_array", "std::valarray"]
            + members("std::valarray", ["apply", "cshift", "max", "min", "resize", "shift", "size", "sum"]),
        ),
        header(
            "chrono",
            "Date, time, clocks, calendars, and time zones",
            "time",
            ns(
                "std::chrono",
                [
                    "abs",
                    "ceil",
                    "clock_cast",
                    "current_zone",
                    "day",
                    "duration",
                    "duration_cast",
                    "file_clock",
                    "floor",
                    "from_stream",
                    "get_leap_second_info",
                    "gps_clock",
                    "hh_mm_ss",
                    "high_resolution_clock",
                    "hours",
                    "is_am",
                    "is_pm",
                    "last_spec",
                    "leap_second",
                    "leap_second_info",
                    "local_days",
                    "local_info",
                    "local_seconds",
                    "local_time",
                    "locate_zone",
                    "microseconds",
                    "milliseconds",
                    "minutes",
                    "month",
                    "month_day",
                    "month_day_last",
                    "month_weekday",
                    "month_weekday_last",
                    "nanoseconds",
                    "nonexistent_local_time",
                    "parse",
                    "round",
                    "seconds",
                    "steady_clock",
                    "sys_days",
                    "sys_info",
                    "sys_seconds",
                    "sys_time",
                    "system_clock",
                    "tai_clock",
                    "time_point",
                    "time_point_cast",
                    "time_zone",
                    "time_zone_link",
                    "tzdb",
                    "tzdb_list",
                    "utc_clock",
                    "utc_time",
                    "weekday",
                    "weekday_indexed",
                    "weekday_last",
                    "year",
                    "year_month",
                    "year_month_day",
                    "year_month_day_last",
                    "year_month_weekday",
                    "year_month_weekday_last",
                    "zoned_time",
                ],
            ),
            since="C++11",
        ),
        header(
            "ctime",
            "C date and time",
            "time",
            ns("std", ["asctime", "clock", "clock_t", "ctime", "difftime", "gmtime", "localtime", "mktime", "strftime", "time", "time_t", "tm"]),
        ),
        header(
            "cinttypes",
            "Formatting and conversion for integer types",
            "io",
            ["std::imaxabs", "std::imaxdiv", "std::imaxdiv_t", "std::strtoimax", "std::strtoumax", "std::wcstoimax", "std::wcstoumax"],
            since="C++11",
        ),
        header(
            "cstdio",
            "C input/output",
            "io",
            ns(
                "std",
                [
                    "clearerr",
                    "fclose",
                    "feof",
                    "ferror",
                    "fflush",
                    "fgetc",
                    "fgetpos",
                    "fgets",
                    "FILE",
                    "fopen",
                    "fprintf",
                    "fputc",
                    "fputs",
                    "fread",
                    "freopen",
                    "fscanf",
                    "fseek",
                    "fsetpos",
                    "ftell",
                    "fwrite",
                    "getc",
                    "getchar",
                    "perror",
                    "printf",
                    "putc",
                    "putchar",
                    "puts",
                    "remove",
                    "rename",
                    "rewind",
                    "scanf",
                    "setbuf",
                    "setvbuf",
                    "snprintf",
                    "sprintf",
                    "sscanf",
                    "stderr",
                    "stdin",
                    "stdout",
                    "tmpfile",
                    "tmpnam",
                    "ungetc",
                    "vfprintf",
                    "vfscanf",
                    "vprintf",
                    "vscanf",
                    "vsnprintf",
                    "vsprintf",
                    "vsscanf",
                ],
            ),
        ),
        header(
            "filesystem",
            "Filesystem paths and operations",
            "io",
            ns(
                "std::filesystem",
                [
                    "absolute",
                    "canonical",
                    "copy",
                    "copy_file",
                    "copy_options",
                    "copy_symlink",
                    "create_directories",
                    "create_directory",
                    "create_directory_symlink",
                    "create_hard_link",
                    "create_symlink",
                    "current_path",
                    "directory_entry",
                    "directory_iterator",
                    "directory_options",
                    "equivalent",
                    "exists",
                    "file_size",
                    "file_status",
                    "file_time_type",
                    "filesystem_error",
                    "hard_link_count",
                    "is_block_file",
                    "is_character_file",
                    "is_directory",
                    "is_empty",
                    "is_fifo",
                    "is_other",
                    "is_regular_file",
                    "is_socket",
                    "is_symlink",
                    "last_write_time",
                    "path",
                    "permissions",
                    "perms",
                    "proximate",
                    "read_symlink",
                    "recursive_directory_iterator",
                    "relative",
                    "remove",
                    "remove_all",
                    "rename",
                    "resize_file",
                    "space",
                    "space_info",
                    "status",
                    "status_known",
                    "symlink_status",
                    "temp_directory_path",
                    "u8path",
                    "weakly_canonical",
                ],
            )
            + members(
                "std::filesystem::path",
                [
                    "append",
                    "clear",
                    "compare",
                    "concat",
                    "empty",
                    "extension",
                    "filename",
                    "generic_string",
                    "has_extension",
                    "has_filename",
                    "has_parent_path",
                    "is_absolute",
                    "is_relative",
                    "operator/",
                    "operator/=",
                    "parent_path",
                    "relative_path",
                    "remove_filename",
                    "replace_extension",
                    "replace_filename",
                    "root_directory",
                    "root_name",
                    "root_path",
                    "stem",
                    "string",
                    "u8string",
                ],
            ),
            since="C++17",
        ),
        header(
            "fstream",
            "File streams",
            "io",
            ns("std", ["basic_filebuf", "basic_fstream", "basic_ifstream", "basic_ofstream", "filebuf", "fstream", "ifstream", "ofstream", "wfilebuf", "wfstream", "wifstream", "wofstream"]),
        ),
        header(
            "iomanip",
            "Stream manipulators",
            "io",
            ns(
                "std",
                [
                    "boolalpha",
                    "get_money",
                    "get_time",
                    "noboolalpha",
                    "put_money",
                    "put_time",
                    "quoted",
                    "resetiosflags",
                    "setbase",
                    "setfill",
                    "setiosflags",
                    "setprecision",
                    "setw",
                ],
            ),
        ),
        header(
            "iosfwd",
            "Forward declarations for IO streams",
            "io",
            ns("std", ["basic_ios", "basic_iostream", "basic_istream", "basic_ostream", "basic_streambuf", "char_traits", "fstream", "ifstream", "iostream", "istream", "ofstream", "ostream", "sstream", "streambuf"]),
        ),
        header(
            "ios",
            "IO stream base classes",
            "io",
            ["std::basic_ios", "std::fpos", "std::ios", "std::ios_base", "std::io_errc", "std::iostream_category", "std::streamoff", "std::streampos", "std::streamsize"],
        ),
        header(
            "iostream",
            "Standard stream objects",
            "io",
            ["std::cerr", "std::cin", "std::clog", "std::cout", "std::wcerr", "std::wcin", "std::wclog", "std::wcout"],
        ),
        header(
            "istream",
            "Input streams",
            "io",
            ["std::basic_iostream", "std::basic_istream", "std::iostream", "std::istream", "std::wiostream", "std::wistream"]
            + members("std::istream", ["gcount", "get", "getline", "ignore", "peek", "putback", "read", "readsome", "seekg", "sync", "tellg", "unget"]),
        ),
        header(
            "ostream",
            "Output streams",
            "io",
            ["std::basic_ostream", "std::endl", "std::ends", "std::flush", "std::flush_emit", "std::noemit_on_flush", "std::emit_on_flush", "std::ostream", "std::wostream"]
            + members("std::ostream", ["flush", "put", "seekp", "tellp", "write"]),
        ),
        header(
            "print",
            "Formatted printing",
            "io",
            ["std::print", "std::println", "std::vprint_nonunicode", "std::vprint_unicode"],
            since="C++23",
        ),
        header(
            "spanstream",
            "Span-backed streams",
            "io",
            ["std::basic_ispanstream", "std::basic_ospanstream", "std::basic_spanbuf", "std::basic_spanstream", "std::ispanstream", "std::ospanstream", "std::spanstream", "std::wispanstream", "std::wospanstream", "std::wspanstream"],
            since="C++23",
        ),
        header(
            "sstream",
            "String streams",
            "io",
            ["std::basic_istringstream", "std::basic_ostringstream", "std::basic_stringbuf", "std::basic_stringstream", "std::istringstream", "std::ostringstream", "std::stringstream", "std::wistringstream", "std::wostringstream", "std::wstringstream"],
        ),
        header(
            "streambuf",
            "Stream buffers",
            "io",
            ["std::basic_streambuf", "std::streambuf", "std::wstreambuf"],
        ),
        header(
            "strstream",
            "Deprecated array-backed streams",
            "io",
            ["std::istrstream", "std::ostrstream", "std::strstream", "std::strstreambuf"],
            availability="deprecated",
        ),
        header(
            "syncstream",
            "Synchronized output streams",
            "io",
            ["std::basic_osyncstream", "std::basic_syncbuf", "std::osyncstream", "std::syncbuf", "std::wosyncstream", "std::wsyncbuf"],
            since="C++20",
        ),
        header(
            "atomic",
            "Atomic operations",
            "concurrency",
            ["std::atomic", "std::atomic_flag", "std::atomic_ref", "std::memory_order"]
            + members(
                "std::atomic",
                [
                    "compare_exchange_strong",
                    "compare_exchange_weak",
                    "exchange",
                    "fetch_add",
                    "fetch_and",
                    "fetch_or",
                    "fetch_sub",
                    "fetch_xor",
                    "is_lock_free",
                    "load",
                    "notify_all",
                    "notify_one",
                    "operator=",
                    "store",
                    "wait",
                ],
            )
            + ns(
                "std",
                [
                    "atomic_compare_exchange_strong",
                    "atomic_compare_exchange_weak",
                    "atomic_exchange",
                    "atomic_fetch_add",
                    "atomic_fetch_and",
                    "atomic_fetch_or",
                    "atomic_fetch_sub",
                    "atomic_fetch_xor",
                    "atomic_init",
                    "atomic_is_lock_free",
                    "atomic_load",
                    "atomic_notify_all",
                    "atomic_notify_one",
                    "atomic_signal_fence",
                    "atomic_store",
                    "atomic_thread_fence",
                    "atomic_wait",
                    "kill_dependency",
                ],
            ),
            since="C++11",
        ),
        header(
            "barrier",
            "Thread barriers",
            "concurrency",
            ["std::barrier"],
            since="C++20",
        ),
        header(
            "condition_variable",
            "Condition variables",
            "concurrency",
            ["std::condition_variable", "std::condition_variable_any", "std::cv_status", "std::notify_all_at_thread_exit"],
            since="C++11",
        ),
        header(
            "future",
            "Futures and asynchronous work",
            "concurrency",
            ns(
                "std",
                [
                    "async",
                    "future",
                    "future_category",
                    "future_errc",
                    "future_error",
                    "future_status",
                    "launch",
                    "packaged_task",
                    "promise",
                    "shared_future",
                ],
            ),
            since="C++11",
        ),
        header(
            "hazard_pointer",
            "Hazard pointers",
            "concurrency",
            ["std::hazard_pointer", "std::hazard_pointer_obj_base", "std::make_hazard_pointer"],
            since="C++26",
            availability="gated",
        ),
        header(
            "latch",
            "Thread latches",
            "concurrency",
            ["std::latch"],
            since="C++20",
        ),
        header(
            "mutex",
            "Mutexes and locks",
            "concurrency",
            ns(
                "std",
                [
                    "adopt_lock",
                    "adopt_lock_t",
                    "call_once",
                    "defer_lock",
                    "defer_lock_t",
                    "lock",
                    "lock_guard",
                    "mutex",
                    "once_flag",
                    "recursive_mutex",
                    "recursive_timed_mutex",
                    "scoped_lock",
                    "timed_mutex",
                    "try_lock",
                    "try_to_lock",
                    "try_to_lock_t",
                    "unique_lock",
                ],
            ),
            since="C++11",
        ),
        header(
            "rcu",
            "Read-copy-update synchronization",
            "concurrency",
            ["std::rcu_barrier", "std::rcu_default_domain", "std::rcu_domain", "std::rcu_obj_base", "std::rcu_retire", "std::rcu_synchronize"],
            since="C++26",
            availability="gated",
        ),
        header(
            "semaphore",
            "Semaphores",
            "concurrency",
            ["std::binary_semaphore", "std::counting_semaphore"],
            since="C++20",
        ),
        header(
            "shared_mutex",
            "Shared mutexes",
            "concurrency",
            ["std::shared_lock", "std::shared_mutex", "std::shared_timed_mutex"],
            since="C++14",
        ),
        header(
            "stdatomic.h",
            "C compatibility atomics",
            "concurrency",
            ["_Atomic", "std::atomic"],
            since="C++23",
            availability="compatibility",
        ),
        header(
            "stop_token",
            "Cooperative cancellation",
            "concurrency",
            ["std::inplace_stop_callback", "std::inplace_stop_source", "std::inplace_stop_token", "std::never_stop_token", "std::nostopstate", "std::stop_callback", "std::stop_source", "std::stop_token"],
            since="C++20",
        ),
        header(
            "thread",
            "Threads",
            "concurrency",
            ["std::jthread", "std::thread", "std::this_thread::get_id", "std::this_thread::sleep_for", "std::this_thread::sleep_until", "std::this_thread::yield"]
            + members("std::thread", ["detach", "get_id", "hardware_concurrency", "join", "joinable", "native_handle", "swap"])
            + members("std::jthread", ["detach", "get_id", "get_stop_source", "get_stop_token", "join", "joinable", "request_stop", "swap"]),
            since="C++11",
        ),
        header("ccomplex", "Compatibility complex header", "c-compatibility", [], availability="removed", notes=["Empty compatibility header removed in C++20."]),
        header("ciso646", "Alternative token macros", "c-compatibility", ["and", "and_eq", "bitand", "bitor", "compl", "not", "not_eq", "or", "or_eq", "xor", "xor_eq"], availability="removed", notes=["Removed in C++20."]),
        header("cstdalign", "Alignment compatibility header", "c-compatibility", ["alignas", "alignof"], since="C++11", availability="removed", notes=["Empty compatibility header removed in C++20."]),
        header("cstdbool", "Boolean compatibility header", "c-compatibility", ["bool", "false", "true"], since="C++11", availability="removed", notes=["Empty compatibility header removed in C++20."]),
        header("ctgmath", "Type-generic math compatibility header", "c-compatibility", [], since="C++11", availability="removed", notes=["Removed in C++20."]),
        header("stdbit.h", "C bit utilities compatibility header", "c-compatibility", ["stdc_bit_ceil", "stdc_bit_floor", "stdc_bit_width", "stdc_count_ones", "stdc_count_zeros", "stdc_first_leading_one", "stdc_first_trailing_one", "stdc_has_single_bit", "stdc_leading_ones", "stdc_leading_zeros", "stdc_trailing_ones", "stdc_trailing_zeros"], since="C++26", availability="gated"),
        header("stdcountof.h", "C countof compatibility header", "c-compatibility", ["countof"], since="C++26", availability="gated"),
    ]


def build_baseline() -> dict[str, Any]:
    headers = build_headers()
    total_symbols = len({symbol for item in headers for symbol in item["symbols"]})
    return {
        "kind": "cpp-stdlib-baseline",
        "schema_version": 2,
        "standard": "C++23 baseline with C++26 library facilities marked gated",
        "source_urls": [
            "https://en.cppreference.com/w/cpp/header",
            "https://en.cppreference.com/w/cpp/standard_library",
            "https://en.cppreference.com/w/cpp/symbol_index",
        ],
        "source_note": (
            "Generated from tools/cpp_stdlib_audit.py using cppreference's "
            "standard library header organization as a navigable reference. "
            "The normative authority remains the ISO C++ standard/library clauses."
        ),
        "coverage_note": (
            "This is a broad header/symbol inventory, not a task plan. Overload sets "
            "are collapsed to stable API names; exposition-only details are mostly "
            "omitted; deprecated/removed/C++26 facilities remain in the baseline with "
            "availability metadata so tasks can deliberately gate or avoid them."
        ),
        "generated_by": "python3 tools/cpp_stdlib_audit.py refresh-baseline",
        "updated_at": date.today().isoformat(),
        "header_count": len(headers),
        "symbol_count": total_symbols,
        "headers": headers,
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return load_json(path)


def build_symbol_index(baseline: dict[str, Any]) -> dict[str, dict[str, Any]]:
    symbol_index: dict[str, dict[str, Any]] = {}
    for header_item in baseline.get("headers", []):
        for symbol in header_item.get("symbols", []):
            symbol_index.setdefault(
                symbol,
                {
                    "header": header_item.get("header"),
                    "area": header_item.get("area"),
                    "availability": header_item.get("availability", "active"),
                    "since": header_item.get("since"),
                    "doc_url": header_item.get("doc_url"),
                    "header_id": header_item.get("id"),
                },
            )
    return symbol_index


def cppreference_url(path: str | None, anchor: str | None = None) -> str | None:
    if not path:
        return None
    normalized = path.replace("\\", "/").lstrip("/")
    if normalized.endswith(".html"):
        normalized = normalized[:-5]
    url = CPPREF_WEB_BASE + normalized
    if anchor:
        url += "#" + anchor
    return url


def classify_symbol(name: str, header_item: dict[str, Any] | None, known_symbols: set[str]) -> str:
    if not name.startswith("std::"):
        if name.startswith("__cpp") or name.isupper() or name in {"assert", "offsetof", "setjmp", "va_arg", "va_copy", "va_end", "va_start"}:
            return "macro"
        return "c_symbol"

    area = (header_item or {}).get("area")
    header_name = (header_item or {}).get("header")
    parent = parent_name(name)
    leaf = name.rsplit("::", 1)[-1]
    if parent and parent in known_symbols:
        if leaf.startswith("operator"):
            return "member_operator"
        return "member_function" if leaf[:1].islower() or "_" in leaf else "member"
    if any(symbol.startswith(name + "::") for symbol in known_symbols):
        return "type"
    if area == "concepts":
        return "concept"
    if header_name == "<type_traits>" and (leaf.startswith("is_") or leaf.endswith("_t") or leaf.endswith("_v")):
        return "type_trait"
    if leaf.startswith("operator"):
        return "operator"
    if leaf[:1].islower() or "_" in leaf:
        return "function"
    return "type"


def parent_name(name: str) -> str | None:
    if "::" not in name:
        return None
    parent = name.rsplit("::", 1)[0]
    return parent if parent != "std" else None


def object_from_symbol(symbol: str, header_item: dict[str, Any], known_symbols: set[str], source: str) -> dict[str, Any]:
    kind = classify_symbol(symbol, header_item, known_symbols)
    return {
        "id": f"{symbol}#{header_item.get('id', 'baseline')}",
        "name": symbol,
        "kind": kind,
        "header": header_item.get("header"),
        "area": header_item.get("area"),
        "parent": parent_name(symbol),
        "availability": header_item.get("availability", "active"),
        "since": header_item.get("since"),
        "doc_url": header_item.get("doc_url"),
        "source": source,
    }


def build_baseline_objects(baseline: dict[str, Any], source: str = "baseline-fallback") -> list[dict[str, Any]]:
    known_symbols = {symbol for header_item in baseline.get("headers", []) for symbol in header_item.get("symbols", [])}
    objects: list[dict[str, Any]] = []
    for header_item in baseline.get("headers", []):
        for symbol in header_item.get("symbols", []):
            objects.append(object_from_symbol(symbol, header_item, known_symbols, source))
    return objects


def find_cppreference_tag(source_dir: Path | None, tag_file: Path | None) -> Path | None:
    if tag_file:
        return tag_file
    if source_dir is None:
        return None
    preferred = [
        source_dir / "cppreference-doxygen-web.tag.xml",
        source_dir / "cppreference-doxygen-local.tag.xml",
    ]
    for candidate in preferred:
        if candidate.exists():
            return candidate
    matches = sorted(source_dir.rglob("cppreference-doxygen-*.tag.xml"))
    if matches:
        return matches[0]
    matches = sorted(source_dir.rglob("*.tag.xml"))
    return matches[0] if matches else None


def parse_tag_objects(tag_path: Path, baseline: dict[str, Any]) -> list[dict[str, Any]]:
    symbol_index = build_symbol_index(baseline)
    known_symbols = set(symbol_index)
    result: list[dict[str, Any]] = []
    root = ET.parse(tag_path).getroot()

    for compound in root.findall("compound"):
        compound_name = (compound.findtext("name") or "").strip()
        compound_kind = compound.get("kind") or "compound"
        filename = (compound.findtext("filename") or "").strip()
        if compound_name.startswith("std::"):
            meta = symbol_index.get(compound_name, {})
            result.append(
                {
                    "id": f"{compound_name}#{filename or compound_kind}",
                    "name": compound_name,
                    "kind": compound_kind,
                    "header": meta.get("header"),
                    "area": meta.get("area"),
                    "parent": parent_name(compound_name),
                    "availability": meta.get("availability", "active"),
                    "since": meta.get("since"),
                    "doc_url": cppreference_url(filename) or meta.get("doc_url"),
                    "source": "cppreference-doxygen-tag",
                }
            )

        for member in compound.findall("member"):
            member_name = (member.findtext("name") or "").strip()
            if not member_name:
                continue
            full_name = member_name if member_name.startswith("std::") else f"{compound_name}::{member_name}"
            if not full_name.startswith("std::"):
                continue
            anchorfile = (member.findtext("anchorfile") or filename).strip()
            anchor = (member.findtext("anchor") or "").strip() or None
            meta = symbol_index.get(full_name) or symbol_index.get(compound_name) or {}
            result.append(
                {
                    "id": f"{full_name}#{anchorfile or filename}#{anchor or member.get('kind', 'member')}",
                    "name": full_name,
                    "kind": member.get("kind") or classify_symbol(full_name, meta, known_symbols),
                    "header": meta.get("header"),
                    "area": meta.get("area"),
                    "parent": compound_name if compound_name.startswith("std::") else parent_name(full_name),
                    "availability": meta.get("availability", "active"),
                    "since": meta.get("since"),
                    "doc_url": cppreference_url(anchorfile, anchor) or meta.get("doc_url"),
                    "source": "cppreference-doxygen-tag",
                }
            )

    return result


def merge_objects(tag_objects: list[dict[str, Any]], fallback_objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for obj in tag_objects:
        key = obj["name"]
        existing = merged.get(key)
        if existing is None or existing.get("source") == "baseline-fallback":
            merged[key] = obj
    for obj in fallback_objects:
        merged.setdefault(obj["name"], obj)
    return sorted(merged.values(), key=lambda item: (item.get("header") or "", item["name"], item.get("kind") or ""))


def build_objects(source_dir: Path | None = None, tag_file: Path | None = None) -> dict[str, Any]:
    baseline = load_json(BASELINE_PATH)
    fallback_objects = build_baseline_objects(baseline)
    resolved_tag = find_cppreference_tag(source_dir, tag_file)
    tag_objects = parse_tag_objects(resolved_tag, baseline) if resolved_tag else []
    objects = merge_objects(tag_objects, fallback_objects)
    source_counts = Counter(obj.get("source", "unknown") for obj in objects)
    return {
        "kind": "cpp-stdlib-objects",
        "schema_version": 1,
        "standard": baseline.get("standard"),
        "source_baseline": "stdlib.baseline.json",
        "source_kind": "cppreference-doxygen-tag" if resolved_tag else "baseline-fallback",
        "source_path": str(resolved_tag) if resolved_tag else None,
        "source_urls": [
            "https://en.cppreference.com/w/Cppreference:Archives",
            "https://en.cppreference.com/w/cpp/header",
            "https://en.cppreference.com/w/cpp/symbol_index",
        ],
        "coverage_note": (
            "Objects are imported from a cppreference Doxygen tag file when one is supplied. "
            "Baseline symbols are always added as fallback objects so task covers remain auditable."
        ),
        "generated_by": "python3 tools/cpp_stdlib_audit.py refresh-objects",
        "updated_at": date.today().isoformat(),
        "object_count": len(objects),
        "source_counts": dict(sorted(source_counts.items())),
        "objects": objects,
    }


def object_lookup(objects_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {obj["name"]: obj for obj in objects_data.get("objects", [])}


def status_for_availability(availability: str) -> str:
    if availability == "gated":
        return "gated"
    if availability in {"removed", "deprecated"}:
        return "omitted"
    return "todo"


def build_checklist() -> dict[str, Any]:
    baseline = load_json(BASELINE_PATH)
    objects_data = load_optional_json(OBJECTS_PATH)
    if not objects_data:
        objects_data = build_objects()
    objects_by_name = object_lookup(objects_data)
    entries: list[dict[str, Any]] = []
    for header_item in baseline.get("headers", []):
        availability = header_item.get("availability", "active")
        items = []
        for symbol in header_item.get("symbols", []):
            obj = objects_by_name.get(symbol) or object_from_symbol(symbol, header_item, set(), "baseline-fallback")
            items.append(
                {
                    "id": symbol,
                    "title": symbol,
                    "kind": obj.get("kind", "api"),
                    "source": obj.get("source", "stdlib.objects.json"),
                    "availability": obj.get("availability", availability),
                    "doc_url": obj.get("doc_url") or header_item.get("doc_url"),
                    "status": status_for_availability(obj.get("availability", availability)),
                    "test_files": [],
                }
            )
        entries.append(
            {
                "id": header_item["id"],
                "baseline_id": header_item["id"],
                "header": header_item["header"],
                "title": header_item["title"],
                "area": header_item["area"],
                "availability": availability,
                "doc_url": header_item.get("doc_url"),
                "status": status_for_availability(availability),
                "items": items,
            }
        )
    return {
        "kind": "cpp-stdlib-checklist",
        "schema_version": 1,
        "source_baseline": "stdlib.baseline.json",
        "source_objects": "stdlib.objects.json",
        "coverage_note": (
            "Generated audit skeleton. Do not refine this file by hand; put learning judgment "
            "in stdlib.tasks.json."
        ),
        "generated_by": "python3 tools/cpp_stdlib_audit.py refresh-checklist",
        "updated_at": date.today().isoformat(),
        "entries": entries,
    }


def collect_baseline_symbols() -> set[str]:
    baseline = load_json(BASELINE_PATH)
    return {symbol for header_item in baseline.get("headers", []) for symbol in header_item.get("symbols", [])}


def collect_task_covers() -> list[str]:
    tasks = load_json(TASKS_PATH)
    return [cover for task in tasks.get("tasks", []) for cover in task.get("covers", [])]


def audit() -> int:
    baseline = load_json(BASELINE_PATH)
    tasks = load_json(TASKS_PATH)
    baseline_symbols = collect_baseline_symbols()
    task_covers = collect_task_covers()
    objects_data = load_optional_json(OBJECTS_PATH)
    checklist_data = load_optional_json(CHECKLIST_PATH)
    object_names = {obj["name"] for obj in objects_data.get("objects", [])}
    checklist_items = {
        item["id"]
        for entry in checklist_data.get("entries", [])
        for item in entry.get("items", [])
    }
    cover_reference_names = object_names or baseline_symbols
    unknown_covers = sorted(set(task_covers) - cover_reference_names)
    baseline_missing_objects = sorted(baseline_symbols - object_names) if objects_data else []
    objects_missing_checklist = sorted(object_names - checklist_items) if checklist_data else []
    header_availability = Counter(header.get("availability", "active") for header in baseline.get("headers", []))
    task_statuses = Counter(task.get("status", "unknown") for task in tasks.get("tasks", []))
    object_sources = Counter(obj.get("source", "unknown") for obj in objects_data.get("objects", []))
    checklist_statuses = Counter(
        entry.get("status", "unknown")
        for entry in checklist_data.get("entries", [])
    )

    print("C++ stdlib audit")
    print(f"headers: {len(baseline.get('headers', []))}")
    for status, count in sorted(header_availability.items()):
        print(f"  {status}: {count}")
    print(f"baseline symbols: {len(baseline_symbols)}")
    print(f"objects: {len(object_names)}")
    for source, count in sorted(object_sources.items()):
        print(f"  {source}: {count}")
    print(f"checklist entries: {len(checklist_data.get('entries', []))}")
    for status, count in sorted(checklist_statuses.items()):
        print(f"  {status}: {count}")
    print(f"checklist items: {len(checklist_items)}")
    print(f"tasks: {len(tasks.get('tasks', []))}")
    for status, count in sorted(task_statuses.items()):
        print(f"  {status}: {count}")
    print(f"task cover references: {len(task_covers)}")
    print(f"unique task covers: {len(set(task_covers))}")
    print(f"unknown task covers: {len(unknown_covers)}")
    for cover in unknown_covers[:50]:
        print(f"  - {cover}")
    print(f"baseline symbols missing from objects: {len(baseline_missing_objects)}")
    for symbol in baseline_missing_objects[:50]:
        print(f"  - {symbol}")
    print(f"objects missing from checklist: {len(objects_missing_checklist)}")
    for symbol in objects_missing_checklist[:50]:
        print(f"  - {symbol}")
    return 1 if unknown_covers or baseline_missing_objects or objects_missing_checklist else 0


def refresh_baseline() -> int:
    baseline = build_baseline()
    write_json(BASELINE_PATH, baseline)
    print(f"wrote {BASELINE_PATH.relative_to(ROOT)}")
    print(f"headers: {baseline['header_count']}")
    print(f"symbols: {baseline['symbol_count']}")
    return 0


def refresh_objects(source_dir: Path | None = None, tag_file: Path | None = None) -> int:
    objects = build_objects(source_dir=source_dir, tag_file=tag_file)
    write_json(OBJECTS_PATH, objects)
    print(f"wrote {OBJECTS_PATH.relative_to(ROOT)}")
    print(f"objects: {objects['object_count']}")
    for source, count in objects.get("source_counts", {}).items():
        print(f"  {source}: {count}")
    if objects.get("source_kind") == "baseline-fallback":
        print("note: no cppreference tag file was supplied; generated baseline-fallback objects")
    return 0


def refresh_checklist() -> int:
    checklist = build_checklist()
    write_json(CHECKLIST_PATH, checklist)
    item_count = sum(len(entry.get("items", [])) for entry in checklist.get("entries", []))
    print(f"wrote {CHECKLIST_PATH.relative_to(ROOT)}")
    print(f"entries: {len(checklist['entries'])}")
    print(f"items: {item_count}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("audit", help="check C++ task covers against stdlib.baseline.json")
    subparsers.add_parser("refresh-baseline", help="rewrite checklists/cpp/stdlib.baseline.json")
    objects_parser = subparsers.add_parser("refresh-objects", help="rewrite checklists/cpp/stdlib.objects.json")
    objects_parser.add_argument("--source-dir", type=Path, help="directory containing cppreference-doxygen-*.tag.xml")
    objects_parser.add_argument("--tag-file", type=Path, help="explicit cppreference Doxygen tag XML file")
    subparsers.add_parser("refresh-checklist", help="rewrite checklists/cpp/stdlib.checklist.json")
    args = parser.parse_args(argv)

    if args.command == "refresh-baseline":
        return refresh_baseline()
    if args.command == "refresh-objects":
        return refresh_objects(source_dir=args.source_dir, tag_file=args.tag_file)
    if args.command == "refresh-checklist":
        return refresh_checklist()
    if args.command in {None, "audit"}:
        return audit()
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
