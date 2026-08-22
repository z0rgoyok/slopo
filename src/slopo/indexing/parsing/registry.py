from pathlib import Path

from slopo.indexing.parsing.lang import (
    c,
    dart,
    javascript,
    csharp,
    elixir,
    rust,
    go,
    php,
    python,
    typescript,
    kotlin,
    java,
    swift,
)
from slopo.indexing.parsing.base import CodeParser

_REGISTRY: dict[str, CodeParser] = {
    ".c": c.parse,
    ".cs": csharp.parse,
    ".cts": typescript.parse,
    ".dart": dart.parse,
    ".ex": elixir.parse,
    ".exs": elixir.parse,
    ".go": go.parse,
    ".h": c.parse,
    ".java": java.parse,
    ".cjs": javascript.parse,
    ".js": javascript.parse,
    ".kt": kotlin.parse,
    ".kts": kotlin.parse,
    ".mjs": javascript.parse,
    ".mts": typescript.parse,
    ".php": php.parse,
    ".py": python.parse,
    ".rs": rust.parse,
    ".ts": typescript.parse,
    ".tsx": typescript.parse_tsx,
    ".swift": swift.parse,
}


def get_parser(path: Path) -> CodeParser:
    suffix = path.suffix.lower()
    parser = _REGISTRY.get(suffix)
    if parser is None:
        raise ValueError(f"No parser registered for '{suffix}' files")
    return parser


def supported_extensions() -> set[str]:
    return set(_REGISTRY)
