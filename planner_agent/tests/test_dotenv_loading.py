"""Tests for dotenv loading behavior in the planner config (FR: override=False)."""

from __future__ import annotations

import os

import dotenv

from planner_agent import config as config_module


def test_dotenv_does_not_override_existing_env(tmp_path, monkeypatch) -> None:
    """A value already present in the environment must survive dotenv loading."""

    env_file = tmp_path / ".env.local"
    env_file.write_text("PLANNER_TEXT_MODEL=from-dotenv\n", encoding="utf-8")

    monkeypatch.setenv("PLANNER_TEXT_MODEL", "from-system")
    dotenv.load_dotenv(dotenv_path=str(env_file), override=False)

    assert os.environ["PLANNER_TEXT_MODEL"] == "from-system"


def test_dotenv_fills_unset_env(tmp_path, monkeypatch) -> None:
    """dotenv still populates variables that are not already set."""

    env_file = tmp_path / ".env.local"
    env_file.write_text("PLANNER_TEXT_NEW_VAR=from-dotenv\n", encoding="utf-8")

    monkeypatch.delenv("PLANNER_TEXT_NEW_VAR", raising=False)
    dotenv.load_dotenv(dotenv_path=str(env_file), override=False)

    assert os.environ["PLANNER_TEXT_NEW_VAR"] == "from-dotenv"


def test_config_module_loads_without_override() -> None:
    """The config module loads dotenv with override disabled at import time."""

    assert config_module.DOTENV_PATH == ".env.local"
