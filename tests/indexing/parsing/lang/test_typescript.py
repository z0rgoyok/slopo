from pathlib import Path

import pytest

from slopo.indexing.parsing.base import CodeUnit
from slopo.indexing.parsing.lang.typescript import parse, parse_tsx

FIXTURES = Path(__file__).parent / "fixtures" / "typescript"


@pytest.fixture
def example() -> list[CodeUnit]:
    return parse((FIXTURES / "Example.ts").read_bytes())


@pytest.fixture
def nested() -> list[CodeUnit]:
    return parse((FIXTURES / "Nested.ts").read_bytes())


@pytest.fixture
def nested_in_body() -> list[CodeUnit]:
    return parse((FIXTURES / "NestedInBody.ts").read_bytes())


@pytest.fixture
def body_sizes() -> list[CodeUnit]:
    return parse((FIXTURES / "BodySizes.ts").read_bytes())


@pytest.fixture
def comments() -> list[CodeUnit]:
    return parse((FIXTURES / "Comments.ts").read_bytes())


def test_extracts_functions_arrows_and_methods(example):
    assert [u.name for u in example] == [
        "add",
        "greet",
        "fetchUser",
        "constructor",
        "area",
    ]


def test_function_declaration_body_exact(example):
    add = next(u for u in example if u.name == "add")
    assert (
        add.body == "function add(a: number, b: number): number {\n  return a + b;\n}"
    )


def test_arrow_function_named_from_binding(example):
    greet = next(u for u in example if u.name == "greet")
    assert greet.body == "(name: string): string => {\n  return `Hello, ${name}!`;\n}"


def test_async_function_body_includes_signature(example):
    fetch_user = next(u for u in example if u.name == "fetchUser")
    assert fetch_user.body == (
        "async function fetchUser(id: number): Promise<User> {\n"
        "  const response = await fetch(`/users/${id}`);\n"
        "  return response.json();\n"
        "}"
    )


def test_class_method_body_exact(example):
    area = next(u for u in example if u.name == "area")
    assert area.body == "area(): number {\n    return Math.PI * this.radius ** 2;\n  }"


def test_line_numbers_are_one_based_and_correct(example):
    add = next(u for u in example if u.name == "add")
    assert add.start_line == 1
    assert add.end_line == 3


def test_method_nested_in_class_is_extracted(nested):
    assert [u.name for u in nested] == ["add"]


def test_enclosing_and_nested_function_both_extracted(nested_in_body):
    assert [u.name for u in nested_in_body] == ["makeCounter", "increment"]


def test_nested_function_body_exact(nested_in_body):
    increment = next(u for u in nested_in_body if u.name == "increment")
    assert increment.body == (
        "function increment(): number {\n    count += 1;\n    return count;\n  }"
    )


def test_body_node_count_counts_expression_for_concise_arrow(body_sizes):
    square = next(u for u in body_sizes if u.name == "square")
    assert square.body_node_count == 3


def test_body_node_count_counts_only_block_for_empty_body(body_sizes):
    noop = next(u for u in body_sizes if u.name == "noop")
    assert noop.body_node_count == 1


def test_body_node_count_for_larger_body(body_sizes):
    build_config = next(u for u in body_sizes if u.name == "buildConfig")
    assert build_config.body_node_count == 51


def test_strips_line_block_and_doc_comments_from_body(comments):
    assert comments[0].body == (
        "function totalWithTax(amount: number): number {\n"
        "  \n"
        "  const rate = 0.2; \n"
        '  const docsUrl = "https://example.com/* not a comment */";\n'
        "  return amount * (1 + rate);\n"
        "}"
    )


def test_tsx_parser_extracts_components_and_nested_callbacks():
    units = parse_tsx((FIXTURES / "Example.tsx").read_bytes())

    assert [unit.name for unit in units] == ["Greeting", "Button", "<unknown>"]
    assert "<strong>Hello, {name}!</strong>" in units[0].body
    assert "<button" in units[1].body
