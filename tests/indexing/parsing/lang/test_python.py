from pathlib import Path

import pytest

from slopo.indexing.parsing.base import CodeUnit, hash_body
from slopo.indexing.parsing.lang.python import parse
from slopo.indexing.scanner import filter_units

FIXTURES = Path(__file__).parent / "fixtures" / "python"

_DATA_ONLY_DATACLASS = b"""\
@dataclass
class Bounds:
    lower: int
    upper: int = 99
"""


@pytest.fixture
def example() -> list[CodeUnit]:
    return parse((FIXTURES / "Example.py").read_bytes())


@pytest.fixture
def nested() -> list[CodeUnit]:
    return parse((FIXTURES / "Nested.py").read_bytes())


@pytest.fixture
def body_sizes() -> list[CodeUnit]:
    return parse((FIXTURES / "BodySizes.py").read_bytes())


@pytest.fixture
def comments() -> list[CodeUnit]:
    return parse((FIXTURES / "Comments.py").read_bytes())


def test_extracts_module_functions_and_methods(example):
    assert [u.name for u in example] == [
        "greet",
        "classify",
        "sum_evens",
        "__init__",
        "increment",
    ]


def test_extracts_data_only_dataclass_as_class_unit():
    units = parse(_DATA_ONLY_DATACLASS)

    assert len(units) == 1
    assert units[0].name == "Bounds"
    assert units[0].body == _DATA_ONLY_DATACLASS.decode().rstrip()
    assert (units[0].start_line, units[0].end_line) == (1, 4)
    assert units[0].body_node_count == 12
    assert units[0].body_hash == hash_body(units[0].body)


@pytest.mark.parametrize(
    "decorator",
    [
        "@dataclass",
        "@dataclass()",
        "@dataclasses.dataclass",
        "@dataclasses.dataclass(slots=True)",
    ],
)
def test_extracts_supported_dataclass_decorator_forms(decorator: str):
    source = f"{decorator}\nclass Settings:\n    enabled: bool\n".encode()
    units = parse(source)

    assert [unit.name for unit in units] == ["Settings"]
    assert units[0].body == f"{decorator}\nclass Settings:\n    enabled: bool"


@pytest.mark.parametrize(
    "decorator",
    [
        "@dataclass  # Data declaration.",
        "@dataclass()  # Data declaration.",
        "@dataclasses.dataclass  # Data declaration.",
        "@dataclasses.dataclass(slots=True)  # Data declaration.",
    ],
)
def test_extracts_dataclass_with_trailing_decorator_comment(decorator: str):
    source = f"{decorator}\nclass Record:\n    value: int\n".encode()
    clean_decorator = decorator.split("  #", maxsplit=1)[0]
    clean_source = f"{clean_decorator}\nclass Record:\n    value: int\n".encode()
    units = parse(source)

    assert [unit.name for unit in units] == ["Record"]
    assert units[0].body_hash == parse(clean_source)[0].body_hash


@pytest.mark.parametrize("decorator", ["@dc", "@attrs.dataclass", "@dataclass.factory"])
def test_does_not_resolve_unsupported_dataclass_aliases(decorator: str):
    source = f"{decorator}\nclass Settings:\n    enabled: bool\n".encode()

    assert parse(source) == []


def test_does_not_extract_undecorated_data_class():
    source = b"class Settings:\n    enabled: bool\n"

    assert parse(source) == []


def test_behavioral_dataclass_keeps_method_unit_without_overlapping_class_unit():
    source = b"""\
@dataclass
class Settings:
    enabled: bool

    def toggle(self):
        self.enabled = not self.enabled
"""

    assert [unit.name for unit in parse(source)] == ["toggle"]


@pytest.mark.parametrize(
    "assignment",
    [
        "handler = lambda value: value",
        "__post_init__ = lambda self: None",
        "limit = 10",
    ],
)
def test_unannotated_assignments_exclude_dataclass_class_unit(assignment: str):
    source = (f"@dataclass\nclass Record:\n    value: int\n    {assignment}\n").encode()

    assert parse(source) == []


@pytest.mark.parametrize(
    "assignment",
    [
        "target.value: int = compute()",
        "values[select_index()]: int = compute()",
        "first, second: tuple[int, int] = compute()",
        "[first, second]: list[int] = compute()",
        "(first, second): tuple[int, int] = compute()",
    ],
)
def test_non_identifier_annotated_targets_exclude_dataclass_class_unit(
    assignment: str,
):
    source = (f"@dataclass\nclass Record:\n    value: int\n    {assignment}\n").encode()

    assert parse(source) == []


def test_annotated_field_default_factory_remains_data_only():
    source = b"""\
@dataclass
class Record:
    values: list[int] = field(default_factory=lambda: build_values())
"""

    assert [unit.name for unit in parse(source)] == ["Record"]


