from pathlib import Path

from typer.testing import CliRunner

from slopo.cli import app
from slopo.config import Config, load_config
from slopo.db import create_db


def _write_config(tmp_path: Path) -> tuple[Path, Config]:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    config_path = tmp_path / "slopo.yaml"
    config_path.write_text(
        f'''\
source_dir: "{source_dir}"
source_extensions:
  - ".py"
db_file: "{tmp_path / "slopo.db"}"
embedding_model: "test/model"
embedding_dimensions: 3
'''
    )
    return config_path, load_config(config_path)


def test_index_explains_how_to_rebuild_after_parser_profile_mismatch(tmp_path: Path):
    config_path, cfg = _write_config(tmp_path)
    conn = create_db(cfg)
    conn.execute(
        "UPDATE metadata SET parser_fingerprint = ? WHERE id = 1",
        ("legacy-python-parser",),
    )
    conn.commit()
    conn.close()

    result = CliRunner().invoke(app, ["--config", str(config_path), "index"])

    assert result.exit_code == 1
    assert "configuration mismatch: parser_fingerprint" in result.output
    assert (
        f"Delete the local database at {cfg.db_file} and run `slopo index` to rebuild it."
        in result.output
    )


def test_index_explains_how_to_rebuild_database_from_older_schema(tmp_path: Path):
    config_path, cfg = _write_config(tmp_path)
    conn = create_db(cfg)
    conn.execute("UPDATE schema_version SET version = 2")
    conn.commit()
    conn.close()

    result = CliRunner().invoke(app, ["--config", str(config_path), "index"])

    assert result.exit_code == 1
    assert "schema version mismatch: database is v2" in result.output
    assert (
        f"Delete the local database at {cfg.db_file} and run `slopo index` to rebuild it."
        in result.output
    )
