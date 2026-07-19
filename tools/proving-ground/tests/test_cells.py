"""Cell env-contract rendering, and the refusal of a cell without a pinned model_id."""

from __future__ import annotations

import pytest
from cells import ENV_API_KEY, ENV_BASE_URL, ENV_MODEL_ID, Cell, hermes_bare


def test_hermes_bare_renders_env_contract():
    cell = hermes_bare()
    env = cell.render_env()
    assert env[ENV_MODEL_ID] == "qwen3.5:4b"
    assert env[ENV_BASE_URL] == "http://host.docker.internal:11434/v1"
    assert env[ENV_API_KEY]  # dummy key present
    assert set(env) == {ENV_BASE_URL, ENV_API_KEY, ENV_MODEL_ID}


def test_model_id_is_recorded_in_env():
    cell = hermes_bare(model_id="qwen3:30b-a3b")
    assert cell.render_env()[ENV_MODEL_ID] == "qwen3:30b-a3b"


def test_cell_without_model_id_is_refused():
    with pytest.raises(ValueError, match="model_id"):
        Cell(name="broken", image="img", model_id="")


def test_cell_with_whitespace_model_id_is_refused():
    with pytest.raises(ValueError, match="model_id"):
        Cell(name="broken", image="img", model_id="   ")


def test_cell_requires_name_and_image():
    with pytest.raises(ValueError, match="name"):
        Cell(name="", image="img", model_id="m")
    with pytest.raises(ValueError, match="image"):
        Cell(name="c", image="", model_id="m")
