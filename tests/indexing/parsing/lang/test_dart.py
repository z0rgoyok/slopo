from pathlib import Path

from slopo.indexing.parsing.lang.dart import parse

FIXTURES = Path(__file__).parent / "fixtures" / "dart"


def test_extracts_dart_functions_methods_and_bound_expressions():
    units = parse((FIXTURES / "Example.dart").read_bytes())

    assert [unit.name for unit in units] == [
        "add",
        "Calculator",
        "multiply",
        "useCallbacks",
        "increment",
        "doubleValue",
    ]
    assert all(unit.body_node_count > 0 for unit in units)


def test_dart_declaration_body_includes_signature():
    units = parse((FIXTURES / "Example.dart").read_bytes())

    add = next(unit for unit in units if unit.name == "add")
    assert add.body == "int add(int a, int b) {\n  \n  return a + b;\n}"
