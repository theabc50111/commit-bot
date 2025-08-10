import pytest
from src.commit_pilot.ai_models import AIModels


@pytest.fixture
def ai_models():
    """Fixture to provide a clean instance of AIModels for each test."""
    yield AIModels()


@pytest.mark.parametrize(
    "model_name, expected_model_name",
    [("ollama-qwen3:0.6b", "qwen3:0.6b"),],
)
def test_ollama_model_streaming(ai_models, model_name, expected_model_name):
    """
    Test that we can get an ollama model and stream from it.
    """
    llm_ollama = ai_models.get_model(model_name)
    prompt = "hello, who are you"
    response_chunks = list(llm_ollama.stream(prompt))
    response_string = " ".join([c.content for c in response_chunks])
    print(f"Response from {model_name}: {response_string}")
    # Check that the response chunks are as expected
    assert response_string != "" and response_string.isspace() is False
    assert response_chunks[-1].response_metadata.get("model") == expected_model_name
