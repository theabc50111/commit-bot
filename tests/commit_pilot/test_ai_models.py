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


def test_ai_models_is_singleton_and_caches_models():
    """
    Tests that AIModels is a singleton and that it caches the models it creates.
    This test is based on the example code that was in `if __name__ == '__main__'`
    """
    # --- Test Singleton Part ---
    # Create two instances
    ai_models1 = AIModels()
    ai_models2 = AIModels()

    # Check if they are the same instance
    assert ai_models1 is ai_models2

    # --- Test Model Caching Part ---
    # Get a model twice from the first instance
    model1 = ai_models1.get_model("ollama-qwen3:0.6b")
    model2 = ai_models1.get_model("ollama-qwen3:0.6b")

    # Check that they are the same model object
    assert model1 is model2

    # Get the same model from the second instance
    model_from_instance2 = ai_models2.get_model("ollama-qwen3:0.6b")

    # Check that it's the same model object as the one from the first instance
    assert model1 is model_from_instance2

    print(f"id(ai_models1): {id(ai_models1)}")
    print(f"id(ai_models2): {id(ai_models2)}")
    print(f"id(model1): {id(model1)}")
    print(f"id(model2): {id(model2)}")
    print(f"id(model_from_instance2): {id(model_from_instance2)}")