def test_dataclass_body_strips_comments_and_docstring_from_actual_class_source():
    source = '''\
@dataclass
class Bounds:
    # Source-specific notes must not affect duplicate detection.
    """Numeric bounds."""
    lower: int  # Inclusive lower bound.
    upper: int = 99
    marker: str = "#"
'''.encode()

    units = parse(source)

    assert len(units) == 1
    assert units[0].body == (
        "@dataclass\n"
        "class Bounds:\n"
        "    \n"
        "    \n"
        "    lower: int  \n"
        "    upper: int = 99\n"
        '    marker: str = "#"'
    )
    assert (units[0].start_line, units[0].end_line) == (1, 7)


def test_dataclasses_with_async_or_nested_behavior_keep_recursive_method_units():
    source = b"""\
@dataclass
class AsyncSettings:
    enabled: bool

    async def refresh(self):
        return self.enabled


@dataclass
class NestedSettings:
    enabled: bool

    class Metadata:
        def label(self):
            return "settings"
"""

    assert [unit.name for unit in parse(source)] == ["refresh", "label"]


def test_data_only_dataclass_allows_docstring_and_pass():
    source = '''\
@dataclass
class Marker:
    """Marker type."""
    pass
'''.encode()

    units = parse(source)

    assert len(units) == 1
    assert units[0].body == "@dataclass\nclass Marker:\n    \n    pass"
    assert units[0].body_node_count == 2


def test_dataclass_options_are_part_of_exact_body_and_hash():
    template = """\
{decorator}
class Settings:
    enabled: bool
"""
    mutable = parse(template.format(decorator="@dataclass").encode())[0]
    frozen = parse(template.format(decorator="@dataclass(frozen=True)").encode())[0]

    assert mutable.body != frozen.body
    assert mutable.body_hash != frozen.body_hash


def test_fstring_function_body_exact(example):
    greet = next(u for u in example if u.name == "greet")
    assert greet.body == 'def greet(name):\n    return f"{prefix}, {name}!"'


def test_branching_function_body_exact(example):
    classify = next(u for u in example if u.name == "classify")
    assert classify.body == (
        "def classify(n):\n"
        "    if n < 0:\n"
        '        return "negative"\n'
        "    elif n == 0:\n"
        '        return "zero"\n'
        "    else:\n"
        '        return "positive"'
    )


def test_method_body_keeps_class_indentation(example):
    increment = next(u for u in example if u.name == "increment")
    assert increment.body == (
        "def increment(self, by=1):\n"
        "        self.value += by\n"
        "        return self.value"
    )


def test_line_numbers_are_one_based_and_correct(example):
    classify = next(u for u in example if u.name == "classify")
    assert classify.start_line == 8
    assert classify.end_line == 14


def test_nested_function_is_extracted(nested):
    assert [u.name for u in nested] == ["make_adder", "add"]


def test_nested_function_body_exact(nested):
    add = next(u for u in nested if u.name == "add")
    assert add.body == "def add(x):\n        return base + x"


def test_body_node_count_for_pass_body(body_sizes):
    empty = next(u for u in body_sizes if u.name == "empty_body")
    assert empty.body_node_count == 2


def test_body_node_count_for_ellipsis_stub(body_sizes):
    stub = next(u for u in body_sizes if u.name == "stub")
    assert stub.body_node_count == 3


def test_body_node_count_ignores_decorator_and_counts_function_logic(body_sizes):
    fibonacci = next(u for u in body_sizes if u.name == "fibonacci")
    assert fibonacci.body_node_count == 38


def test_strips_line_comments_and_docstrings_but_keeps_string_assignments(comments):
    assert comments[0].body == (
        "def with_comments(a, b):\n"
        "    \n"
        "    \n"
        "    total = a + b  \n"
        '    url = "http://example.com/#section"\n'
        "    return total"
    )


def test_comments_and_docstring_are_excluded_from_body_node_count(comments):
    assert comments[0].body_node_count == 16


def test_comments_do_not_change_function_hash_or_body_node_count():
    plain = parse(b"def total(a, b):\n    value = a + b\n    return value\n")[0]
    commented = parse(
        b"def total(a, b):\n"
        b"    # The explanation must not affect threshold eligibility.\n"
        b"    value = a + b  # Keep the result for reuse.\n"
        b"    return value\n"
    )[0]

    assert plain.body_node_count == commented.body_node_count == 9
    assert plain.body_hash == commented.body_hash
    assert filter_units([plain, commented], body_node_count_threshold=10) == []


def test_comments_do_not_change_dataclass_hash_or_threshold_eligibility():
    plain = parse(b"@dataclass\nclass Record:\n    first: int\n    second: int = 2\n")[
        0
    ]
    commented = parse(
        b"@dataclass\n"
        b"class Record:\n"
        b"    # The explanation must not increase the declaration size.\n"
        b"    first: int  # Required input.\n"
        b"    second: int = 2\n"
    )[0]

    assert plain.body_node_count == commented.body_node_count == 12
    assert plain.body_hash == commented.body_hash
    assert filter_units([plain, commented], body_node_count_threshold=13) == []
