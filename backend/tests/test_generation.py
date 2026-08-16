from app.core.config import Settings
from app.generation.grounded import GroundedGenerator, LLMConfigurationError


def test_generator_rejects_groq_key_with_xai_endpoint() -> None:
    settings = Settings(
        llm_api_key="gsk_example",
        llm_base_url="https://api.x.ai/v1",
        llm_model="grok-4.5",
    )

    try:
        GroundedGenerator(settings).validate_configuration()
    except LLMConfigurationError as error:
        assert "Groq-format key" in str(error)
    else:
        raise AssertionError("Expected a provider configuration error")


def test_generator_accepts_consistent_groq_configuration() -> None:
    settings = Settings(
        llm_api_key="gsk_example",
        llm_base_url="https://api.groq.com/openai/v1",
        llm_model="llama-3.3-70b-versatile",
    )

    GroundedGenerator(settings).validate_configuration()
