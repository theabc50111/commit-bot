import os

from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pyhocon import ConfigFactory


class AIModels:
    def __init__(self):
        self._models = {}
        script_dir = os.path.dirname(os.path.abspath(__file__))
        conf_path = os.path.join(script_dir, "conf", "model.conf")
        conf = ConfigFactory.parse_file(conf_path)
        ollama_base_url = conf.get("ollama_base_url")
        self._ollama_base_url = ollama_base_url
        self._model_configs = conf.get_config("model_configs").as_plain_ordered_dict()

    def _create_model(self, model_name: str):
        config = self._model_configs.get(model_name)
        if not config:
            return None

        model_type = config["type"]
        model_id = config["model"]

        if model_type == "ollama":
            return ChatOllama(
                model=model_id, streaming=True, base_url=self._ollama_base_url
            )
        elif model_type == "openai":
            return ChatOpenAI(
                model=model_id, streaming=True, api_key=os.environ.get("OPENAI_API_KEY")
            )
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
