from pathlib import Path

import pytest

from slopo.indexing.scanner import filter_units, parse_file, scan_directory

_JAVA = """\
class Calculator {
    int increment(int a) {
        return a + 1;
    }
}
"""

_KOTLIN = """\
fun increment(a: Int): Int {
    return a + 1
}
"""

_PYTHON_DATACLASS = """\
@dataclass
class AgeGroupSpec:
    minimum_age: int
    maximum_age: int = 99
"""


def test_scans_all_supported_languages(tmp_path: Path):
    (tmp_path / "Calculator.java").write_text(_JAVA)
    (tmp_path / "Increment.kt").write_text(_KOTLIN)

    scanned = set(scan_directory(tmp_path, exclude=[]))

    assert scanned == {"Calculator.java", "Increment.kt"}


def test_scans_only_configured_extensions(tmp_path: Path):
    (tmp_path / "Calculator.java").write_text(_JAVA)
    (tmp_path / "Increment.kt").write_text(_KOTLIN)

    scanned = set(scan_directory(tmp_path, exclude=[], source_extensions=[".kt"]))

    assert scanned == {"Increment.kt"}


def test_parses_units_from_each_language(tmp_path: Path):
    (tmp_path / "Calculator.java").write_text(_JAVA)
    (tmp_path / "Increment.kt").write_text(_KOTLIN)

    java_units = parse_file(tmp_path / "Calculator.java")
    kotlin_units = parse_file(tmp_path / "Increment.kt")

    assert [u.name for u in java_units] == ["increment"]
    assert [u.name for u in kotlin_units] == ["increment"]


@pytest.mark.parametrize(
    ("filename", "source", "expected_name"),
    [
        ("module.mjs", "export function increment(a) { return a + 1; }", "increment"),
        ("module.cjs", "function increment(a) { return a + 1; }", "increment"),
        (
            "module.mts",
            "export function increment(a: number) { return a + 1; }",
            "increment",
        ),
        ("module.cts", "function increment(a: number) { return a + 1; }", "increment"),
        ("component.tsx", "function View() { return <main />; }", "View"),
        ("build.kts", "fun increment(a: Int): Int { return a + 1 }", "increment"),
        ("config.exs", "def increment(a), do: a + 1", "increment"),
        ("module.dart", "int increment(int a) { return a + 1; }", "increment"),
        ("Module.swift", "func increment(_ a: Int) -> Int { a + 1 }", "increment"),
        ("module.c", "int increment(int a) { return a + 1; }", "increment"),
        ("module.h", "static int increment(int a) { return a + 1; }", "increment"),
    ],
)
def test_scans_and_parses_supported_extension_variants(
    tmp_path: Path,
    filename: str,
    source: str,
    expected_name: str,
):
    path = tmp_path / filename
    path.write_text(source)

    assert list(scan_directory(tmp_path, exclude=[])) == [filename]
    assert [unit.name for unit in parse_file(path)] == [expected_name]


def test_recurses_into_subdirectories_with_paths_relative_to_root(tmp_path: Path):
    (tmp_path / "sub" / "nested").mkdir(parents=True)
    (tmp_path / "sub" / "nested" / "Increment.kt").write_text(_KOTLIN)

    scanned = list(scan_directory(tmp_path, exclude=[]))

    assert scanned == ["sub/nested/Increment.kt"]


def test_ignores_unsupported_file_types(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("not code")
    (tmp_path / "data.json").write_text("{}")

    assert list(scan_directory(tmp_path, exclude=[])) == []


def test_excludes_units_below_body_node_count_threshold(tmp_path: Path):
    (tmp_path / "Calculator.java").write_text(_JAVA)
    units = parse_file(tmp_path / "Calculator.java")

    filtered = filter_units(units, body_node_count_threshold=1000)

    assert filtered == []


def test_keeps_data_only_dataclass_at_eight_node_threshold(tmp_path: Path):
    path = tmp_path / "age_group.py"
    path.write_text(_PYTHON_DATACLASS)

    filtered = filter_units(parse_file(path), body_node_count_threshold=8)

    assert [unit.name for unit in filtered] == ["AgeGroupSpec"]


def test_excludes_units_exceeding_max_body_chars(tmp_path: Path):
    big_body = "\n".join(f"        int x{i} = {i};" for i in range(500))
    assert len(big_body) == 11779
    source = (
        "class Big {\n"
        "    void huge() {\n"
        f"{big_body}\n"
        "    }\n"
        "    int small(int a) {\n"
        "        return a + 1;\n"
        "    }\n"
        "}\n"
    )
    (tmp_path / "Big.java").write_text(source)
    units = parse_file(tmp_path / "Big.java")

    filtered = filter_units(units, body_node_count_threshold=0)

    assert [u.name for u in filtered] == ["small"]


def test_skips_files_under_excluded_directory(tmp_path: Path):
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "Generated.kt").write_text(_KOTLIN)
    (tmp_path / "Increment.kt").write_text(_KOTLIN)

    scanned = list(scan_directory(tmp_path, exclude=["build/"]))

    assert scanned == ["Increment.kt"]


def test_skips_files_matching_glob_pattern(tmp_path: Path):
    (tmp_path / "Increment.gen.kt").write_text(_KOTLIN)
    (tmp_path / "Increment.kt").write_text(_KOTLIN)

    scanned = list(scan_directory(tmp_path, exclude=["*.gen.kt"]))

    assert scanned == ["Increment.kt"]


def test_negation_pattern_reincludes_excluded_file(tmp_path: Path):
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "Keep.kt").write_text(_KOTLIN)
    (tmp_path / "build" / "Drop.kt").write_text(_KOTLIN)

    scanned = list(scan_directory(tmp_path, exclude=["build/", "!build/Keep.kt"]))

    assert scanned == ["build/Keep.kt"]
