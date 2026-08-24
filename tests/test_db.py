from dataclasses import replace
from pathlib import Path

import pytest

from slopo import db
from slopo.config import parse_config
from slopo.db import ConfigurationMismatchError, chunked, create_db, open_db
from slopo.indexing.parsing import registry


def _config(tmp_path: Path):
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    return parse_config(
        {
            "source_dir": str(source_dir),
            "source_extensions": [".py"],
            "db_file": str(tmp_path / "slopo.db"),
            "embedding_model": "test/model",
            "embedding_dimensions": 3,
        },
        source="<test>",
    )


def test_yields_nothing_for_empty_input():
    assert list(chunked([])) == []


def test_yields_single_chunk_when_input_fits(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(db, "_MAX_SQL_VARIABLES", 3)

    assert list(chunked([1, 2])) == [[1, 2]]


def test_splits_input_across_chunks(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(db, "_MAX_SQL_VARIABLES", 2)

    assert list(chunked([1, 2, 3, 4, 5])) == [[1, 2], [3, 4], [5]]


def test_exact_multiple_leaves_no_trailing_empty_chunk(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(db, "_MAX_SQL_VARIABLES", 2)

    assert list(chunked([1, 2, 3, 4])) == [[1, 2], [3, 4]]


def test_rejects_stale_parser_profile_before_unchanged_mtime_can_skip_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    cfg = _config(tmp_path)
    source_path = cfg.source_dir / "record.py"
    source_path.write_text("@dataclass\nclass Record:\n    value: int\n")
    conn = create_db(cfg)
    conn.execute(
        "INSERT INTO files (path, mtime) VALUES (?, ?)",
        (source_path.name, source_path.stat().st_mtime),
    )
    conn.commit()
    conn.close()
    python = registry._REGISTRY[".py"]
    monkeypatch.setitem(
        registry._REGISTRY,
        ".py",
        replace(python, version=python.version + 1),
    )

    with pytest.raises(ConfigurationMismatchError) as error:
        open_db(cfg)

    assert error.value.field == "parser_fingerprint"
    assert error.value.stored != error.value.current


def test_rejects_changed_active_extension_profile(tmp_path: Path):
    cfg = _config(tmp_path)
    create_db(cfg).close()
    expanded_cfg = replace(cfg, source_extensions=[".py", ".java"])

    with pytest.raises(ConfigurationMismatchError) as error:
        open_db(expanded_cfg)

    assert error.value.field == "parser_fingerprint"


def test_inactive_parser_version_does_not_invalidate_scoped_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    cfg = _config(tmp_path)
    create_db(cfg).close()
    dart = registry._REGISTRY[".dart"]
    monkeypatch.setitem(
        registry._REGISTRY,
        ".dart",
        replace(dart, version=dart.version + 1),
    )

    conn = open_db(cfg)

    conn.close()


def test_create_rejects_unsupported_parser_profile_without_database_artifact(
    tmp_path: Path,
):
    cfg = replace(_config(tmp_path), source_extensions=[".vue"])

    with pytest.raises(ValueError, match=r"unsupported source extension '\.vue'"):
        create_db(cfg)

    assert not cfg.db_file.exists()


def test_open_rejects_unsupported_parser_profile_before_reading_database(
    tmp_path: Path,
):
    cfg = replace(_config(tmp_path), source_extensions=[".vue"])
    original = b"existing database contents"
    cfg.db_file.write_bytes(original)

    with pytest.raises(ValueError, match=r"unsupported source extension '\.vue'"):
        open_db(cfg)

    assert cfg.db_file.read_bytes() == original
