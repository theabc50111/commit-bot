import pytest

from src.commit_bot.ai_models import AIModels
from src.commit_bot.utils import load_config


@pytest.fixture
def ai_models():
    """Fixture to provide a clean instance of AIModels for each test."""
    yield AIModels()


@pytest.fixture
def model_name():
    """Fixture to provide a model name for testing."""
    return load_config("job.conf").get("used_model", "ollama-qwen3:4b")


@pytest.fixture
def expected_model_id(model_name):
    """Fixture to provide the expected model name for testing."""
    model_id = load_config("model.conf").as_plain_ordered_dict().get("model_configs", {}).get(model_name, {}).get("model_id", model_name)
    post_processed_model_id = model_id.replace("ollama/", "")
    return post_processed_model_id


@pytest.mark.parametrize(
    argnames=["model_name", "expected_model_id"],
    argvalues=[
        ("default_model_name", "default_model_id"),  # Replace with actual default values
    ],
    indirect=["model_name", "expected_model_id"],
)
def test_ollama_model_streaming(ai_models, model_name, expected_model_id):
    """
    Test that we can get an ollama model and stream from it.
    """
    llm_ollama = ai_models.get_model(model_name)
    prompt = [{"role": "user", "content": "hello, who are you"}]
    response_chunks = list(llm_ollama.stream(prompt))
    response_string = " ".join([c.content for c in response_chunks])
    print(f"Response from {model_name}:\n{response_string}")
    # Check that the response chunks are as expected
    assert response_string != "" and response_string.isspace() is False
    assert response_chunks[-1].response_metadata.get("model") == expected_model_id


@pytest.mark.skip(reason="Skipping huggingface model is not ready")
def test_huggingface_model_streaming(ai_models):
    """
    Test that we can get a huggingface model and stream from it.
    This test is based on the example code that was in `if __name__ == '__main__'`
    """
    model = ai_models.get_model("hf-gpt-oss-20b")
    assert model is not None, "Model 'hf-gpt-oss-20b' could not be created. Check model.conf"
    messages = [
        {"role": "system", "content": "You are a helpful assistant that generates concise commit messages based on code changes."},
        {"role": "user", "content": "Generate a concise commit message for the following changes: Added new feature X and fixed bug Y."},
    ]

    response_chunks = list(model.stream(messages))
    response_string = "".join([chunk.content for chunk in response_chunks])
    print(f"Response from hf-gpt-oss-20b:\n{response_string}")

    assert response_string != "" and not response_string.isspace()


def test_ai_models_is_singleton_and_caches_models():
    """
    Tests that AIModels is a singleton and that it caches the models it creates.
    This test is based on the example code that was in `if __name__ == '__main__'`
    """
    # --- Test Singleton Part ---
    # Create two instances
    ai_models1 = AIModels()
    ai_models2 = AIModels()

    # --- Test Model Caching Part ---
    # Get a model twice from the first instance
    model1 = ai_models1.get_model("ollama-qwen3:0.6b")
    model2 = ai_models1.get_model("ollama-qwen3:0.6b")

    # Get the same model from the second instance
    model_from_instance2 = ai_models2.get_model("ollama-qwen3:0.6b")

    print(f"id(ai_models1): {id(ai_models1)}")
    print(f"id(ai_models2): {id(ai_models2)}")
    print(f"id(model1): {id(model1)}")
    print(f"id(model2): {id(model2)}")
    print(f"id(model_from_instance2): {id(model_from_instance2)}")

    # Check that they are the same model object
    assert model1 is model2

    # Check that it's the same model object as the one from the first instance
    assert model1 is model_from_instance2
