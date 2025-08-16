import os

from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import ChatHuggingFace
from langchain_openai import ChatOpenAI
from pyhocon import ConfigFactory

from src.commit_pilot.huggingface_chat_model import get_hf_base_llm
from src.commit_pilot.utils import load_config


class AIModels:
    _instance = None

    def __new__(cls):
        """Singleton pattern to ensure only one instance of AIModels exists."""
        if cls._instance is not None:
            return cls._instance
        cls._instance = super(AIModels, cls).__new__(cls)
        cls._instance._models = {}
        conf = load_config("model.conf")
        ollama_base_url = conf.get("ollama_base_url")
        cls._instance._ollama_base_url = ollama_base_url
        cls._instance._model_configs = conf.get_config("model_configs").as_plain_ordered_dict()
        return cls._instance

    def _create_model(self, model_name: str):
        config = self._model_configs.get(model_name)
        if not config:
            return None

        model_type = config["type"]
        model_id = config.get("model") or config.get("model_path")

        if model_type == "ollama":
            return ChatOllama(model=model_id, streaming=True, base_url=self._ollama_base_url)
        elif model_type == "openai":
            return ChatOpenAI(model=model_id, streaming=True, api_key=os.environ.get("OPENAI_API_KEY"))
        elif model_type == "gemini":
            return ChatGoogleGenerativeAI(
                model=model_id,
                streaming=True,
                google_api_key=os.environ.get("GOOGLE_API_KEY"),
            )
        elif model_type == "claude":
            return ChatAnthropic(
                model=model_id,
                streaming=True,
                api_key=os.environ.get("ANTHROPIC_API_KEY"),
            )
        elif model_type == "huggingface":
            hf_base_llm = get_hf_base_llm(config)
            return ChatHuggingFace(llm=hf_base_llm, streaming=True)
        return None

    def get_model(self, model_name: str):
        if model_name not in self._models:
            model_instance = self._create_model(model_name)
            if model_instance:
                self._models[model_name] = model_instance
            else:
                return None
        return self._models.get(model_name)

    def get_available_models(self):
        return list(self._model_configs.keys())


if __name__ == "__main__":
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    ai_models = AIModels()
    print("Available models:", ai_models.get_available_models())
    model = ai_models.get_model("hf-gpt-oss-20b")
    messages = [
        SystemMessage(content="You are a helpful assistant that generates concise commit messages based on code changes."),
        HumanMessage(content="Generate a concise commit message for the following changes:\nAdded new feature X and fixed bug Y."),
    ]
    for chunk in model.stream(messages):
        print(chunk.content, end="", flush=True)
