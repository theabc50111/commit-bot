import os

from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import ChatHuggingFace
from langchain_openai import ChatOpenAI

from .huggingface_chat_model import get_hf_base_llm
from .utils import load_config


class AIModels:
    _instance = None

    def __new__(cls):
        """Singleton pattern to ensure only one instance of AIModels exists."""
        if cls._instance is not None:
            return cls._instance
        conf = load_config("model.conf")
        ollama_base_url = conf.get("ollama_base_url")
        cls._instance = super(AIModels, cls).__new__(cls)
        cls._instance._models = {}
        cls._instance._ollama_base_url = ollama_base_url
        cls._instance._model_configs = conf.get_config("model_configs").as_plain_ordered_dict()
        cls._instance._default_gen_configs = conf.get_config("default_gen_configs").as_plain_ordered_dict()
        return cls._instance

    def _get_all_configs(self, model_name: str):
        model_conf = self._model_configs.get(model_name)
        generate_conf = self._default_gen_configs
        if not model_conf or not generate_conf:
            return None
        return model_conf.get("type"), {"model":model_conf.get("model_id"), "base_url":self._ollama_base_url, **generate_conf}


    def _create_model(self, model_name: str):
        model_type, gen_conf = self._get_all_configs(model_name)
        if model_type == "ollama":
            return ChatOllama(**gen_conf)
        elif model_type == "openai":
            return ChatOpenAI(**gen_conf, api_key=os.environ.get("OPENAI_API_KEY"))
        elif model_type == "gemini":
            return ChatGoogleGenerativeAI(**gen_conf, google_api_key=os.environ.get("GOOGLE_API_KEY"))
        elif model_type == "claude":
            return ChatAnthropic(**gen_conf, api_key=os.environ.get("ANTHROPIC_API_KEY"))
        elif model_type == "huggingface":
            raise NotImplementedError("Huggingface model support is not implemented yet.")
            #hf_base_llm = get_hf_base_llm(config)
            #return ChatHuggingFace(llm=hf_base_llm, streaming=True)
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
