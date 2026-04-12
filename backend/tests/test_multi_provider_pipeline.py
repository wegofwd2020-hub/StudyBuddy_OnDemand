"""
tests/test_multi_provider_pipeline.py

Epic 1 — Multi-Provider LLM Pipeline tests.

Test coverage:
  F-1  Provider abstraction layer (registry, base interface, provider init)
  F-2  build_unit/build_grade accept --provider flag, stamp provider in output
  F-3  Multi-provider (comparison) builds in build_grade
  F-5  School LLM config API (GET / PUT /schools/{id}/llm-config)

All external calls (LLM APIs, DB) are mocked — no live APIs in CI.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Helpers ──────────────────────────────────────────────────────────────────


_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def _make_config(tmpdir: str, provider: str = "anthropic") -> MagicMock:
    cfg = MagicMock()
    cfg.CONTENT_STORE_PATH = tmpdir
    cfg.CONTENT_VERSION = 1
    cfg.CLAUDE_MODEL = "claude-sonnet-4-6"
    cfg.OPENAI_MODEL = "gpt-4o"
    cfg.GEMINI_MODEL = "gemini-1.5-pro"
    cfg.ANTHROPIC_API_KEY = "test-anthropic-key"
    cfg.OPENAI_API_KEY = "test-openai-key"
    cfg.GOOGLE_API_KEY = "test-google-key"
    cfg.DEFAULT_PROVIDER = provider
    cfg.S3_BUCKET_NAME = None
    cfg.TOKEN_COST_INPUT_USD = 0.000003
    cfg.TOKEN_COST_OUTPUT_USD = 0.000015
    cfg.MAX_PIPELINE_COST_USD = 50.0
    cfg.REVIEW_AUTO_APPROVE = False
    cfg.DATABASE_URL = None
    cfg.PUSHGATEWAY_URL = None
    return cfg


_VALID_LESSON = {
    "unit_id": "G8-SCI-001",
    "subject": "Science",
    "topic": "Density",
    "synopsis": "Learn about density.",
    "key_concepts": ["density", "buoyancy"],
    "learning_objectives": ["Explain density"],
    "reading_level": "Grade 8",
    "estimated_duration_minutes": 30,
    "language": "en",
    "generated_at": "2026-04-01T00:00:00Z",
    "model": "claude-sonnet-4-6",
    "content_version": 1,
}
_VALID_QUIZ_QUESTIONS = [
    {
        "question_id": f"q{i}",
        "question_text": f"What is the definition of density question number {i}?",
        "question_type": "multiple_choice",
        "options": [
            {"option_id": "A", "text": "Mass divided by volume"},
            {"option_id": "B", "text": "Volume divided by mass"},
            {"option_id": "C", "text": "Mass times volume"},
            {"option_id": "D", "text": "Mass plus volume"},
        ],
        "correct_option": "A",
        "explanation": "Density is mass divided by volume (D = m/V).",
        "difficulty": "medium",
    }
    for i in range(1, 9)
]
_VALID_QUIZ = {
    "unit_id": "G8-SCI-001",
    "set_number": 1,
    "language": "en",
    "questions": _VALID_QUIZ_QUESTIONS,
    "total_questions": 8,
    "estimated_duration_minutes": 10,
    "passing_score": 6,
    "generated_at": "2026-04-01T00:00:00Z",
    "model": "claude-sonnet-4-6",
    "content_version": 1,
}
_VALID_TUTORIAL = {
    "unit_id": "G8-SCI-001",
    "language": "en",
    "title": "Density Tutorial",
    "sections": [
        {
            "section_id": "s1",
            "title": "What is Density?",
            "content": "Density = mass / volume.",
            "examples": ["A rock is denser than wood."],
            "practice_question": "Calculate density.",
        }
    ],
    "common_mistakes": ["Confusing mass with weight"],
    "generated_at": "2026-04-01T00:00:00Z",
    "model": "claude-sonnet-4-6",
    "content_version": 1,
}


def _cycle_responses(*jsons):
    """Return a side_effect function that cycles through JSON strings."""
    responses = list(jsons)
    call_count = [0]

    def _fn(*args, **kwargs):
        text = responses[call_count[0] % len(responses)]
        call_count[0] += 1
        return text, 100, 200

    return _fn


# ── F-1: Provider registry ────────────────────────────────────────────────────


def test_provider_registry_list():
    """list_providers() returns all three registered provider IDs."""
    from pipeline.providers import list_providers

    providers = list_providers()
    assert "anthropic" in providers
    assert "openai" in providers
    assert "google" in providers


def test_provider_registry_unknown():
    """get_provider raises ValueError for unknown provider IDs."""
    from pipeline.providers import get_provider

    config = MagicMock()
    with pytest.raises(ValueError, match="Unknown provider 'bad_provider'"):
        get_provider("bad_provider", config)


def test_anthropic_provider_init_missing_key():
    """AnthropicProvider raises RuntimeError when API key is missing."""
    from pipeline.providers.anthropic import AnthropicProvider

    config = MagicMock()
    config.ANTHROPIC_API_KEY = None

    mock_anthropic = MagicMock()
    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            AnthropicProvider(config)


def test_anthropic_provider_init_missing_sdk():
    """AnthropicProvider raises RuntimeError when anthropic SDK is not installed."""
    from pipeline.providers.anthropic import AnthropicProvider

    config = MagicMock()
    config.ANTHROPIC_API_KEY = "key"

    with patch.dict("sys.modules", {"anthropic": None}):
        with pytest.raises((RuntimeError, ImportError)):
            AnthropicProvider(config)


def test_openai_provider_init_missing_key():
    """OpenAIProvider raises RuntimeError when API key is missing."""
    from pipeline.providers.openai import OpenAIProvider

    config = MagicMock()
    config.OPENAI_API_KEY = None

    mock_openai = MagicMock()
    with patch.dict("sys.modules", {"openai": mock_openai}):
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            OpenAIProvider(config)


def test_google_provider_init_missing_key():
    """GeminiProvider raises RuntimeError when API key is missing."""
    from pipeline.providers.google import GeminiProvider

    config = MagicMock()
    config.GOOGLE_API_KEY = None

    mock_genai_module = MagicMock()
    mock_google_pkg = MagicMock()
    mock_google_pkg.generativeai = mock_genai_module

    with patch.dict(
        "sys.modules",
        {"google": mock_google_pkg, "google.generativeai": mock_genai_module},
    ):
        with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
            GeminiProvider(config)


def test_anthropic_provider_generate():
    """AnthropicProvider.generate() returns (text, in_tokens, out_tokens)."""
    from pipeline.providers.anthropic import AnthropicProvider

    config = MagicMock()
    config.ANTHROPIC_API_KEY = "test-key"
    config.CLAUDE_MODEL = "claude-sonnet-4-6"

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text='{"hello": "world"}')]
    mock_message.usage.input_tokens = 50
    mock_message.usage.output_tokens = 100

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    mock_anthropic = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client

    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        provider = AnthropicProvider(config)
        text, in_tok, out_tok = provider.generate("test prompt")

    assert text == '{"hello": "world"}'
    assert in_tok == 50
    assert out_tok == 100


def test_openai_provider_generate():
    """OpenAIProvider.generate() extracts text and token counts from response."""
    from pipeline.providers.openai import OpenAIProvider

    config = MagicMock()
    config.OPENAI_API_KEY = "test-key"
    config.OPENAI_MODEL = "gpt-4o"

    mock_choice = MagicMock()
    mock_choice.message.content = '{"answer": 42}'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 30
    mock_response.usage.completion_tokens = 80

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    mock_openai = MagicMock()
    mock_openai.OpenAI.return_value = mock_client

    with patch.dict("sys.modules", {"openai": mock_openai}):
        provider = OpenAIProvider(config)
        text, in_tok, out_tok = provider.generate("test prompt")

    assert text == '{"answer": 42}'
    assert in_tok == 30
    assert out_tok == 80


def test_google_provider_generate():
    """GeminiProvider.generate() extracts text and token counts from response."""
    from pipeline.providers.google import GeminiProvider

    config = MagicMock()
    config.GOOGLE_API_KEY = "test-key"
    config.GEMINI_MODEL = "gemini-1.5-pro"

    mock_response = MagicMock()
    mock_response.text = '{"result": "ok"}'
    mock_response.usage_metadata.prompt_token_count = 40
    mock_response.usage_metadata.candidates_token_count = 90

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    # google and google.generativeai must be separate mocks so that
    # `import google.generativeai as genai` resolves to mock_genai_module
    # whether Python uses sys.modules lookup OR the parent package attribute.
    mock_genai_module = MagicMock()
    mock_genai_module.GenerativeModel.return_value = mock_model

    mock_google_pkg = MagicMock()
    mock_google_pkg.generativeai = mock_genai_module

    with patch.dict(
        "sys.modules",
        {"google": mock_google_pkg, "google.generativeai": mock_genai_module},
    ):
        provider = GeminiProvider(config)
        text, in_tok, out_tok = provider.generate("test prompt")

    assert text == '{"result": "ok"}'
    assert in_tok == 40
    assert out_tok == 90


# ── F-2: build_unit with explicit provider ────────────────────────────────────


def test_build_unit_dry_run_includes_provider():
    """build_unit dry_run returns provider in the result dict."""
    from pipeline.build_unit import build_unit

    with tempfile.TemporaryDirectory() as tmpdir:
        config = _make_config(tmpdir, provider="openai")

        result = build_unit(
            curriculum_id="default-2026-g8",
            unit_id="G8-SCI-001",
            unit_data={"title": "Density", "subject": "science", "has_lab": False, "grade": 8},
            lang="en",
            config=config,
            dry_run=True,
        )

    assert result["status"] == "dry_run"
    assert result["provider"] == "openai"


def test_build_unit_explicit_provider_id():
    """build_unit with provider_id='openai' stamps openai in the result."""
    from pipeline.build_unit import build_unit
    from pipeline.providers.base import LLMProvider

    # Inject a mock provider directly
    mock_provider = MagicMock(spec=LLMProvider)
    mock_provider.provider_id = "openai"
    mock_provider.model = "gpt-4o"

    responses = [
        json.dumps(_VALID_LESSON),
        json.dumps({**_VALID_QUIZ, "set_number": 1}),
        json.dumps({**_VALID_QUIZ, "set_number": 2}),
        json.dumps({**_VALID_QUIZ, "set_number": 3}),
        json.dumps(_VALID_TUTORIAL),
    ]
    call_count = [0]

    def _generate(prompt: str):
        text = responses[call_count[0] % len(responses)]
        call_count[0] += 1
        return text, 100, 200

    mock_provider.generate.side_effect = _generate

    with tempfile.TemporaryDirectory() as tmpdir:
        config = _make_config(tmpdir, provider="anthropic")

        with (
            patch("pipeline.build_unit.synthesize_lesson"),
            patch("pipeline.build_unit._upload_unit_to_s3"),
            patch("pipeline.alex_runner.run_alex", return_value={"warnings_count": 0, "warnings": []}),
        ):
            result = build_unit(
                curriculum_id="default-2026-g8",
                unit_id="G8-SCI-001",
                unit_data={"title": "Density", "subject": "science", "has_lab": False, "grade": 8},
                lang="en",
                config=config,
                force=True,
                provider_id="openai",
                provider=mock_provider,
            )

    assert result["status"] == "ok"
    assert result["provider"] == "openai"
    assert result["tokens_used"] > 0


def test_build_unit_idempotency_respects_provider():
    """
    build_unit skips regeneration only when provider matches the built meta.
    A different provider triggers a rebuild.
    """
    from pipeline.build_unit import build_unit

    with tempfile.TemporaryDirectory() as tmpdir:
        curriculum_id = "default-2026-g8"
        unit_id = "G8-SCI-001"
        lang = "en"
        store_path = os.path.join(tmpdir, "curricula", curriculum_id, unit_id)
        os.makedirs(store_path, exist_ok=True)

        # Write meta.json marked as built by anthropic
        meta = {
            "unit_id": unit_id,
            "curriculum_id": curriculum_id,
            "generated_at": "2026-04-01T00:00:00Z",
            "model": "claude-sonnet-4-6",
            "provider": "anthropic",
            "content_version": 1,
            "langs_built": ["en"],
            "alex_warnings_count": 0,
        }
        with open(os.path.join(store_path, "meta.json"), "w") as f:
            json.dump(meta, f)
        for fname in ["lesson_en.json", "quiz_set_1_en.json", "quiz_set_2_en.json",
                      "quiz_set_3_en.json", "tutorial_en.json"]:
            with open(os.path.join(store_path, fname), "w") as f:
                json.dump({"unit_id": unit_id}, f)

        config = _make_config(tmpdir)

        # Same provider → skip
        result_skip = build_unit(
            curriculum_id=curriculum_id, unit_id=unit_id,
            unit_data={"title": "D", "subject": "s", "has_lab": False, "grade": 8},
            lang=lang, config=config, force=False, provider_id="anthropic",
        )
        assert result_skip["status"] == "skipped"

        # Different provider → dry_run to avoid calling LLM, but status is NOT skipped
        result_diff = build_unit(
            curriculum_id=curriculum_id, unit_id=unit_id,
            unit_data={"title": "D", "subject": "s", "has_lab": False, "grade": 8},
            lang=lang, config=config, force=False, provider_id="openai", dry_run=True,
        )
        assert result_diff["status"] == "dry_run"
        assert result_diff["provider"] == "openai"


# ── F-3: Multi-provider comparison build ─────────────────────────────────────


def test_build_grade_multi_provider_dry_run():
    """
    run_grade with providers=['anthropic', 'openai'] runs in dry_run mode
    and returns both providers in the summary.
    """
    import json as _json

    from pipeline.build_grade import run_grade

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a minimal grade data file
        grade_data = {
            "grade": 8,
            "subjects": [
                {
                    "subject_id": "science",
                    "name": "Science",
                    "units": [
                        {"unit_id": "G8-SCI-001", "title": "Density", "has_lab": False}
                    ],
                }
            ],
        }
        data_dir = os.path.join(tmpdir, "data")
        os.makedirs(data_dir, exist_ok=True)
        grade_file = os.path.join(data_dir, "grade8_stem.json")
        with open(grade_file, "w") as f:
            _json.dump(grade_data, f)

        from pipeline import build_grade as bg_module

        original_root = bg_module._REPO_ROOT
        try:
            bg_module._REPO_ROOT = tmpdir

            with patch("pipeline.config.settings") as mock_settings:
                mock_settings.CONTENT_STORE_PATH = tmpdir
                mock_settings.CONTENT_VERSION = 1
                mock_settings.CLAUDE_MODEL = "claude-sonnet-4-6"
                mock_settings.OPENAI_MODEL = "gpt-4o"
                mock_settings.ANTHROPIC_API_KEY = "test-key"
                mock_settings.OPENAI_API_KEY = "test-key"
                mock_settings.DEFAULT_PROVIDER = "anthropic"
                mock_settings.S3_BUCKET_NAME = None
                mock_settings.TOKEN_COST_INPUT_USD = 0.000003
                mock_settings.TOKEN_COST_OUTPUT_USD = 0.000015
                mock_settings.MAX_PIPELINE_COST_USD = 50.0
                mock_settings.REVIEW_AUTO_APPROVE = False
                mock_settings.DATABASE_URL = None
                mock_settings.PUSHGATEWAY_URL = None

                summary = run_grade(
                    grade=8,
                    langs=["en"],
                    year=2026,
                    force=False,
                    dry_run=True,
                    providers=["anthropic", "openai"],
                )

        finally:
            bg_module._REPO_ROOT = original_root

    assert summary["providers"] == ["anthropic", "openai"]
    assert summary["succeeded"] > 0


def test_build_grade_single_provider_default():
    """
    run_grade without providers= defaults to [config.DEFAULT_PROVIDER] in summary.
    """
    from pipeline.build_grade import run_grade

    with tempfile.TemporaryDirectory() as tmpdir:
        grade_data = {
            "grade": 8,
            "subjects": [
                {
                    "subject_id": "math",
                    "name": "Math",
                    "units": [{"unit_id": "G8-MATH-001", "title": "Algebra", "has_lab": False}],
                }
            ],
        }
        data_dir = os.path.join(tmpdir, "data")
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, "grade8_stem.json"), "w") as f:
            json.dump(grade_data, f)

        from pipeline import build_grade as bg_module

        original_root = bg_module._REPO_ROOT
        try:
            bg_module._REPO_ROOT = tmpdir

            with patch("pipeline.config.settings") as mock_settings:
                mock_settings.CONTENT_STORE_PATH = tmpdir
                mock_settings.CONTENT_VERSION = 1
                mock_settings.CLAUDE_MODEL = "claude-sonnet-4-6"
                mock_settings.ANTHROPIC_API_KEY = "test-key"
                mock_settings.DEFAULT_PROVIDER = "anthropic"
                mock_settings.S3_BUCKET_NAME = None
                mock_settings.TOKEN_COST_INPUT_USD = 0.000003
                mock_settings.TOKEN_COST_OUTPUT_USD = 0.000015
                mock_settings.MAX_PIPELINE_COST_USD = 50.0
                mock_settings.REVIEW_AUTO_APPROVE = False
                mock_settings.DATABASE_URL = None
                mock_settings.PUSHGATEWAY_URL = None

                summary = run_grade(
                    grade=8,
                    langs=["en"],
                    year=2026,
                    dry_run=True,
                    providers=None,
                )

        finally:
            bg_module._REPO_ROOT = original_root

    assert summary["providers"] == ["anthropic"]


# ── F-5: School LLM config API ────────────────────────────────────────────────
#
# Tests follow the same pattern as test_school.py:
#   1. Register a school (creates school + school_admin in DB)
#   2. Use the returned token to call LLM config endpoints
#   3. The migration 0043 adds school_llm_config table — applied in conftest run_migrations
#

from tests.helpers.token_factory import make_teacher_token


@pytest.mark.asyncio
async def test_get_llm_config_returns_defaults(client):
    """GET /schools/{id}/llm-config returns default config for a new school."""
    # Register a school
    reg = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": "LLM Config Test School A",
            "contact_email": "llm-a@test-provider.example.com",
            "country": "CA",
            "password": "TestPassw0rd!!",
        },
    )
    assert reg.status_code == 201, reg.text
    school_id = reg.json()["school_id"]
    token = reg.json()["access_token"]

    r = await client.get(
        f"/api/v1/schools/{school_id}/llm-config",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["default_provider"] == "anthropic"
    assert "anthropic" in data["allowed_providers"]
    assert data["comparison_enabled"] is False
    assert data["dpa_acknowledged_at"] == {}


@pytest.mark.asyncio
async def test_get_llm_config_teacher_forbidden(client):
    """Non-school_admin teacher cannot access LLM config."""
    reg = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": "LLM Config Test School B",
            "contact_email": "llm-b@test-provider.example.com",
            "country": "CA",
            "password": "TestPassw0rd!!",
        },
    )
    assert reg.status_code == 201, reg.text
    school_id = reg.json()["school_id"]
    # Use a regular teacher token (not school_admin)
    teacher_token = make_teacher_token(school_id=school_id, role="teacher")

    r = await client.get(
        f"/api/v1/schools/{school_id}/llm-config",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_update_llm_config_add_provider(client):
    """PUT /schools/{id}/llm-config enables openai and acknowledges its DPA."""
    reg = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": "LLM Config Test School C",
            "contact_email": "llm-c@test-provider.example.com",
            "country": "CA",
            "password": "TestPassw0rd!!",
        },
    )
    assert reg.status_code == 201, reg.text
    school_id = reg.json()["school_id"]
    token = reg.json()["access_token"]

    r = await client.put(
        f"/api/v1/schools/{school_id}/llm-config",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "allowed_providers": ["anthropic", "openai"],
            "default_provider": "openai",
            "comparison_enabled": True,
            "acknowledge_dpa": ["openai"],
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "openai" in data["allowed_providers"]
    assert data["default_provider"] == "openai"
    assert data["comparison_enabled"] is True
    assert "openai" in data["dpa_acknowledged_at"]


@pytest.mark.asyncio
async def test_update_llm_config_invalid_provider(client):
    """PUT with an unknown provider ID returns 422."""
    reg = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": "LLM Config Test School D",
            "contact_email": "llm-d@test-provider.example.com",
            "country": "CA",
            "password": "TestPassw0rd!!",
        },
    )
    assert reg.status_code == 201, reg.text
    school_id = reg.json()["school_id"]
    token = reg.json()["access_token"]

    r = await client.put(
        f"/api/v1/schools/{school_id}/llm-config",
        headers={"Authorization": f"Bearer {token}"},
        json={"allowed_providers": ["badprovider"]},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_llm_config_cross_school_forbidden(client):
    """A school_admin cannot update another school's LLM config."""
    reg = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": "LLM Config Test School E",
            "contact_email": "llm-e@test-provider.example.com",
            "country": "CA",
            "password": "TestPassw0rd!!",
        },
    )
    assert reg.status_code == 201, reg.text
    school_id = reg.json()["school_id"]
    token = reg.json()["access_token"]

    other_school = "c0000000-0000-0000-0000-000000000099"
    r = await client.put(
        f"/api/v1/schools/{other_school}/llm-config",
        headers={"Authorization": f"Bearer {token}"},
        json={"default_provider": "openai"},
    )
    assert r.status_code == 403
