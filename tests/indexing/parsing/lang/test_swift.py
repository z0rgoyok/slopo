from pathlib import Path

from slopo.indexing.parsing.lang.swift import parse

FIXTURES = Path(__file__).parent / "fixtures" / "swift"


def test_extracts_swift_functions_initializers_and_bound_lambdas():
    units = parse((FIXTURES / "Example.swift").read_bytes())

    assert [unit.name for unit in units] == ["add", "init", "multiply", "increment"]
    assert all(unit.body_node_count > 0 for unit in units)


def test_swift_function_body_includes_signature():
    units = parse((FIXTURES / "Example.swift").read_bytes())

    add = next(unit for unit in units if unit.name == "add")
    assert add.body == (
        "func add(_ a: Int, _ b: Int) -> Int {\n"
        "    \n"
        "    a + b\n"
        "}"
    )
