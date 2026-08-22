from pathlib import Path

from slopo.indexing.parsing.lang.c import parse

FIXTURES = Path(__file__).parent / "fixtures" / "c"


def test_extracts_c_functions_with_names_and_bodies():
    units = parse((FIXTURES / "Example.c").read_bytes())

    assert [unit.name for unit in units] == ["add", "greet"]
    assert units[0].body == (
        "static int add(int a, int b) {\n"
        "    \n"
        "    return a + b;\n"
        "}"
    )
    assert units[0].body_node_count > 0
