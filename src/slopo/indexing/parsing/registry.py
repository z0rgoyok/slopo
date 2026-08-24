import hashlib
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ParserRegistration:
    parser_id: str
    version: int
    parser: CodeParser


# Increment a parser version whenever its CodeUnit output can change. Persisted
# file mtimes are safe to reuse only while the active parser profile is identical.
_C = ParserRegistration("c", 1, c.parse)
_CSHARP = ParserRegistration("csharp", 1, csharp.parse)
_DART = ParserRegistration("dart", 1, dart.parse)
_ELIXIR = ParserRegistration("elixir", 1, elixir.parse)
_GO = ParserRegistration("go", 1, go.parse)
_JAVA = ParserRegistration("java", 1, java.parse)
_JAVASCRIPT = ParserRegistration("javascript", 1, javascript.parse)
_KOTLIN = ParserRegistration("kotlin", 1, kotlin.parse)
_PHP = ParserRegistration("php", 1, php.parse)
_PYTHON = ParserRegistration("python", 2, python.parse)
_RUST = ParserRegistration("rust", 1, rust.parse)
_SWIFT = ParserRegistration("swift", 1, swift.parse)
_TYPESCRIPT = ParserRegistration("typescript", 1, typescript.parse)
_TSX = ParserRegistration("tsx", 1, typescript.parse_tsx)

_REGISTRY: dict[str, ParserRegistration] = {
    ".c": _C,
    ".cs": _CSHARP,
    ".cts": _TYPESCRIPT,
    ".dart": _DART,
    ".ex": _ELIXIR,
    ".exs": _ELIXIR,
    ".go": _GO,
    ".h": _C,
    ".java": _JAVA,
    ".cjs": _JAVASCRIPT,
    ".js": _JAVASCRIPT,
    ".kt": _KOTLIN,
    ".kts": _KOTLIN,
    ".mjs": _JAVASCRIPT,
    ".mts": _TYPESCRIPT,
    ".php": _PHP,
    ".py": _PYTHON,
    ".rs": _RUST,
    ".ts": _TYPESCRIPT,
    ".tsx": _TSX,
    ".swift": _SWIFT,
}


def get_parser(path: Path) -> CodeParser:
    suffix = path.suffix.lower()
    registration = _REGISTRY.get(suffix)
    if registration is None:
        raise ValueError(f"No parser registered for '{suffix}' files")
    return registration.parser


def supported_extensions() -> set[str]:
    return set(_REGISTRY)


def parser_profile_fingerprint(source_extensions: list[str] | None) -> str:
    extensions = set(source_extensions) if source_extensions is not None else _REGISTRY
    unsupported = sorted(set(extensions) - _REGISTRY.keys())
    if unsupported:
        label = "extension" if len(unsupported) == 1 else "extensions"
        values = ", ".join(repr(extension) for extension in unsupported)
        raise ValueError(f"unsupported source {label} {values}")
    canonical = "\n".join(
        f"{extension}:{_REGISTRY[extension].parser_id}:{_REGISTRY[extension].version}"
        for extension in sorted(extensions)
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
