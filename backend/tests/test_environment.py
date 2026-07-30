import os

from config.settings.environment import load_env_file


def test_load_env_file_loads_values_and_strips_matching_quotes(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("DOTENV_PLAIN", raising=False)
    monkeypatch.delenv("DOTENV_QUOTED", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# local settings\n"
        "DOTENV_PLAIN=value\n"
        'DOTENV_QUOTED="quoted value"\n',
        encoding="utf-8",
    )

    load_env_file(env_file)

    assert os.environ["DOTENV_PLAIN"] == "value"
    assert os.environ["DOTENV_QUOTED"] == "quoted value"


def test_load_env_file_does_not_replace_explicit_process_value(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("DOTENV_PRIORITY", "from-process")
    env_file = tmp_path / ".env"
    env_file.write_text("DOTENV_PRIORITY=from-file\n", encoding="utf-8")

    load_env_file(env_file)

    assert os.environ["DOTENV_PRIORITY"] == "from-process"


def test_load_env_file_allows_missing_file(tmp_path):
    load_env_file(tmp_path / "missing.env")
